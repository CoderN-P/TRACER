import inspect
from collections import defaultdict

class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def subscribe(self, event_type, callback):
        self.listeners[event_type].append(callback)

    async def publish(self, event):
        for callback in self.listeners[type(event)]:
            result = callback(event)

            if inspect.isawaitable(result):
                await result