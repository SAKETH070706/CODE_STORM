"""Read-only corroboration. No credentials or connection strings are emitted."""
import json, sys, sqlite3
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[2]
try:
    url=dotenv_values(ROOT/'backend/.env').get('DATABASE_URL','').replace('postgresql+psycopg://','postgresql://')
    with psycopg.connect(url,connect_timeout=10,row_factory=dict_row) as connection:
        connection.read_only=True
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL statement_timeout = 10000')
            cursor.execute("SELECT id,email,active,can_create_workspaces,(password_hash IS NOT NULL AND length(password_hash)>0) AS has_password_hash FROM users WHERE email=%s",('admin@example.test',))
            admin=cursor.fetchall()
            cursor.execute('SELECT id,name,active_policy_id,audit_sequence,audit_head FROM organizations ORDER BY created_at')
            organizations=cursor.fetchall()
            cursor.execute("SELECT id,user_id,organization_id,permissions,groups,active FROM memberships WHERE user_id IN (SELECT id FROM users WHERE email=%s)",('admin@example.test',))
            memberships=cursor.fetchall()
            counts={}
            for table in ['users','memberships','agents','tasks','connectors','reviewer_groups','policies','policy_sources','workspace_actions','workspace_artifacts','workspace_approvals','workspace_outbox','compilation_jobs','agent_credentials','workspace_idempotency','workspace_audit']:
                cursor.execute('SELECT count(*) AS count FROM '+table)
                counts[table]=cursor.fetchone()['count']
            result={'admin':admin,'organizations':organizations,'admin_memberships':memberships,'counts':counts}
            if '--records' in sys.argv:
                records={}
                for table in ['agents','tasks','connectors','reviewer_groups','policies','policy_sources','workspace_actions','workspace_artifacts','workspace_approvals','workspace_outbox','compilation_jobs']:
                    cursor.execute('SELECT id,organization_id,name,state,data,created_at FROM '+table+' ORDER BY created_at')
                    records[table]=cursor.fetchall()
                cursor.execute('SELECT id,organization_id,sequence,event_json,previous_hash,event_hash FROM workspace_audit ORDER BY organization_id,sequence')
                records['audit']=cursor.fetchall()
                result['records']=records
    demo=ROOT/'backend/data/demo_sales.db'
    if not demo.exists():result['demo']={'exists':False}
    else:
        with sqlite3.connect(demo.resolve().as_uri()+'?mode=ro',uri=True) as c:
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            result['demo']={'exists':True,'sales_table_exists':'sales_summary' in tables}
            if 'sales_summary' in tables:
                result['demo']['sales_rows']=c.execute('SELECT count(*) FROM sales_summary').fetchone()[0]
                result['demo']['sample']=c.execute('SELECT month,total_sales FROM sales_summary LIMIT 3').fetchall()
    text=json.dumps(result,default=str,indent=2)
    target=Path(sys.argv[1]) if len(sys.argv)>1 and not sys.argv[1].startswith('--') else None
    if target:target.write_text(text,encoding='utf-8');print(json.dumps({'saved':str(target),'counts':counts,'demo':result['demo']}))
    else:print(text)
except Exception as error:
    print(json.dumps({'error_type':type(error).__name__,'message':'Read-only check failed; connection details withheld.'}))
    sys.exit(1)
