from collections import defaultdict
from sqlalchemy import select, func
from .models import *

def inventory_rows(db):
    rows=[]
    for inv,p,l in db.execute(select(Inventory,Product,Location).join(Product,Product.id==Inventory.product_id).join(Location,Location.id==Inventory.location_id)):
        available=inv.quantity_available
        rows.append({'id':inv.id,'product_id':p.id,'location_id':l.id,'sku':p.sku,'product_name':p.product_name,'category':p.category,'location_name':l.location_name,'location_type':l.location_type,'region':l.region,'quantity_on_hand':inv.quantity_on_hand,'quantity_reserved':inv.quantity_reserved,'quantity_available':available,'safety_stock':inv.safety_stock,'reorder_level':inv.reorder_level,'version':inv.version,'status':'stockout' if available==0 else 'low' if available<inv.reorder_level else 'overstock' if available>inv.reorder_level*5 else 'healthy','value':float(p.unit_cost)*inv.quantity_on_hand,'last_updated':inv.last_updated})
    return rows

def summary(db):
    rows=inventory_rows(db);locations=list(db.scalars(select(Location)))
    recent=db.scalar(select(Forecast.run_id).order_by(Forecast.id.desc()).limit(1))
    wape=db.scalar(select(func.avg(Forecast.wape)).where(Forecast.run_id==recent)) if recent else None
    approved=list(db.scalars(select(Run).where(Run.status=='approved')))
    total=sum(r['quantity_on_hand'] for r in rows)
    sales=db.scalar(select(func.sum(Sale.quantity_sold))) or 0
    return {'total_products':db.scalar(select(func.count(Product.id)).where(Product.active==True)),'total_inventory':total,'total_warehouses':sum(l.location_type in ('warehouse','distribution_center') for l in locations),'total_stores':sum(l.location_type=='store' for l in locations),'online_inventory':sum(r['quantity_on_hand'] for r in rows if r['location_type']=='online'),'offline_inventory':sum(r['quantity_on_hand'] for r in rows if r['location_type']=='store'),'low_stock':sum(r['status'] in ('low','stockout') for r in rows),'overstock':sum(r['status']=='overstock' for r in rows),'stockout_risk':round(100*sum(r['status'] in ('low','stockout') for r in rows)/max(1,len(rows)),2),'inventory_turnover':round(sales/max(1,total),2),'forecast_accuracy':round(max(0,1-wape)*100,2) if wape is not None else None,'estimated_savings':round(sum(r.results.get('estimated_savings',0) for r in approved),2),'inventory_value':round(sum(r['value'] for r in rows),2),'data_label':'Reproducible synthetic demonstration data','turnover_basis':'53-week sales / current on-hand (proxy)','savings_basis':'Modeled shortage-cost avoidance for currently approved runs'}

def sales_performance(db):
    buckets=defaultdict(lambda:{'online':0,'offline':0,'revenue':0})
    month_expression=func.substr(Sale.sale_date,1,7).label('sales_month')
    for month,channel,qty,revenue in db.execute(select(month_expression,Sale.sales_channel,func.sum(Sale.quantity_sold),func.sum(Sale.quantity_sold*Sale.selling_price)).group_by(month_expression,Sale.sales_channel)):
        buckets[month][channel]=qty;buckets[month]['revenue']+=float(revenue)
    return [{'month':k,**v} for k,v in sorted(buckets.items())]

def inventory_health(db):
    rows=inventory_rows(db);statuses=defaultdict(int);groups=defaultdict(int)
    for r in rows: statuses[r['status']]+=1;groups[r['location_name']]+=r['quantity_on_hand']
    return {'statuses':[{'name':k,'value':v} for k,v in statuses.items()],'locations':[{'name':k,'value':v} for k,v in groups.items()]}
