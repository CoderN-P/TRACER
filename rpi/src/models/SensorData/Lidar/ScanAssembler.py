from .LidarScan import LidarScan, LidarPoint
import time

class ScanAssembler:
    def __init__(self):
        self.current_scan: LidarScan | None = None
        
    def add(self, point: LidarPoint) -> LidarScan | None:
        if not self.current_scan:
            self.current_scan = LidarScan(
                start_time_ns=point.timestamp_ns,
                end_time_ns=point.timestamp_ns,
                points=[point]
            )
        
        else:
            if point.angle < self.current_scan.points[-1].angle and len(self.current_scan.points) > 400:
                # Scan is complete
                completed_scan = self.current_scan
                self.current_scan = None
                return completed_scan
            else:
                self.current_scan.points.append(point)
                self.current_scan.end_time_ns = point.timestamp_ns
                return None