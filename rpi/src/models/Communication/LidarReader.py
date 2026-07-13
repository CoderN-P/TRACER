from rplidarc1.scanner import RPLidar
import threading
import logging
import time
import asyncio
from ..SensorData.Lidar import ScanAssembler, LidarPoint

class LidarReader:
    def __init__(self, port='/dev/ttyUSB0', baudrate=460800):
        self.reader = RPLidar(port,baudrate)
        self.running = False
        self._logger = logging.getLogger("LidarReader")
        self.scan_assembler = ScanAssembler()
        
    async def scan_loop(self, callback):
        try:
            print(self.reader.healthcheck())
            scan_coroutine = self.reader.simple_scan(make_return_dict=True)
            
            async with asyncio.TaskGroup() as tg:
                tg.create_task(scan_coroutine)
                tg.create_task(self.process_loop(callback))
                
        finally:
            self.reader.stop_event.set()
            self.reader.reset()
            self.reader.shutdown()
                
    async def process_loop(self, callback):
        while True:
            point_raw = await self.reader.output_queue.get()
            
            if point_raw["d_mm"] is None:
                continue

            point = LidarPoint(
                angle=point_raw["a_deg"],
                distance=point_raw["d_mm"] / 1000.0,
                quality=point_raw["q"],
                timestamp_ns=time.perf_counter_ns()
            )
            
            scan = self.scan_assembler.add(point)
            
            if scan is not None:
                callback(scan)
        
            
                    
    
                
            