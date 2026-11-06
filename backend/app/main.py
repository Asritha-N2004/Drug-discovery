import os, uuid, json, asyncio, logging, time
from contextlib import asynccontextmanager
from decimal import Decimal
from collections import defaultdict
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from .database import Session, get_db, now
from .models import *
from .schemas import *
from .security import current_user, managers, operators, require, token_for, decode_token, throttle
from .agents import AGENTS, workflow, serialize, snapshot
from .forecasting import forecast_all
from .optimization import optimize, route
from .transactions import apply_run, lock
from .analytics import summary, inventory_rows, sales_performance, inventory_health
from .events import bus
import bcrypt

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

@asynccontextmanager
async def lifespan(app):
    # Crash recovery is explicit: interrupted jobs never appear completed.
    if os.getenv('VERCEL'):
        # A new function instance is not a process crash. Never invalidate another instance's work.
        yield
        return
    with Session() as db:
        for run in db.scalars(select(Run).where(Run.status.in_(['queued','running']))):
            run.status='failed';run.error='Process restarted during execution; retry with a new run.'
        for ex in db.scalars(select(Execution).where(Execution.status=='running')):
            ex.status='failed';ex.error_message='Process restarted during execution'
        db.commit()
    yield

app=FastAPI(title='Nexus Retail • Multi-Agent Inventory API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','),allow_credentials=False,allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Authorization','Content-Type'])

@app.middleware('http')
async def request_log(request,call_next):
    start=time.perf_counter();response=await call_next(request)
    logging.info(json.dumps({'method':request.method,'path':request.url.path,'status':response.status_code,'duration_ms':round((time.perf_counter()-start)*1000,2)}))
    return response

@app.exception_handler(IntegrityError)
async def integrity_error(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409,content={'detail':'Conflicting record or database constraint violation'})

def get_or_404(db,model,id):
    obj=db.get(model,id)
    if obj is None: raise HTTPException(404,f'{model.__name__} not found')
    return obj

def page(items,page=1,page_size=25):
    return {'items':items[(page-1)*page_size:page*page_size],'total':len(items),'page':page,'page_size':page_size}

def audit(db,user,action,entity,id,before,after):
    db.add(Audit(user_id=user.id,action=action,entity_type=entity,entity_id=str(id),previous_value=before,new_value=after))

def safe_dict(obj):
    return {k:float(v) if isinstance(v,Decimal) else v for k,v in serialize(obj).items()}

@app.get('/health')
def health(db=Depends(get_db)):
    db.execute(text('SELECT 1'));return {'status':'ok','database':db.bind.dialect.name,'event_transport':'database polling' if os.getenv('VERCEL') else 'websocket + polling','dataset':'synthetic'}

@app.post('/api/auth/login')
def login(body:Login,request:Request,db=Depends(get_db)):
    throttle(request.client.host if request.client else 'unknown')
    user=db.scalar(select(User).where(User.email==body.email))
    if not user or not user.active or not bcrypt.checkpw(body.password.encode(),user.password_hash.encode()): raise HTTPException(401,'Incorrect email or password')
    return {'access_token':token_for(user),'token_type':'bearer','user':{'id':user.id,'name':user.name,'email':user.email,'role':db.get(Role,user.role_id).name}}

@app.get('/api/auth/me')
def me(user=Depends(current_user),db=Depends(get_db)):
    return {'id':user.id,'name':user.name,'email':user.email,'role':db.get(Role,user.role_id).name}

@app.put('/api/auth/me')
def update_me(body:ProfileUpdate,user=Depends(current_user),db=Depends(get_db)):
    user.name=body.name;db.commit();return {'name':user.name}

@app.get('/api/dashboard/summary')
def dashboard_summary(user=Depends(current_user),db=Depends(get_db)): return summary(db)

@app.get('/api/dashboard/inventory-health')
def dashboard_health(user=Depends(current_user),db=Depends(get_db)): return inventory_health(db)

