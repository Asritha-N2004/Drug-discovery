import math
from collections import defaultdict
from datetime import date, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy import select
from .models import Sale, Inventory, Location, Forecast, Product

MODELS = ('moving_average','exponential_smoothing','linear_regression','random_forest')

def predict(values, model, steps=1):
    y = np.asarray(values, dtype=float)
    if len(y)<4:
        return np.full(steps, max(1,float(y.mean()) if len(y) else 3))
    if model == 'moving_average':
        return np.full(steps, float(y[-4:].mean()))
    if model == 'exponential_smoothing':
        level = y[0]
        for v in y[1:]:
            level = .35*v+.65*level
        return np.full(steps,level)
    x = np.arange(len(y)).reshape(-1,1)
    reg = LinearRegression() if model=='linear_regression' else RandomForestRegressor(n_estimators=16,max_depth=4,random_state=42,n_jobs=1)
    reg.fit(x,y)
    return np.maximum(0,reg.predict(np.arange(len(y),len(y)+steps).reshape(-1,1)))

def forecast_all(db, run_id, model='exponential_smoothing', horizon=7, product_id=None, location_id=None, multiplier=1.0):
    query=select(Sale).order_by(Sale.sale_date)
    if product_id: query=query.where(Sale.product_id==product_id)
    if location_id: query=query.where(Sale.location_id==location_id)
    history=defaultdict(list)
    for s in db.scalars(query):
        history[(s.product_id,s.location_id)].append((s.sale_date,s.quantity_sold/7))
    locations={l.id:l for l in db.scalars(select(Location).where(Location.active==True))}
    active_products=set(db.scalars(select(Product.id).where(Product.active==True)))
    rows=[]
    query=select(Inventory)
    if product_id: query=query.where(Inventory.product_id==product_id)
    if location_id: query=query.where(Inventory.location_id==location_id)
    for inv in db.scalars(query):
        if inv.product_id not in active_products:continue
        loc=locations.get(inv.location_id)
        if not loc or loc.location_type not in ('store','online'): continue
        series=history[(inv.product_id,inv.location_id)]
        vals=[v for _,v in series]
        used=model if len(vals)>=4 else 'fallback'
        p=float(predict(vals,model)[0])*horizon*multiplier
        # Rolling holdout predictions only use preceding observations.
        errors=[abs(vals[i]-float(predict(vals[:i],model)[0])) for i in range(max(4,len(vals)-4),len(vals))]
        mae=float(np.mean(errors)) if errors else 0
        denom=float(np.mean(vals[-4:])) if vals else 0
        wape=mae/denom if denom else 0
        uncertainty=1.96*max(mae,float(np.std(vals[-12:])) if vals else 3)*math.sqrt(horizon)*multiplier
        rows.append(dict(run_id=run_id, product_id=inv.product_id,location_id=inv.location_id,channel='online' if loc.location_type=='online' else 'offline',forecast_date=((date.fromisoformat(series[-1][0]) if series else date.today())+timedelta(days=1)).isoformat(),horizon=horizon,predicted_demand=round(p,2),lower_bound=round(max(0,p-uncertainty),2),upper_bound=round(p+uncertainty,2),model_name=used,confidence_score=round(max(.1,1-min(.9,wape)),3) if vals else .1,mae=round(mae,3),wape=round(wape,4)))
    if rows: db.execute(Forecast.__table__.insert(),rows)
    return rows
