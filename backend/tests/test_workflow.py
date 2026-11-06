from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
from app.database import Session
from app.models import Inventory, Run, Audit, Forecast
from app.agents import snapshot, workflow
from app.optimization import optimize,validate
from app.forecasting import predict

def proposal(client,headers):
    r=client.post('/api/optimization/run',headers=headers,json={'method':'milp'})
    assert r.status_code==202,r.text
    id=r.json()['id']
    detail=client.get(f'/api/optimization/runs/{id}',headers=headers).json()
    assert detail['status']=='waiting_for_approval',detail
    return id,detail

def test_auth_and_permissions(client,admin,analyst):
    assert client.get('/api/dashboard/summary').status_code in (401,403)
    assert client.post('/api/auth/login',json={'email':'none','password':'wrong'}).status_code==401
    assert client.post('/api/optimization/run',json={},headers=analyst).status_code==403
    assert client.get('/api/users',headers=analyst).status_code==403
    assert client.get('/api/auth/me',headers=admin).json()['role']=='Administrator'

def test_seed_and_dashboard(client,admin):
    s=client.get('/api/dashboard/summary',headers=admin).json()
    assert s['total_products']>=100 and s['total_stores']>=15 and s['total_warehouses']>=5
    assert s['forecast_accuracy'] is None or 0<=s['forecast_accuracy']<=100
    a=client.get('/api/dashboard/sales-performance',headers=admin).json()
    assert len(a)>=12
    assert client.get('/api/dashboard/summary',headers=admin).json()==s

def test_products_inventory(client,admin,analyst):
    p={'sku':'TEST-NEW','product_name':'Test item','category':'Electronics','unit_cost':'12.34','selling_price':'20.00'}
    r=client.post('/api/products',headers=admin,json=p);assert r.status_code==201,r.text
    id=r.json()['id'];p['product_name']='Updated item'
    assert client.put(f'/api/products/{id}',headers=admin,json=p).status_code==200
    assert client.get('/api/products?search=Updated',headers=admin).json()['total']==1
    assert client.delete(f'/api/products/{id}',headers=admin).status_code==204
    r=client.get('/api/inventory?status=low&page_size=5',headers=admin).json()
    assert r['items'] and all(i['status']=='low' for i in r['items'])
    inv=r['items'][0]
    body={k:inv[k] for k in ['quantity_on_hand','quantity_reserved','safety_stock','reorder_level','version']}
    assert client.put(f"/api/inventory/{inv['id']}",headers=analyst,json=body).status_code==403
    assert client.put(f"/api/inventory/{inv['id']}",headers=admin,json=body).status_code==200
    assert client.put(f"/api/inventory/{inv['id']}",headers=admin,json=body).status_code==409
    body['quantity_on_hand']=-1
    assert client.put(f"/api/inventory/{inv['id']}",headers=admin,json=body).status_code==422

def test_forecast_models(client,admin):
    for model in ['moving_average','exponential_smoothing','linear_regression','random_forest']:
        r=client.post('/api/forecast/run',headers=admin,json={'product_id':1,'location_id':21,'model':model,'horizon':7})
        assert r.status_code==200,r.text
        f=r.json()['items'][0]
        assert 0<=f['lower_bound']<=f['predicted_demand']<=f['upper_bound']
        assert f['mae']>=0 and 0<=f['confidence_score']<=1
    assert predict([], 'moving_average')[0]>0
    assert predict([0]*10,'linear_regression')[0]==0

def test_full_workflow_approval_rollback(client,admin,analyst):
    with Session() as db:
        initial={i.id:i.quantity_on_hand for i in db.scalars(select(Inventory))}
    id,run=proposal(client,admin)
    recs=client.get(f'/api/optimization/runs/{id}/recommendations',headers=admin).json()
    assert recs and run['total_allocated']>0
    logs=client.get(f'/api/agents/executions/{id}',headers=admin).json()
    assert len(set(e['agent_name'] for e in logs['executions']))==10
    assert all(e['status']=='completed' for e in logs['executions']) and len(logs['messages'])>=10
    with Session() as db:
        assert {i.id:i.quantity_on_hand for i in db.scalars(select(Inventory))}==initial
        snapshot_data=db.get(Run,id).snapshot
        validate(snapshot_data['inventory'],snapshot_data['locations'],recs)
    assert client.post(f'/api/optimization/runs/{id}/approve',headers=analyst).status_code==403
    assert client.post(f'/api/optimization/runs/{id}/approve',headers=admin).status_code==200
    assert client.post(f'/api/optimization/runs/{id}/approve',headers=admin).status_code==409
    with Session() as db:
        after={i.id:i.quantity_on_hand for i in db.scalars(select(Inventory))}
        assert sum(after.values())==sum(initial.values()) and after!=initial
        assert db.scalar(select(func.count(Audit.id)).where(Audit.entity_id==id,Audit.action=='approve'))==1
    assert client.get('/api/dashboard/summary',headers=admin).json()['estimated_savings']>0
    assert client.get('/api/transfers',headers=admin).json()
    assert client.post(f'/api/optimization/runs/{id}/rollback',headers=admin).status_code==200
    with Session() as db:assert {i.id:i.quantity_on_hand for i in db.scalars(select(Inventory))}==initial