@app.get('/api/dashboard/sales-performance')
def dashboard_sales(user=Depends(current_user),db=Depends(get_db)): return sales_performance(db)

@app.get('/api/dashboard/channel-performance')
def channel_performance(user=Depends(current_user),db=Depends(get_db)):
    rows=inventory_rows(db)
    return [{'name':t.title(),'value':sum(r['quantity_on_hand'] for r in rows if r['location_type']==t)} for t in ('online','store','warehouse','distribution_center')]

@app.get('/api/products')
def products(search:str='',category:str='',page_no:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=200),sort:Literal['sku','product_name','category']='sku',user=Depends(current_user),db=Depends(get_db)):
    q=select(Product).where(Product.active==True)
    if search: q=q.where((Product.product_name.ilike(f'%{search}%')) | (Product.sku.ilike(f'%{search}%')))
    if category:q=q.where(Product.category==category)
    return page([safe_dict(p) for p in db.scalars(q.order_by(getattr(Product,sort)))],page_no,page_size)

@app.post('/api/products',status_code=201)
def create_product(body:ProductInput,user=Depends(managers),db=Depends(get_db)):
    p=Product(**body.model_dump());db.add(p);db.flush()
    for l in db.scalars(select(Location).where(Location.active==True)):
        db.add(Inventory(product_id=p.id,location_id=l.id,quantity_on_hand=0,quantity_reserved=0,safety_stock=10,reorder_level=30))
    audit(db,user,'create','product',p.id,{},safe_dict(p));db.commit();return safe_dict(p)

@app.get('/api/products/{id}')
def product(id:int,user=Depends(current_user),db=Depends(get_db)):return safe_dict(get_or_404(db,Product,id))

@app.put('/api/products/{id}')
def update_product(id:int,body:ProductInput,user=Depends(managers),db=Depends(get_db)):
    p=get_or_404(db,Product,id);before=safe_dict(p)
    for k,v in body.model_dump().items():setattr(p,k,v)
    p.updated_at=now();audit(db,user,'update','product',id,before,safe_dict(p));db.commit();return safe_dict(p)

@app.delete('/api/products/{id}',status_code=204)
def delete_product(id:int,user=Depends(managers),db=Depends(get_db)):
    p=get_or_404(db,Product,id);p.active=False;audit(db,user,'deactivate','product',id,{'active':True},{'active':False});db.commit()

@app.get('/api/inventory')
def inventory(search:str='',status:str='',location_type:str='',category:str='',location_id:int|None=None,page_no:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=2500),sort:Literal['sku','quantity_available','product_name','location_name']='sku',descending:bool=False,user=Depends(current_user),db=Depends(get_db)):
    rows=[r for r in inventory_rows(db) if (not search or search.lower() in (r['sku']+' '+r['product_name']).lower()) and (not status or r['status']==status) and (not location_type or r['location_type']==location_type) and (not category or r['category']==category) and (not location_id or r['location_id']==location_id)]
    return page(sorted(rows,key=lambda r:r[sort],reverse=descending),page_no,page_size)

@app.get('/api/inventory/low-stock')
def low_stock(user=Depends(current_user),db=Depends(get_db)):return [r for r in inventory_rows(db) if r['status'] in ('low','stockout')]

@app.get('/api/inventory/overstock')
def overstock(user=Depends(current_user),db=Depends(get_db)):return [r for r in inventory_rows(db) if r['status']=='overstock']

@app.get('/api/inventory/{product_id}')
def product_inventory(product_id:int,user=Depends(current_user),db=Depends(get_db)):
    get_or_404(db,Product,product_id);return [r for r in inventory_rows(db) if r['product_id']==product_id]

