import math
from collections import defaultdict
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint

def route(source, destination):
    km = math.hypot(source['latitude']-destination['latitude'],source['longitude']-destination['longitude'])*111
    return round(.4+km*.002,2), max(4,math.ceil(km/45)+4)

def optimize(inventory, locations, forecasts, weights, method='milp'):
    """Integer transportation with shortage costs and shared residual location capacity."""
    locs={r['id']:r for r in locations}
    inv={(r['product_id'],r['location_id']):dict(r) for r in inventory}
    used=defaultdict(int)
    for r in inventory: used[r['location_id']]+=r['quantity_on_hand']
    room={i:max(0,l['storage_capacity']-used[i]) for i,l in locs.items()}
    fulfillment={i:l['fulfillment_capacity'] for i,l in locs.items()}
    by_product=defaultdict(list)
    for f in forecasts: by_product[f['product_id']].append(f)
    recommendations=[]; baseline=0; shortages=0; solver_status=[]
    for product,fs in sorted(by_product.items()):
        sources=[r for r in inventory if r['product_id']==product and locs[r['location_id']]['location_type'] in ('warehouse','distribution_center') and locs[r['location_id']]['active']]
        supply={s['location_id']:max(0,s['quantity_on_hand']-s['quantity_reserved']-s['safety_stock']) for s in sources}
        need={}; priority={}
        for f in fs:
            r=inv[(product,f['location_id'])]
            target=math.ceil(f['predicted_demand']+r['safety_stock']*weights.get('safety_stock_multiplier',1))
            n=max(0,target-r['quantity_on_hand']+r['quantity_reserved'])
            need[f['location_id']]=min(n,room[f['location_id']],fulfillment[f['location_id']])
            priority[f['location_id']]=weights.get('online_priority',1.2) if f['channel']=='online' else 1
            baseline+=n
        edges=[(s,d) for s in sorted(supply) for d in sorted(need) if supply[s]>0 and need[d]>0]
        if not edges: continue
        costs=np.array([route(locs[s],locs[d])[0]+.15+weights.get('holding_cost',.2)-weights.get('stockout_penalty',25)*priority[d] for s,d in edges])
        upper=np.array([min(supply[s],need[d]) for s,d in edges])
        quantities=None
        if method=='milp':
            keys=[('source',s) for s in supply]+[('destination',d) for d in need]
            matrix=np.array([[int((s==k) if t=='source' else (d==k)) for s,d in edges] for t,k in keys],dtype=float)
            limits=np.array([supply[k] if t=='source' else need[k] for t,k in keys])
            result=milp(costs,integrality=np.ones(len(edges)),bounds=Bounds(np.zeros(len(edges)),upper),constraints=LinearConstraint(matrix,np.zeros(len(keys)),limits),options={'time_limit':10})
            if result.success:
                quantities=np.rint(result.x).astype(int); solver_status.append('scipy_milp')
        if quantities is None:
            quantities=np.zeros(len(edges),dtype=int); remaining_s=dict(supply);remaining_d=dict(need)
            for k in sorted(range(len(edges)),key=lambda k:(costs[k],edges[k])):
                s,d=edges[k]
                if costs[k]>=0: continue
                quantities[k]=min(remaining_s[s],remaining_d[d]);remaining_s[s]-=quantities[k];remaining_d[d]-=quantities[k]
            solver_status.append('greedy_fallback')
        for (s,d),q in zip(edges,quantities):
            if q<=0: continue
            cost,eta=route(locs[s],locs[d]);q=int(q)
            recommendations.append(dict(product_id=product,source_location_id=s,destination_location_id=d,sales_channel='online' if locs[d]['location_type']=='online' else 'offline',allocated_quantity=q,estimated_cost=round(q*(cost+.15),2),eta_hours=eta,reason=f'Replenish {q} units against forecast and safety stock; source reservations protected.'))
            room[d]-=q; fulfillment[d]-=q
    total=sum(r['allocated_quantity'] for r in recommendations)
    cost=round(sum(r['estimated_cost'] for r in recommendations),2)
    shortages=max(0,baseline-total)
    holding=round(total*weights.get('holding_cost',.2),2)
    return {'recommendations':recommendations,'total_allocated':total,'total_cost':cost,'holding_cost':holding,'baseline_shortage':baseline,'optimized_shortage':shortages,'stockout_reduction':round(100*total/baseline,2) if baseline else 0,'estimated_savings':round(total*weights.get('stockout_penalty',25)-cost-holding,2),'objective_value':round(shortages*weights.get('stockout_penalty',25)+cost+holding,2),'solver':sorted(set(solver_status)) or ['no_movement_required']}

def validate(inventory,locations,recommendations):
    rows={(r['product_id'],r['location_id']):dict(r) for r in inventory}
    locs={r['id']:r for r in locations};received=defaultdict(int)
    for a in recommendations:
        q=a['allocated_quantity'];s=a['source_location_id'];d=a['destination_location_id'];p=a['product_id']
        if not isinstance(q,int) or q<=0 or s==d or (p,s) not in rows or (p,d) not in rows: raise ValueError('Invalid inventory movement')
        if not locs[s]['active'] or not locs[d]['active']: raise ValueError('Inactive location')
        source=rows[(p,s)];dest=rows[(p,d)]
        if source['quantity_on_hand']-q < source['quantity_reserved']+source['safety_stock']: raise ValueError('Insufficient source stock after reservations and safety stock')
        source['quantity_on_hand']-=q;dest['quantity_on_hand']+=q;received[d]+=q
    for l,loc in locs.items():
        if sum(r['quantity_on_hand'] for r in rows.values() if r['location_id']==l)>loc['storage_capacity']: raise ValueError('Destination storage capacity exceeded')
        if received[l]>loc['fulfillment_capacity']: raise ValueError('Destination fulfillment capacity exceeded')
    return rows
