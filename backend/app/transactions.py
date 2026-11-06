from fastapi import HTTPException
from sqlalchemy import select, text
from .database import now
from .models import Run, Inventory, Location, Allocation, Transfer, Audit
from .agents import serialize
from .optimization import validate
from .events import bus

def lock(db):
    db.rollback()
    if db.bind.dialect.name=='sqlite': db.execute(text('BEGIN IMMEDIATE'))

def apply_run(db,run_id,user_id,rollback=False):
    lock(db)
    try:
        run=db.scalar(select(Run).where(Run.id==run_id).with_for_update())
        if not run: raise HTTPException(404,'Run not found')
        expected='approved' if rollback else 'waiting_for_approval'
        if run.status!=expected: raise HTTPException(409,f'Run must be {expected}; currently {run.status}')
        rows=list(db.scalars(select(Inventory).order_by(Inventory.id).with_for_update()))
        locations=list(db.scalars(select(Location).order_by(Location.id).with_for_update()))
        lookup={(r.product_id,r.location_id):r for r in rows}
        allocations=list(db.scalars(select(Allocation).where(Allocation.allocation_run_id==run_id)))
        touched={(a.product_id,l) for a in allocations for l in (a.source_location_id,a.destination_location_id)}
        versions=run.results.get('committed_versions',{}) if rollback else {str(r['id']):r['version'] for r in run.snapshot['inventory']}
        for key in touched:
            r=lookup[key]
            if versions.get(str(r.id))!=r.version: raise HTTPException(409,'Inventory changed since proposal or approval. Create a new run; rollback requires unchanged affected stock.')
        before={str(lookup[k].id):serialize(lookup[k]) for k in touched}
        if rollback:
            for a in allocations:
                src=lookup[(a.product_id,a.source_location_id)];dst=lookup[(a.product_id,a.destination_location_id)]
                if dst.quantity_on_hand-a.allocated_quantity<dst.quantity_reserved: raise HTTPException(409,'Rollback would consume reserved stock')
                src.quantity_on_hand+=a.allocated_quantity;dst.quantity_on_hand-=a.allocated_quantity
            for l in locations:
                if sum(r.quantity_on_hand for r in rows if r.location_id==l.id)>l.storage_capacity: raise HTTPException(409,'Rollback exceeds source capacity')
            for t in db.scalars(select(Transfer).where(Transfer.allocation_id.in_([a.id for a in allocations]))): t.status='reversed'
            run.status='rolled_back'
        else:
            projected=validate([serialize(r) for r in rows],[serialize(l) for l in locations],[serialize(a) for a in allocations])
            for key in touched: lookup[key].quantity_on_hand=projected[key]['quantity_on_hand']
            for a in allocations:
                db.add(Transfer(allocation_id=a.id,product_id=a.product_id,source_location_id=a.source_location_id,destination_location_id=a.destination_location_id,quantity=a.allocated_quantity,estimated_cost=a.estimated_cost,eta_hours=a.eta_hours,status='scheduled'))
            run.status='approved'
        for key in touched:
            r=lookup[key];r.version+=1;r.last_updated=now()
        for a in allocations: a.allocation_status=run.status
        run.results={**run.results,'committed_versions':{str(lookup[k].id):lookup[k].version for k in touched}}
        db.add(Audit(user_id=user_id,action='rollback' if rollback else 'approve',entity_type='optimization_run',entity_id=run_id,previous_value=before,new_value={str(lookup[k].id):serialize(lookup[k]) for k in touched}))
        db.commit();bus.publish('inventory_changed',{'run_id':run_id,'status':run.status});return serialize(run)
    except ValueError as e:
        db.rollback();raise HTTPException(409,str(e))
    except Exception:
        db.rollback();raise