@app.put('/api/inventory/{id}')
def update_inventory(id:int,body:InventoryInput,user=Depends(operators),db=Depends(get_db)):
    lock(db)
    rows=list(db.scalars(select(Inventory).order_by(Inventory.id).with_for_update()))
    inv=next((r for r in rows if r.id==id),None)
    if not inv:raise HTTPException(404,'Inventory not found')
    if inv.version!=body.version:raise HTTPException(409,'Stock changed; reload before editing')
    if body.quantity_reserved>body.quantity_on_hand:raise HTTPException(422,'Reserved stock exceeds on-hand')
    location=get_or_404(db,Location,inv.location_id)
    if sum(r.quantity_on_hand for r in rows if r.location_id==inv.location_id and r.id!=id)+body.quantity_on_hand>location.storage_capacity:raise HTTPException(409,'Location capacity exceeded')
    before=serialize(inv)
    for k,v in body.model_dump(exclude={'version'}).items():setattr(inv,k,v)
    inv.version+=1;inv.last_updated=now();audit(db,user,'adjust','inventory',id,before,serialize(inv));db.commit()
    bus.publish('inventory_alert',{'id':id,'available':inv.quantity_available});return serialize(inv)

@app.get('/api/locations')
def locations(user=Depends(current_user),db=Depends(get_db)):
    rows=inventory_rows(db)
    return [{**serialize(l),'on_hand':sum(r['quantity_on_hand'] for r in rows if r['location_id']==l.id),'utilization':round(100*sum(r['quantity_on_hand'] for r in rows if r['location_id']==l.id)/l.storage_capacity,2)} for l in db.scalars(select(Location))]

@app.post('/api/forecast/run')
def run_forecast(body:ForecastInput,user=Depends(managers),db=Depends(get_db)):
    id=str(uuid.uuid4());rows=forecast_all(db,id,body.model,body.horizon,body.product_id,body.location_id);db.commit()
    bus.publish('forecast_completed',{'run_id':id,'count':len(rows)});return {'run_id':id,'count':len(rows),'items':rows}

@app.get('/api/forecast')
def forecasts(product_id:int|None=None,location_id:int|None=None,channel:str='',run_id:str='',user=Depends(current_user),db=Depends(get_db)):
    if not run_id:
        latest=select(Forecast.run_id)
        if product_id:latest=latest.where(Forecast.product_id==product_id)
        if location_id:latest=latest.where(Forecast.location_id==location_id)
        if channel:latest=latest.where(Forecast.channel==channel)
        run_id=db.scalar(latest.order_by(Forecast.id.desc()).limit(1))
    q=select(Forecast).where(Forecast.run_id==run_id)
    if product_id:q=q.where(Forecast.product_id==product_id)
    if location_id:q=q.where(Forecast.location_id==location_id)
    if channel:q=q.where(Forecast.channel==channel)
    return [serialize(f) for f in db.scalars(q)]

@app.get('/api/forecast/{product_id}')
def forecast_product(product_id:int,user=Depends(current_user),db=Depends(get_db)):
    return forecasts(product_id=product_id,location_id=None,channel='',run_id='',user=user,db=db)

@app.get('/api/sales/history')
def history(product_id:int,location_id:int|None=None,user=Depends(current_user),db=Depends(get_db)):
    q=select(Sale.sale_date,func.sum(Sale.quantity_sold)).where(Sale.product_id==product_id)
    if location_id:q=q.where(Sale.location_id==location_id)
    return [{'date':d,'quantity':n} for d,n in db.execute(q.group_by(Sale.sale_date).order_by(Sale.sale_date))]

@app.get('/api/agents')
@app.get('/api/agents/status')
def agents(user=Depends(current_user),db=Depends(get_db)):
    output=[]
    for id,name,role in AGENTS:
        ex=db.scalar(select(Execution).where(Execution.agent_name==id).order_by(Execution.id.desc()).limit(1))
        count=db.scalar(select(func.count(Execution.id)).where(Execution.agent_name==id,Execution.status=='completed'))
        output.append({'id':id,'name':name,'role':role,'status':ex.status if ex else 'idle','tasks_completed':count,'last_execution':serialize(ex) if ex else None})
    return output

