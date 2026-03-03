from .QuinticHermiteSpline import QuinticHermiteSpline
from typing import List
import multiprocessing as mp
import numpy as np
from multiprocessing import shared_memory

from .RAMSETE import RAMSETE
from .TrajectoryState import TrajectoryState


class Path:
    def __init__(self, splines: List[QuinticHermiteSpline], scale=1.0):
        self.splines = splines
        self.scale = scale #(meters per unit) 
        self.trajectory = None
        self._shm = None
        self._ready = mp.Event()
        self._meta_queue = mp.Queue()
        self.ramsete = None
        
        process = mp.Process(
            target=self._build_trajectory_worker,
            args=(splines, self._meta_queue, self._ready),
            daemon=True
        )
        
        process.start()
        
    def check_c2_continuity(self):
        for i in range(len(self.splines) - 1):
            end_spline = self.splines[i]
            start_next_spline = self.splines[i + 1]
            
            # Check position continuity
            
        
        print("Path is C2 continuous")
        return True
    
    def _build_trajectory_worker(self):
        shm = shared_memory.SharedMemory(create=True)
        
        trajectory = []
        for i, spline in enumerate(self.splines):
            start_velocity = 0.0 if i == 0 else self.trajectory[-1].v
            end_velocity = 0.0 if i == len(self.splines) - 1 else None
            
            spline_trajectory = spline.build_trajectory(start_velocity, end_velocity, self.trajectory[-1].t if self.trajectory else 0.0)
            
            if i > 0:
                spline_trajectory.pop(0) # Remove the first point to avoid duplicates
                
            trajectory.extend(spline_trajectory)
            
        # Serialize into numpy array
        
        arr = np.array([[p.x, p.y, p.theta, p.v, p.omega, p.t] for p in trajectory])
        shared_arr = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
        shared_arr[:] = arr
        self._meta_queue.put((shm.name, len(trajectory)))
        self._ready.set()
        
    def is_ready(self):
        if self.trajectory is not None:
            return True
        
        if self._ready.is_set():
            name, n_points = self._meta_queue.get()
            
            self._shm = shared_memory.SharedMemory(name=name)
            
            arr = np.ndarray((n_points, 6), dtype=np.float64, buffer=self._shm.buf)
            self.trajectory = [
                TrajectoryState(x=p[0], y=p[1], theta=p[2], v=p[3], omega=p[4], t=p[5]) 
                for p in arr
            ]
            self.ramsete = RAMSETE(self.trajectory)
            self._shm.close()
            self._shm.unlink()
            return True
        
        return False
    
    def complete(self):
        if self.trajectory is None:
            return False
        
        return self.ramsete.running_time >= self.trajectory[-1].t
    
    def get_command(self, current_state, dt):
        if self.trajectory is None: 
            return None
        return self.ramsete.calculate_control_command(current_state, dt)
            
    
            
        
            
        
        
    
    
    
    
    
        
    