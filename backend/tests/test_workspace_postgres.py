"""PostgreSQL-only locking tests. Requires a dedicated *_test database explicitly configured.
Only a generated png5_test_<hex> schema is created and dropped.
"""
import os
import sys
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
pytest.importorskip('sqlalchemy')
pytest.importorskip('psycopg')
pytest.importorskip('argon2')
pytest.importorskip('jwt')
from sqlalchemy import text,event
from sqlalchemy.engine import make_url
from workspace.models import Database,Base,Organization,Policy,Source,Task,Connector,Agent,ReviewerGroup
from workspace.audit import append,verify
from workspace.admin import Administration
from workspace.identity import Identity,PERMISSIONS
from workspace.runtime import Runtime
from workspace.sources import LocalStorage

@pytest.fixture
def pg(tmp_path):
    url=os.getenv('TEST_DATABASE_URL','')
    if not url:pytest.skip('Set TEST_DATABASE_URL to a disposable PostgreSQL database ending in _test')
    if not make_url(url).database.endswith('_test'):pytest.fail('Refusing a database not ending in _test')
    db=Database(url);schema='png5_test_'+uuid4().hex
    with db.engine.begin() as c:c.execute(text('CREATE SCHEMA '+schema))
    db.engine.dispose()
    @event.listens_for(db.engine,'connect')
    def search_path(connection,record):
        with connection.cursor() as cursor:cursor.execute('SET search_path TO '+schema)
        connection.commit()
    try:
        Base.metadata.create_all(db.engine)
        yield db
    finally:
        # Generated literal identifier, never taken from a user or production schema name.
        with db.engine.begin() as c:c.execute(text('DROP SCHEMA '+schema+' CASCADE'))
        db.engine.dispose()

def test_concurrent_audit_appends(pg):
    with pg.transaction() as s:
        org=Organization(name='Test');s.add(org);s.flush();oid=org.id
    def write(i):
        with pg.transaction(oid) as s:append(s,oid,'test','concurrency',{'i':i})
    with ThreadPoolExecutor(8) as pool:list(pool.map(write,range(40)))
    with pg.transaction(oid) as s:
        result=verify(s,oid);assert result['valid'] and result['event_count']==40

def test_concurrent_publish_and_approval(pg,tmp_path):
    from fastapi import HTTPException
    import sqlite3
    with pg.transaction() as s:
        org=Organization(name='Test');s.add(org);s.flush();oid=org.id
    admin=Administration(pg,LocalStorage(tmp_path/'docs'));owner=Identity('admin',oid,'human',permissions=PERMISSIONS)
    agent=admin.registry(owner,Agent,{'role':'data_analyst'},'Analyst')
    connectors=[admin.registry(owner,Connector,{'kind':kind,'destinations':['review@example.test'] if kind=='simulated_delivery' else []},kind) for kind in ['demo_sales','report_storage','simulated_delivery']]
    task=admin.registry(owner,Task,{'roles':['data_analyst'],'resources':[c['id'] for c in connectors],'agents':[agent['id']]},'Sales')
    group=admin.registry(owner,ReviewerGroup,{},'Managers')
    with pg.transaction(oid) as s:
        source=Source(organization_id=oid,name='Policy',data={'revision':1,'segments':[{'index':1,'text':'Read, create reports, share with manager approval.'}]});s.add(source);s.flush();sid=source.id
    rules=[{'id':str(i),'role':'data_analyst','tool':tool,'resource':c['id'],'tasks':[task['id']], 'decision':'ESCALATE' if i==2 else 'ALLOW','reviewer_group':group['id'] if i==2 else None,
            'arguments':{'destinations':['review@example.test'] if i==2 else []},'source':{'source_id':sid,'revision':1,'segment':1,'passage':'Read, create reports, share with manager approval.'}} for i,(tool,c) in enumerate(zip(['database.read','report.create','report.send'],connectors))]
    drafts=[admin.draft(owner,rules,'Policy') for _ in range(2)]
    for draft in drafts:admin.validate(owner,draft['id'])
    def publish(draft):
        try:return admin.publish(owner,draft['id'],None)['state']
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(publish,drafts))
    assert sorted(map(str,results))==['409','PUBLISHED']
    demo=tmp_path/'demo.db';c=sqlite3.connect(demo);c.execute('CREATE TABLE sales_summary(month TEXT,total_sales INTEGER)');c.execute("INSERT INTO sales_summary VALUES('January',10)");c.commit();c.close()
    runtime=Runtime(pg,tmp_path/'reports',demo);who=Identity(agent['id'],oid,'agent','data_analyst')
    def submit(index,arguments):return runtime.submit(who,{'task_id':task['id'],'tool':rules[index]['tool'],'resource':connectors[index]['id'],'arguments':arguments})
    read=submit(0,{'limit':3});report=submit(1,{'source_artifact_id':read['result']['artifact_id']});pending=submit(2,{'artifact_id':report['result']['artifact_id'],'recipient':'review@example.test'})
    reviewer=Identity('reviewer',oid,'human',permissions=frozenset({'review'}),groups=frozenset({group['id']}))
    def approve(_):
        try:return runtime.review(reviewer,pending['request_id'],True,'checked')['state']
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(approve,range(2)))
    assert sorted(map(str,results))==['409','SUCCEEDED']
    with pg.transaction(oid) as s:assert verify(s,oid)['valid']