@app.get('/api/agents/logs')
def agent_logs(run_id:str='',user=Depends(current_user),db=Depends(get_db)):
    q=select(Execution).order_by(Execution.id.desc())
    m=select(Message).order_by(Message.id.desc())
    if run_id:q=q.where(Execution.execution_id==run_id);m=m.where(Message.execution_id==run_id)
    return {'executions':[serialize(e) for e in db.scalars(q.limit(100))],'messages':[serialize(e) for e in db.scalars(m.limit(100))]}

@app.get('/api/agents/executions/{execution_id}')
def executions(execution_id:str,user=Depends(current_user),db=Depends(get_db)):return agent_logs(execution_id,user,db)

@app.post('/api/optimization/run',status_code=202)
@app.post('/api/agents/run',status_code=202)
def start_run(body:RunInput,tasks:BackgroundTasks,user=Depends(managers),db=Depends(get_db)):
    throttle(f'run:{user.id}')
    id=str(uuid.uuid4());run=Run(id=id,run_name=body.run_name,status='queued');db.add(run)
    audit(db,user,'start','optimization_run',id,{},body.model_dump());db.commit()
    defaults=db.get(Setting,'forecast').value
    args=(id,body.model if 'model' in body.model_fields_set else defaults['model'],body.horizon if 'horizon' in body.model_fields_set else defaults['horizon'],body.method,body.agent_id)
    if os.getenv('VERCEL'):
        # Execute inside the function lifetime; persisted statuses remain observable by polling.
        workflow(*args)
        db.expire_all()
        return {'id':id,'status':db.get(Run,id).status}
    tasks.add_task(workflow,*args)
    return {'id':id,'status':'queued'}

@app.get('/api/optimization/runs')
def runs(user=Depends(current_user),db=Depends(get_db)):return [{k:v for k,v in safe_dict(r).items() if k!='snapshot'} for r in db.scalars(select(Run).order_by(Run.created_at.desc()).limit(100))]

@app.get('/api/optimization/runs/{run_id}')
def run_detail(run_id:str,user=Depends(current_user),db=Depends(get_db)):
    r=get_or_404(db,Run,run_id);out=safe_dict(r);out.pop('snapshot');out['baseline_inventory_units']=sum(i['quantity_on_hand'] for i in r.snapshot.get('inventory',[]));return out

@app.get('/api/optimization/runs/{run_id}/recommendations')
def recommendations(run_id:str,user=Depends(current_user),db=Depends(get_db)):
    r=get_or_404(db,Run,run_id)
    products={p.id:p for p in db.scalars(select(Product))};locs={l.id:l for l in db.scalars(select(Location))};old={(i['product_id'],i['location_id']):i for i in r.snapshot.get('inventory',[])}
    output=[]
    movements=list(db.scalars(select(Allocation).where(Allocation.allocation_run_id==run_id)))
    receipts=defaultdict(int)
    for a in movements:receipts[(a.product_id,a.destination_location_id)]+=a.allocated_quantity
    for a in movements:
        before=old.get((a.product_id,a.destination_location_id),{}).get('quantity_on_hand',0)
        output.append({**safe_dict(a),'product_name':products[a.product_id].product_name,'sku':products[a.product_id].sku,'source':locs[a.source_location_id].location_name,'destination':locs[a.destination_location_id].location_name,'before':before,'after':before+receipts[(a.product_id,a.destination_location_id)]})
    return output

@app.post('/api/optimization/runs/{run_id}/approve')
def approve(run_id:str,user=Depends(managers),db=Depends(get_db)):return apply_run(db,run_id,user.id)

@app.post('/api/optimization/runs/{run_id}/rollback')
def rollback(run_id:str,user=Depends(managers),db=Depends(get_db)):return apply_run(db,run_id,user.id,True)

