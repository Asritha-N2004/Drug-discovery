import asyncio
from collections import deque
from .database import now

class EventBus:
    def __init__(self):
        self.events=deque(maxlen=1000)
        self.sequence=0
    def publish(self,kind,payload):
        self.sequence+=1
        self.events.append({'sequence':self.sequence,'type':kind,'payload':payload,'timestamp':now()})
    def since(self,seq):
        return [e for e in list(self.events) if e['sequence']>seq]

bus=EventBus()
