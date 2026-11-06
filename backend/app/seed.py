import os, random, math
from datetime import date, timedelta
from sqlalchemy import select, func, text, Integer
from .database import Session
from .models import *
from .security import hash_password

def seed(db):
    if db.scalar(select(func.count(Product.id))):
        return
    rng = random.Random(42)
    roles = ['Administrator', 'Inventory Manager', 'Warehouse Manager', 'Store Manager', 'Analyst']
    for i, name in enumerate(roles, 1):
        db.add(Role(id=i, name=name))
    db.flush()
    password = os.getenv('SEED_PASSWORD', 'RetailDemo!2026')
    for i, role in enumerate(roles, 1):
        db.add(User(email=['admin','inventory','warehouse','store','analyst'][i-1]+'@retail.local', name=role, role_id=i, password_hash=hash_password(password)))
    cities = [('Mumbai',19.07,72.87),('Delhi',28.61,77.2),('Bengaluru',12.97,77.59),('Hyderabad',17.38,78.48),('Chennai',13.08,80.27)]
    for i in range(22):
        city, lat, lon = cities[i%5]
        kind = 'warehouse' if i<5 else 'store' if i<20 else 'online' if i==20 else 'distribution_center'
        db.add(Location(id=i+1, location_name=f'{city} {kind.replace("_", " ").title()} {i+1:02}', location_type=kind, region=city, latitude=lat+i*.01, longitude=lon+i*.01, storage_capacity=100000 if kind in ('warehouse','distribution_center') else 15000 if kind=='online' else 5000, fulfillment_capacity=10000 if kind=='online' else 2000))
    categories = {'Electronics':['Wireless Headphones','Smart Speaker','USB-C Hub','Power Bank'], 'Clothing':['Cotton T-Shirt','Denim Jacket','Running Shorts','Linen Shirt'], 'Grocery':['Organic Coffee','Basmati Rice','Olive Oil','Green Tea'], 'Home Appliances':['Electric Kettle','Air Purifier','Hand Blender','Table Fan'], 'Personal Care':['Face Cleanser','Body Lotion','Shampoo','Sunscreen'], 'Accessories':['Travel Backpack','Leather Wallet','Sunglasses','Canvas Tote']}
    for p in range(1,101):
        category = list(categories)[(p-1)%6]
        name = categories[category][((p-1)//6)%4]
        cost = rng.randint(150,5000)
        db.add(Product(id=p, sku=f'RTL-{p:04}', product_name=f'{name} {chr(65+(p-1)//24)}', category=category, description=f'{name}, synthetic demonstration catalogue.', unit_cost=cost, selling_price=round(cost*1.45,2), weight=round(rng.uniform(.1,3),2)))
    db.flush()
    inventory, sales = [], []
    end = date(2026,11,5)
    for p in range(1,101):
        for loc in range(1,23):
            source = loc<=5 or loc==22
            q = rng.randint(120,350) if source else rng.randint(0,65) if loc!=21 else rng.randint(20,160)
            reserved = min(q, rng.randint(0,8))
            inventory.append(dict(product_id=p,location_id=loc,quantity_on_hand=q,quantity_reserved=reserved,safety_stock=20 if source else 8,reorder_level=40 if source else 20,version=1,last_updated=now()))
            if source:
                continue
            base = (2 + p%7) * (3 if loc==21 else .65+loc%4*.15)
            for week in range(53):
                day = end-timedelta(days=7*(52-week))
                seasonal = 1+.25*math.sin(2*math.pi*week/52)
                promo = week%13==0
                units = max(0,round(base*7*seasonal*(1.3 if promo else 1)*rng.uniform(.75,1.25)))
                sales.append(dict(product_id=p,location_id=loc,sales_channel='online' if loc==21 else 'offline',quantity_sold=units,selling_price=round((150+(p*97)%4800)*1.45,2),promotion_flag=promo,sale_date=day.isoformat()))
    db.execute(Inventory.__table__.insert(), inventory)
    for offset in range(0,len(sales),5000):
        db.execute(Sale.__table__.insert(),sales[offset:offset+5000])
    db.add_all([Supplier(id=i,name=f'{city[0]} Supply Co.',lead_time_days=2+i) for i,city in enumerate(cities,1)])
    db.flush()
    db.add_all([PurchaseOrder(supplier_id=i,product_id=i,location_id=i,quantity=200,status='pending',expected_date='2026-11-12') for i in range(1,6)])
    db.add(Notification(title='Demo network ready: 100 products across 22 locations',severity='info'))
    db.add(Notification(title='Run an allocation to identify demand-driven replenishment',severity='warning'))
    db.add(Setting(key='optimization',value={'stockout_penalty':25,'holding_cost':.2,'online_priority':1.2,'safety_stock_multiplier':1.0}))
    db.add(Setting(key='forecast',value={'model':'exponential_smoothing','horizon':7}))
    db.add(Setting(key='notifications',value={'inventory_alerts':True,'workflow_updates':True}))
    if db.bind.dialect.name=='postgresql':
        # Explicit reproducible IDs must advance PostgreSQL's generated sequences.
        db.flush()
        for table in Base.metadata.sorted_tables:
            column=table.c.get('id')
            if column is not None and isinstance(column.type,Integer) and column.primary_key:
                sequence=db.scalar(text("SELECT pg_get_serial_sequence(:table_name,'id')"),{'table_name':table.name})
                maximum=db.scalar(select(func.max(column)))
                if sequence and maximum:db.execute(text('SELECT setval(:sequence,:maximum,true)'),{'sequence':sequence,'maximum':maximum})
    db.commit()

if __name__ == '__main__':
    with Session() as db:
        seed(db)