def test_concurrent_duplicate_approval(client,admin):
    id,_=proposal(client,admin)
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes=list(pool.map(lambda _:client.post(f'/api/optimization/runs/{id}/approve',headers=admin).status_code,range(2)))
    assert sorted(codes)==[200,409]
    assert client.post(f'/api/optimization/runs/{id}/rollback',headers=admin).status_code==200

def test_stale_proposal(client,admin):
    id,_=proposal(client,admin)
    rec=client.get(f'/api/optimization/runs/{id}/recommendations',headers=admin).json()[0]
    with Session() as db:
        from app.models import Allocation
        a=db.get(Allocation,rec['id']);i=db.scalar(select(Inventory).where(Inventory.product_id==a.product_id,Inventory.location_id==a.source_location_id));i.version+=1;db.commit()
    assert client.post(f'/api/optimization/runs/{id}/approve',headers=admin).status_code==409
    assert client.post(f'/api/optimization/runs/{id}/reject',headers=admin).status_code==200

def test_all_simulations_are_isolated(client,admin):
    with Session() as db:
        before=[(r.id,r.quantity_on_hand,r.version) for r in db.scalars(select(Inventory))]
        count=db.scalar(select(func.count(Forecast.id)))
    for scenario in ['online_surge','store_surge','warehouse_shortage','supplier_delay','seasonal_surge','regional_imbalance','promotion_spike']:
        r=client.post('/api/simulation/run',headers=admin,json={'scenario':scenario,'multiplier':2})
        assert r.status_code==201,r.text
        s=r.json()['results'];assert s['optimized_shortage']<=s['baseline_shortage'] and s['inventory_changed'] is False
    with Session() as db:
        assert before==[(r.id,r.quantity_on_hand,r.version) for r in db.scalars(select(Inventory))]
        assert count==db.scalar(select(func.count(Forecast.id)))

def test_optimizer_edge_cases():
    locs=[{'id':1,'location_type':'warehouse','active':True,'latitude':0,'longitude':0,'storage_capacity':100,'fulfillment_capacity':100},{'id':2,'location_type':'store','active':True,'latitude':1,'longitude':1,'storage_capacity':12,'fulfillment_capacity':4}]
    inv=[{'id':1,'product_id':1,'location_id':1,'quantity_on_hand':30,'quantity_reserved':10,'safety_stock':10},{'id':2,'product_id':1,'location_id':2,'quantity_on_hand':10,'quantity_reserved':0,'safety_stock':2}]
    f=[{'product_id':1,'location_id':2,'predicted_demand':100,'channel':'offline'}]
    for method in ['milp','greedy']:
        result=optimize(inv,locs,f,{},method)
        assert result['total_allocated']==2
        validate(inv,locs,result['recommendations'])
        inv[0]['quantity_on_hand']=20
        assert optimize(inv,locs,f,{},method)['total_allocated']==0
        inv[0]['quantity_on_hand']=30
    try:validate(inv,locs,[{'product_id':1,'source_location_id':1,'destination_location_id':2,'allocated_quantity':20}]);assert False
    except ValueError:pass

def test_failed_workflow_is_recorded(client,admin,monkeypatch):
    import app.agents as agents
    def fail(*args,**kwargs):raise RuntimeError('Controlled forecasting failure')
    monkeypatch.setattr(agents,'forecast_all',fail)
    r=client.post('/api/optimization/run',headers=admin,json={});id=r.json()['id']
    d=client.get(f'/api/optimization/runs/{id}',headers=admin).json()
    assert d['status']=='failed' and 'Controlled' in d['error']

def test_events_websocket_and_reports(client,admin):
    token=admin['Authorization'].split()[1]
    with client.websocket_connect('/ws') as ws:
        ws.send_json({'token':token});assert ws.receive_json()['type']=='connected'
    assert client.get('/api/events',headers=admin).status_code==200
    assert 'text/csv' in client.get('/api/reports/export',headers=admin).headers['content-type']
    assert client.get('/api/analytics/forecast-accuracy',headers=admin).json()
    for path in ['inventory','allocation-performance','cost-savings']:
        assert client.get('/api/analytics/'+path,headers=admin).status_code==200
