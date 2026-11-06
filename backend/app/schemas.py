from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Login(Strict):
    email: str=Field(max_length=200)
    password: str=Field(min_length=1,max_length=72)

class ProductInput(Strict):
    sku: str=Field(min_length=1,max_length=60)
    product_name: str=Field(min_length=1,max_length=160)
    category: str=Field(min_length=1,max_length=80)
    description: str=''
    unit_cost: Decimal=Field(ge=0,max_digits=12,decimal_places=2)
    selling_price: Decimal=Field(ge=0,max_digits=12,decimal_places=2)
    weight: float=Field(default=1,gt=0)
    dimensions: str='20x20x20 cm'
    active: bool=True

class InventoryInput(Strict):
    quantity_on_hand: int=Field(ge=0)
    quantity_reserved: int=Field(ge=0)
    safety_stock: int=Field(ge=0)
    reorder_level: int=Field(ge=0)
    version: int=Field(ge=1)

class ForecastInput(Strict):
    model: Literal['moving_average','exponential_smoothing','linear_regression','random_forest']='exponential_smoothing'
    horizon: int=Field(default=7,ge=1,le=90)
    product_id: int | None=None
    location_id: int | None=None

class RunInput(ForecastInput):
    run_name: str=Field(default='Network allocation',max_length=120)
    method: Literal['milp','greedy']='milp'
    agent_id: Literal['supervisor','demand','inventory','online','offline','warehouse','pricing','risk','allocation','logistics'] | None=None

class SimulationInput(Strict):
    scenario: Literal['online_surge','store_surge','warehouse_shortage','supplier_delay','seasonal_surge','regional_imbalance','promotion_spike']
    multiplier: float=Field(default=2,ge=1,le=5)

class TransferInput(Strict):
    product_id: int
    source_location_id: int
    destination_location_id: int
    quantity: int=Field(gt=0)

class TransferStatus(Strict):
    status: Literal['in_transit','delivered']

class OptimizationSettings(Strict):
    stockout_penalty: float=Field(ge=1,le=1000)
    holding_cost: float=Field(ge=0,le=100)
    online_priority: float=Field(ge=.1,le=5)
    safety_stock_multiplier: float=Field(ge=1,le=5)

class RoleUpdate(Strict):
    role_id: int=Field(ge=1,le=5)

class ProfileUpdate(Strict):
    name: str=Field(min_length=1,max_length=100)

class NotificationSettings(Strict):
    inventory_alerts: bool=True
    workflow_updates: bool=True
