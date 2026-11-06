"""Read-only production smoke checks using the documented synthetic login."""
import json
from urllib.request import Request,urlopen

BASE='https://nexus-retail-allocation.vercel.app'

def get(path,token=None):
    headers={'Authorization':'Bearer '+token} if token else {}
    with urlopen(Request(BASE+path,headers=headers),timeout=120) as response:
        return json.load(response)

if __name__=='__main__':
    health=get('/health')
    assert health['status']=='ok' and health['database']=='postgresql',health
    assert health['event_transport']=='database polling',health
    login=Request(BASE+'/api/auth/login',method='POST',headers={'Content-Type':'application/json'},data=json.dumps({'email':'admin@retail.local','password':'RetailDemo!2026'}).encode())
    with urlopen(login,timeout=120) as response:
        token=json.load(response)['access_token']
    summary=get('/api/dashboard/summary',token)
    assert summary['total_products']>=100 and summary['total_stores']>=15
    sales=get('/api/dashboard/sales-performance',token)
    assert len(sales)>=12
    agents=get('/api/agents',token)
    assert len(agents)==10
    outcomes={}
    for path in ['/api/inventory','/api/optimization/runs','/api/simulation/runs','/api/analytics/inventory','/api/analytics/forecast-accuracy','/api/analytics/allocation-performance','/api/analytics/cost-savings','/api/settings','/api/notifications']:
        result=get(path,token)
        outcomes[path]='ok'
    for path in ['/simulation','/inventory','/allocation']:
        with urlopen(BASE+path,timeout=60) as response:
            assert response.status==200 and 'text/html' in response.headers.get('Content-Type','')
            outcomes[path]='SPA route ok'
    print(json.dumps({'url':BASE,'health':health,'login':'passed','products':summary['total_products'],'inventory_units':summary['total_inventory'],'sales_months':len(sales),'agents':len(agents),'checks':outcomes},indent=2))
