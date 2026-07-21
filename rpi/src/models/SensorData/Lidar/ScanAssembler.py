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
                
                # Reset cur scan
                self.current_scan = LidarScan(
                    start_time_ns=point.timestamp_ns,
                    end_time_ns=point.timestamp_ns,
                    points=[point]
                )

                # Interpolate lidar point timestamps
                SCAN_PERIOD_NS = 100_000_000

                dt = SCAN_PERIOD_NS / len(completed_scan.points)
                
                for i, point in enumerate(completed_scan.points):
                    point.timestamp_ns = (
                        completed_scan.start_time_ns + int(i * dt)
                    )
                    
                completed_scan.end_time_ns =  completed_scan.points[-1].timestamp_ns
                
                return completed_scan
            else:
                self.current_scan.points.append(point)
                self.current_scan.end_time_ns = point.timestamp_ns
                return None