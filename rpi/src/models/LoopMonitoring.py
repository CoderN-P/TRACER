class LoopMonitoring:
    def __init__(self):
        self.max_loop_time = 0.0
        
    def update_loop_time(self, start):
        duration_ms = 1000*(asyncio.get_event_loop().time() - start)
      
        if duration_ms > self.max_loop_time:
            self.max_loop_time = duration_ms
            
        