@app.post('/api/optimization/runs/{run_id}/reject')
def reject(run_id:str,user=Depends(managers),db=Depends(get_db)):
    lock(db);r=db.scalar(select(Run).where(Run.id==run_id).with_for_update())
    if not r:raise HTTPException(404,'Run not found')
    if r.status!='waiting_for_approval':raise HTTPException(409,'Run is not awaiting approval')
    r.status='rejected'
    for a in db.scalars(select(Allocation).where(Allocation.allocation_run_id==run_id)):a.allocation_status='rejected'
    audit(db,user,'reject','optimization_run',run_id,{'status':'waiting_for_approval'},{'status':'rejected'});db.commit();bus.publish('optimization_status',{'id':run_id,'status':'rejected'});return safe_dict(r)

@app.get('/api/transfers')
def transfers(user=Depends(current_user),db=Depends(get_db)):
    locs={l.id:l.location_name for l in db.scalars(select(Location))};products={p.id:p.product_name for p in db.scalars(select(Product))}
    return [{**safe_dict(t),'source':locs[t.source_location_id],'destination':locs[t.destination_location_id],'product_name':products[t.product_id]} for t in db.scalars(select(Transfer).order_by(Transfer.id.desc()))]

@app.post('/api/transfers',status_code=201)
def create_transfer(body:TransferInput,user=Depends(operators),db=Depends(get_db)):
    # Manual transfers enter the same explicit proposal/approval workflow.
    from .optimization import validate
    inventory,locations=snapshot(db);locs={l['id']:l for l in locations}
    if body.source_location_id not in locs or body.destination_location_id not in locs:raise HTTPException(404,'Location not found')
    a={'product_id':body.product_id,'source_location_id':body.source_location_id,'destination_location_id':body.destination_location_id,'allocated_quantity':body.quantity}
    try:validate(inventory,locations,[a])
    except ValueError as e:raise HTTPException(409,str(e))
    cost,eta=route(locs[body.source_location_id],locs[body.destination_location_id]);id=str(uuid.uuid4())
    db.add(Run(id=id,run_name='Manual transfer proposal',status='waiting_for_approval',snapshot={'inventory':inventory,'locations':locations},total_allocated=body.quantity,total_cost=body.quantity*cost,results={}))
    db.flush();db.add(Allocation(allocation_run_id=id,**a,sales_channel='online' if locs[body.destination_location_id]['location_type']=='online' else 'offline',estimated_cost=body.quantity*cost,eta_hours=eta,reason='Explicit manual transfer proposal; pending approval.'))
    audit(db,user,'propose_transfer','optimization_run',id,{},body.model_dump());db.commit();return {'run_id':id,'status':'waiting_for_approval'}

@app.put('/api/transfers/{id}/status')
def transfer_status(id:int,body:TransferStatus,user=Depends(operators),db=Depends(get_db)):
    lock(db);t=db.scalar(select(Transfer).where(Transfer.id==id).with_for_update())
    if not t:raise HTTPException(404,'Transfer not found')
    allowed={'scheduled':'in_transit','in_transit':'delivered'}
    if allowed.get(t.status)!=body.status:raise HTTPException(409,'Invalid transfer state transition')
    previous=t.status;t.status=body.status;audit(db,user,'transfer_status','transfer',id,{'status':previous},{'status':t.status});db.commit();bus.publish('transfer_status',{'id':id,'status':t.status});return safe_dict(t)

@app.get('/api/analytics/inventory')
def analytics_inventory(user=Depends(current_user),db=Depends(get_db)):return {'summary':summary(db),'health':inventory_health(db)}

