import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from pydantic import ValidationError
from workspace.rules import Rule,RuleSet,matching,validate_rules
from workspace.sources import validate_url,extract,MAX_FILE

SOURCE='a'*32
RESOURCE='b'*32
TASK='c'*32
GROUP='d'*32

def rule(**changes):
    data={'id':'sales-read','role':'data_analyst','tool':'database.read','resource':RESOURCE,'tasks':[TASK],
          'arguments':{'max_rows':10},'decision':'ALLOW','source':{'source_id':SOURCE,'revision':1,'segment':1,'passage':'Analysts may read sales data.'}}
    data.update(changes)
    return Rule.model_validate(data)

def context():
    return ({SOURCE:{'revision':1,'segments':[{'index':1,'text':'Analysts may read sales data.'}]}},
            {RESOURCE:{'kind':'demo_sales','destinations':[]}}, {TASK:{'roles':['data_analyst']}}, {GROUP})

def test_valid_cited_rule():
    assert validate_rules([rule()],*context())==[]

@pytest.mark.parametrize('change',[
    {'role':'Unknown Role'}, {'tool':'shell.execute'}, {'resource':'../../private'},
    {'arguments':{'max_rows':'10'}},{'arguments':{'sql':'DROP TABLE users'}},{'decision':'safe'},
])
def test_invalid_rule_language(change):
    with pytest.raises(ValidationError):rule(**change)

@pytest.mark.parametrize('change',[
    {'assumptions':['verify authorization']},{'ambiguity':['financial amount unspecified']},
    {'source':{'source_id':SOURCE,'revision':2,'segment':1,'passage':'Analysts may read sales data.'}},
    {'source':{'source_id':SOURCE,'revision':1,'segment':1,'passage':'Invented permission'}},
    {'tasks':['other']},{'decision':'ESCALATE','reviewer_group':'not-a-group'},
])
def test_ambiguous_and_unbound_sources_fail_publication(change):
    assert validate_rules([rule(**change)],*context())

def test_rule_precedence_and_default_deny():
    action={'tool':'database.read','resource':RESOURCE,'task_id':TASK,'arguments':{'limit':3}}
    allow=rule();escalate=rule(id='review',decision='ESCALATE',reviewer_group=GROUP);block=rule(id='deny',decision='BLOCK')
    assert matching([], 'data_analyst',action)[0]=='BLOCK'
    assert matching([allow,escalate], 'data_analyst',action)[0]=='ESCALATE'
    assert matching([allow,escalate,block], 'data_analyst',action)[0]=='BLOCK'
    assert matching([allow], 'customer_support',action)[0]=='BLOCK'
    action['arguments']['limit']=11
    assert matching([allow], 'data_analyst',action)[0]=='BLOCK'

def test_review_group_conflict():
    a=rule(id='a',decision='ESCALATE',reviewer_group=GROUP)
    b=rule(id='b',decision='ESCALATE',reviewer_group='e'*32)
    sources,connectors,tasks,groups=context();groups.add('e'*32)
    assert any('different reviewer groups' in e for e in validate_rules([a,b],sources,connectors,tasks,groups))

def resolver(ip):
    return lambda *args,**kwargs:[(2,1,6,'',(ip,443))]

@pytest.mark.parametrize('url,ip',[
    ('http://policy.example.test/p','8.8.8.8'),('https://policy.example.test/p','127.0.0.1'),
    ('https://policy.example.test/p','10.0.0.1'),('https://policy.example.test/p','169.254.169.254'),
    ('https://policy.example.test/p','::1'),('https://policy.example.test/p','fc00::1'),
    ('https://user:pass@policy.example.test/p','8.8.8.8'),('https://evil.example.test/p','8.8.8.8'),
    ('https://policy.example.test:444/p','8.8.8.8'),
])
def test_ssrf_boundaries(url,ip):
    with pytest.raises(ValueError):validate_url(url,{'policy.example.test'},resolver(ip))

def test_dns_public_pin_and_mixed_results():
    parsed,ips=validate_url('https://policy.example.test/p',{'policy.example.test'},resolver('8.8.8.8'))
    assert parsed.hostname=='policy.example.test' and ips==['8.8.8.8']
    with pytest.raises(ValueError):validate_url('https://policy.example.test/p',{'policy.example.test'},lambda *a,**k:resolver('8.8.8.8')()+resolver('127.0.0.1')())

def test_text_limits_and_binary_rejection():
    assert extract(b'# Policy\nAnalysts may read.', '.md')[0]['index']==1
    for data,extension in [(b'x'*(MAX_FILE+1),'.txt'),(b'\x00binary','.txt'),(b'code','.exe'),(b'not pdf','.pdf')]:
        with pytest.raises(ValueError):extract(data,extension)

def test_redirect_rechecks_dns(monkeypatch):
    import workspace.sources as module
    calls=[]
    def validation(url,hosts):
        calls.append(url)
        return validate_url(url,hosts,resolver('8.8.8.8' if len(calls)==1 else '127.0.0.1'))
    class Redirect:
        status=302
        def getheader(self,name,default=None):return '/private' if name=='Location' else default
    class Connection:
        def __init__(self,*args):pass
        def request(self,*args,**kwargs):pass
        def getresponse(self):return Redirect()
        def close(self):pass
    monkeypatch.setattr(module,'validate_url',validation);monkeypatch.setattr(module,'PinnedHTTPS',Connection)
    with pytest.raises(ValueError):module.fetch('https://policy.example.test/start',{'policy.example.test'})
    assert len(calls)==2
