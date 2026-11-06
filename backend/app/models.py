from sqlalchemy import Integer, String, Boolean, Float, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, now

class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(200))
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'))
    active: Mapped[bool] = mapped_column(default=True)

class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(60), unique=True)
    product_name: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text, default='')
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2))
    weight: Mapped[float] = mapped_column(Float, default=1)
    dimensions: Mapped[str] = mapped_column(String(80), default='20x20x20 cm')
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)

class Location(Base):
    __tablename__ = 'locations'
    id: Mapped[int] = mapped_column(primary_key=True)
    location_name: Mapped[str] = mapped_column(String(120))
    location_type: Mapped[str] = mapped_column(String(60), index=True)
    address: Mapped[str] = mapped_column(default='Synthetic retail network')
    region: Mapped[str] = mapped_column(String(60))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    storage_capacity: Mapped[int] = mapped_column(Integer)
    fulfillment_capacity: Mapped[int] = mapped_column(Integer, default=12000)
    active: Mapped[bool] = mapped_column(default=True)

class Inventory(Base):
    __tablename__ = 'inventory'
    __table_args__ = (UniqueConstraint('product_id', 'location_id'), CheckConstraint('quantity_on_hand >= quantity_reserved AND quantity_reserved >= 0 AND safety_stock >= 0'))
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'), index=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, default=10)
    reorder_level: Mapped[int] = mapped_column(Integer, default=30)
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_updated: Mapped[str] = mapped_column(default=now)
    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved

class Sale(Base):
    __tablename__ = 'sales_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'), index=True)
    sales_channel: Mapped[str] = mapped_column(String(20))
    quantity_sold: Mapped[int] = mapped_column(Integer)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2))
    promotion_flag: Mapped[bool] = mapped_column(default=False)
    sale_date: Mapped[str] = mapped_column(String(10), index=True)

class Forecast(Base):
    __tablename__ = 'demand_forecasts'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    channel: Mapped[str] = mapped_column(String(20))
    forecast_date: Mapped[str] = mapped_column(String(10))
    horizon: Mapped[int] = mapped_column(Integer)
    predicted_demand: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float] = mapped_column(Float)
    upper_bound: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(60))
    confidence_score: Mapped[float] = mapped_column(Float)
    mae: Mapped[float] = mapped_column(Float)
    wape: Mapped[float] = mapped_column(Float)

class Run(Base):
    __tablename__ = 'optimization_runs'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), index=True)
    objective_value: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    total_allocated: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    stockout_risk: Mapped[float] = mapped_column(Float, default=0)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(default=now)
    completed_at: Mapped[str | None] = mapped_column(nullable=True)

class Allocation(Base):
    __tablename__ = 'inventory_allocations'
    id: Mapped[int] = mapped_column(primary_key=True)
    allocation_run_id: Mapped[str] = mapped_column(ForeignKey('optimization_runs.id'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    source_location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    destination_location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    sales_channel: Mapped[str] = mapped_column(String(20))
    allocated_quantity: Mapped[int] = mapped_column(Integer)
    allocation_status: Mapped[str] = mapped_column(String(40), default='proposed')
    estimated_cost: Mapped[float] = mapped_column(Numeric(14, 2))
    reason: Mapped[str] = mapped_column(Text)
    eta_hours: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(default=now)
    __table_args__ = (CheckConstraint('allocated_quantity > 0 AND source_location_id != destination_location_id'),)

class Execution(Base):
    __tablename__ = 'agent_executions'
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(80), index=True)
    execution_id: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40))
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_duration: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[str] = mapped_column(default=now)

class Message(Base):
    __tablename__ = 'agent_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(40), index=True)
    sender: Mapped[str] = mapped_column(String(80))
    recipient: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[str] = mapped_column(default=now)

class Audit(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(60))
    previous_value: Mapped[dict] = mapped_column(JSON, default=dict)
    new_value: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[str] = mapped_column(default=now)

class Transfer(Base):
    __tablename__ = 'transfers'
    id: Mapped[int] = mapped_column(primary_key=True)
    allocation_id: Mapped[int | None] = mapped_column(ForeignKey('inventory_allocations.id'), nullable=True, unique=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    source_location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    destination_location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default='scheduled')
    estimated_cost: Mapped[float] = mapped_column(Numeric(14, 2))
    eta_hours: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(default=now)

class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(20), default='info')
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(default=now)

class Simulation(Base):
    __tablename__ = 'simulation_runs'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    scenario: Mapped[str] = mapped_column(String(80))
    parameters: Mapped[dict] = mapped_column(JSON)
    results: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)

class Supplier(Base):
    __tablename__ = 'suppliers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    lead_time_days: Mapped[int] = mapped_column(Integer)

class PurchaseOrder(Base):
    __tablename__ = 'purchase_orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(default='pending')
    expected_date: Mapped[str] = mapped_column(String(10))

class Promotion(Base):
    __tablename__ = 'promotions'
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    uplift: Mapped[float] = mapped_column(Float)
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))

class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