@app.get('/api/analytics/forecast-accuracy')
def accuracy(user=Depends(current_user),db=Depends(get_db)):
    return [{'model':model,'mae':float(mae),'wape':float(wape),'accuracy':round(max(0,1-wape)*100,2),'predictions':count} for model,mae,wape,count in db.execute(select(Forecast.model_name,func.avg(Forecast.mae),func.avg(Forecast.wape),func.count(Forecast.id)).group_by(Forecast.model_name))]

@app.get('/api/analytics/allocation-performance')
def performance(user=Depends(current_user),db=Depends(get_db)):
    return [{'id':r.id,'date':r.created_at,'status':r.status,'allocated':r.total_allocated,'cost':float(r.total_cost),**{k:v for k,v in r.results.items() if k!='committed_versions'}} for r in db.scalars(select(Run).order_by(Run.created_at))]

@app.get('/api/analytics/cost-savings')
def savings(user=Depends(current_user),db=Depends(get_db)):
    return {'estimated_savings':summary(db)['estimated_savings'],'basis':'Modeled cost avoidance; not realized accounting profit','runs':performance(user,db)}

@app.post('/api/simulation/run',status_code=201)
def simulation(body:SimulationInput,user=Depends(managers),db=Depends(get_db)):
    inventory,locations=snapshot(db);id=str(uuid.uuid4())
    # Forecast persistence is isolated: only the simulation result is saved.
    nested=db.begin_nested();fs=forecast_all(db,id);nested.rollback()
    initial=sum(r['quantity_on_hand'] for r in inventory);locs={l['id']:l for l in locations}
    if body.scenario in ('warehouse_shortage','supplier_delay'):
        for r in inventory:
            if locs[r['location_id']]['location_type'] in ('warehouse','distribution_center'):
                r['quantity_on_hand']=max(r['quantity_reserved']+r['safety_stock'],int(r['quantity_on_hand']/(body.multiplier*(1.5 if body.scenario=='supplier_delay' else 1))))
    for f in fs:
        affected=(body.scenario in ('seasonal_surge','promotion_spike') or body.scenario=='online_surge' and f['channel']=='online' or body.scenario=='store_surge' and f['channel']=='offline' or body.scenario=='regional_imbalance' and locs[f['location_id']]['region']=='Mumbai')
        if affected:f['predicted_demand']*=body.multiplier
    result=optimize(inventory,locations,fs,db.get(Setting,'optimization').value)
    result.update({'initial_inventory':initial,'scenario_inventory':sum(r['quantity_on_hand'] for r in inventory),'simulated_demand':round(sum(f['predicted_demand'] for f in fs)),'baseline_cost':round(result['baseline_shortage']*db.get(Setting,'optimization').value['stockout_penalty'],2),'optimized_cost':result['objective_value'],'inventory_changed':False,'agent_decisions':{'demand':'Scenario multiplier applied to affected channel forecasts','warehouse':'Scenario supply constraint applied','allocation':result['solver'],'risk':{'remaining_shortage':result['optimized_shortage']},'supervisor':'Sandbox only; no inventory commit'}})
    s=Simulation(id=id,scenario=body.scenario,parameters=body.model_dump(),results=result);db.add(s);db.commit();return serialize(s)

@app.get('/api/simulation/runs')
def simulations(user=Depends(current_user),db=Depends(get_db)):return [serialize(s) for s in db.scalars(select(Simulation).order_by(Simulation.created_at.desc()).limit(50))]

@app.get('/api/simulation/results/{id}')
def simulation_result(id:str,user=Depends(current_user),db=Depends(get_db)):return serialize(get_or_404(db,Simulation,id))

@app.get('/api/notifications')
def notifications(user=Depends(current_user),db=Depends(get_db)):
    pref=db.get(Setting,f'notifications:{user.id}') or db.get(Setting,'notifications')
    return [serialize(n) for n in db.scalars(select(Notification).order_by(Notification.id.desc()).limit(100)) if pref.value.get('inventory_alerts',True) and n.severity=='warning' or pref.value.get('workflow_updates',True) and n.severity!='warning']

