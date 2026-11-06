import time, uuid, logging
from sqlalchemy import select, func
from .database import Session, now
from .models import Inventory, Location, Setting, Run, Execution, Message, Allocation, Notification
from .forecasting import forecast_all
from .optimization import optimize, validate, route
from .events import bus

AGENTS=[('supervisor','Supervisor / Coordinator','Validate and coordinate workflows'),('demand','Demand Forecasting','Predict channel demand and uncertainty'),('inventory','Inventory Monitoring','Detect stock health and reservation issues'),('online','Online Channel','Calculate e-commerce requirements'),('offline','Offline Store','Calculate local replenishment'),('warehouse','Warehouse','Identify transferable supply'),('pricing','Pricing and Promotion','Suggest slow-stock promotions'),('risk','Risk Management','Identify shortages and bottlenecks'),('allocation','Inventory Allocation','Minimize constrained inventory costs'),('logistics','Logistics','Estimate routes, delivery times and costs')]

def serialize(obj):
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}

def snapshot(db):
    return [serialize(r) for r in db.scalars(select(Inventory).order_by(Inventory.id))], [serialize(l) for l in db.scalars(select(Location).where(Location.active==True))]

def execute_agent(db,run_id,agent,input_data,fn):
    ex=Execution(agent_name=agent,execution_id=run_id,status='running',input_summary=input_data)
    db.add(ex);db.commit();start=time.perf_counter()
    bus.publish('agent_execution',{'run_id':run_id,'agent':agent,'status':'running'})
    try:
        output=fn()
        ex.status='completed';ex.output_summary=output;ex.confidence=output.get('confidence')
        db.add(Message(execution_id=run_id,sender=agent,recipient='supervisor' if agent!='supervisor' else 'all',payload=output))
        ex.execution_duration=round(time.perf_counter()-start,4);db.commit()
        bus.publish('agent_execution',{'run_id':run_id,'agent':agent,'status':'completed','output':output})
        return output
    except Exception as e:
        db.rollback();ex=db.get(Execution,ex.id);ex.status='failed';ex.error_message=str(e);db.commit()
        bus.publish('agent_execution',{'run_id':run_id,'agent':agent,'status':'failed','error':str(e)})
        raise

def workflow(run_id,model='exponential_smoothing',horizon=7,method='milp',only_agent=None):
    with Session() as db:
        run=db.get(Run,run_id)
        try:
            run.status='running';db.commit()
            inventory,locations=snapshot(db)
            weights=db.get(Setting,'optimization').value
            shared={'inventory':inventory,'locations':locations}
            execute_agent(db,run_id,'supervisor',{'model':model,'horizon':horizon},lambda:{'state':'forecasting','tasks':[a[0] for a in AGENTS[1:]],'mode':'individual_with_dependencies' if only_agent else 'full_workflow'})
            def demand_task():
                forecasts=forecast_all(db,run_id,model,horizon)
                shared['forecasts']=forecasts
                return {'predictions':len(forecasts),'expected_demand':round(sum(f['predicted_demand'] for f in forecasts)),'confidence':round(sum(f['confidence_score'] for f in forecasts)/max(1,len(forecasts)),3)}
            execute_agent(db,run_id,'demand',{'model':model,'horizon':horizon},demand_task)
            forecasts=shared['forecasts']
            low=[r for r in inventory if r['quantity_on_hand']-r['quantity_reserved']<r['reorder_level']]
            execute_agent(db,run_id,'inventory',{'records':len(inventory)},lambda:{'low_stock':len(low),'overstock':sum(r['quantity_on_hand']>r['reorder_level']*5 for r in inventory),'stock_health_score':round(100*(1-len(low)/max(1,len(inventory))),1),'inconsistencies':sum(r['quantity_reserved']>r['quantity_on_hand'] for r in inventory)})
            for agent,channel in [('online','online'),('offline','offline')]:
                fs=[f for f in forecasts if f['channel']==channel]
                execute_agent(db,run_id,agent,{'forecast_run':run_id},lambda fs=fs,channel=channel:{'channel':channel,'expected_demand':round(sum(f['predicted_demand'] for f in fs)),'destinations':len(set(f['location_id'] for f in fs)),'requirements':[{'product_id':f['product_id'],'location_id':f['location_id'],'demand':f['predicted_demand']} for f in fs[:20]]})
            source_ids={l['id'] for l in locations if l['location_type'] in ('warehouse','distribution_center')}
            execute_agent(db,run_id,'warehouse',{'source_locations':len(source_ids)},lambda:{'available_to_transfer':sum(max(0,r['quantity_on_hand']-r['quantity_reserved']-r['safety_stock']) for r in inventory if r['location_id'] in source_ids),'sources':sorted(source_ids)})
            execute_agent(db,run_id,'pricing',{'inventory_records':len(inventory)},lambda:{'suggestions':[{'product_id':r['product_id'],'location_id':r['location_id'],'suggested_discount_percent':10,'estimated_uplift':1.15} for r in inventory if r['location_id'] not in source_ids and r['quantity_on_hand']>5*r['reorder_level']][:30],'automatic_price_changes':False})
            execute_agent(db,run_id,'risk',{'low_stock_records':len(low)},lambda:{'stockout_alerts':len(low),'risk_score':round(len(low)/max(1,len(inventory)),3),'bottlenecks':[l['id'] for l in locations if sum(r['quantity_on_hand'] for r in inventory if r['location_id']==l['id'])>l['storage_capacity']*.9]})
            result=optimize(inventory,locations,forecasts,weights,method)
            execute_agent(db,run_id,'allocation',{'forecast_run':run_id,'constraints':'reservations,safety,storage,fulfillment,integers'},lambda:{k:v for k,v in result.items() if k!='recommendations'})
            execute_agent(db,run_id,'logistics',{'proposed_routes':len(result['recommendations'])},lambda:{'transfer_cost':result['total_cost'],'max_eta_hours':max((a['eta_hours'] for a in result['recommendations']),default=0),'feasible_routes':len(result['recommendations'])})
            validate(inventory,locations,result['recommendations'])
            execute_agent(db,run_id,'supervisor',{'phase':'validation'},lambda:{'state':'waiting_for_approval','constraints_valid':True,'movements':len(result['recommendations']),'inventory_changed':False})
            for a in result['recommendations']: db.add(Allocation(allocation_run_id=run_id,**a))
            run.snapshot={'inventory':inventory,'locations':locations,'model':model,'horizon':horizon,'weights':weights}
            run.results={k:v for k,v in result.items() if k!='recommendations'}
            run.total_allocated=result['total_allocated'];run.total_cost=result['total_cost'];run.objective_value=result['objective_value']
            run.stockout_risk=result['optimized_shortage']/max(1,result['baseline_shortage'])
            run.status='waiting_for_approval';run.completed_at=now()
            db.add(Notification(title=f'Allocation {run_id[:8]} ready for review: {run.total_allocated:,} units'))
            db.commit();bus.publish('optimization_status',{'id':run_id,'status':run.status})
        except Exception as e:
            db.rollback();run=db.get(Run,run_id);run.status='failed';run.error=str(e);run.completed_at=now();db.commit()
            logging.exception('Workflow failed',extra={'run_id':run_id});bus.publish('optimization_status',{'id':run_id,'status':'failed','error':str(e)})