@app.put('/api/notifications/{id}/read')
def mark_read(id:int,user=Depends(current_user),db=Depends(get_db)):
    n=get_or_404(db,Notification,id);n.read=True;db.commit();return serialize(n)

@app.get('/api/settings')
def settings(user=Depends(current_user),db=Depends(get_db)):
    result={s.key:s.value for s in db.scalars(select(Setting).where(Setting.key.in_(['optimization','forecast','notifications'])))}
    pref=db.get(Setting,f'notifications:{user.id}')
    if pref:result['notifications']=pref.value
    return result

@app.put('/api/settings/notifications')
def update_notification_settings(body:NotificationSettings,user=Depends(current_user),db=Depends(get_db)):
    key=f'notifications:{user.id}';s=db.get(Setting,key)
    if s:s.value=body.model_dump()
    else:db.add(Setting(key=key,value=body.model_dump()))
    db.commit();return body.model_dump()

@app.put('/api/settings/optimization')
def update_settings(body:OptimizationSettings,user=Depends(managers),db=Depends(get_db)):
    s=get_or_404(db,Setting,'optimization');before=s.value;s.value=body.model_dump();audit(db,user,'settings','setting',s.key,before,s.value);db.commit();return s.value

@app.put('/api/settings/forecast')
def update_forecast_settings(body:ForecastInput,user=Depends(managers),db=Depends(get_db)):
    s=get_or_404(db,Setting,'forecast');s.value=body.model_dump(exclude={'product_id','location_id'});db.commit();return s.value

@app.get('/api/users')
def users(user=Depends(require('Administrator')),db=Depends(get_db)):
    return [{'id':u.id,'name':u.name,'email':u.email,'role_id':u.role_id,'role':db.get(Role,u.role_id).name} for u in db.scalars(select(User))]

@app.put('/api/users/{id}/role')
def user_role(id:int,body:RoleUpdate,user=Depends(require('Administrator')),db=Depends(get_db)):
    if id==user.id:raise HTTPException(409,'Cannot change your own administrator role')
    u=get_or_404(db,User,id);before=u.role_id;u.role_id=body.role_id;audit(db,user,'role_change','user',id,{'role_id':before},{'role_id':u.role_id});db.commit();return {'id':id,'role_id':u.role_id}

@app.get('/api/audit')
def audits(user=Depends(managers),db=Depends(get_db)):return [serialize(a) for a in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(100))]

@app.get('/api/purchase-orders')
def purchase_orders(user=Depends(current_user),db=Depends(get_db)):return [serialize(p) for p in db.scalars(select(PurchaseOrder))]

@app.get('/api/events')
def events(after:int=0,user=Depends(current_user)):return {'events':bus.since(after),'cursor':bus.sequence}

@app.websocket('/ws')
async def websocket(ws:WebSocket):
    await ws.accept()
    try:
        # Authenticate in the first frame so JWTs never appear in access-log URLs.
        frame=await asyncio.wait_for(ws.receive_json(),timeout=5)
        id=decode_token(frame.get('token',''))
        with Session() as db:
            user=db.get(User,id)
            if not user or not user.active:raise HTTPException(401,'Inactive user')
        cursor=bus.sequence
        await ws.send_json({'type':'connected','cursor':cursor})
        while True:
            for e in bus.since(cursor):await ws.send_json(e);cursor=e['sequence']
            await asyncio.sleep(.5)
    except (WebSocketDisconnect,RuntimeError):pass
    except (HTTPException,asyncio.TimeoutError,ValueError):await ws.close(code=1008)

@app.get('/api/reports/export')
def export_report(run_id:str='',user=Depends(current_user),db=Depends(get_db)):
    import csv,io
    rows=recommendations(run_id,user,db) if run_id else inventory_rows(db)
    stream=io.StringIO()
    if rows:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader()
        for row in rows:
            writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()})
    return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=inventory-report.csv'})
