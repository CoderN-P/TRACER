from .QuinticHermiteSpline import QuinticHermiteSpline
from typing import List
import multiprocessing as mp
from multiprocessing.resource_tracker import unregister
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
        
        if not self.check_c2_continuity():
            raise ValueError("Splines must be C2 continuous")
        
        process = mp.Process(
            target=self._build_trajectory_worker,
            args=(),
            daemon=True
        )
        
        process.start()
    
    @classmethod
    def from_raw(cls, splines):
        spline_objects = [
            QuinticHermiteSpline(
                start=s['start'],
                end=s['end'],
                start_velocity=s['start_velocity'],
                end_velocity=s['end_velocity'],
                start_acceleration=s['start_acceleration'],
                end_acceleration=s['end_acceleration']
            ) for s in splines
        ]
        
        return cls(spline_objects)
    
    def check_c2_continuity(self):
        for i in range(len(self.splines) - 1):
            end_spline = self.splines[i]
            start_spline = self.splines[i + 1]
            
            if not np.isclose(end_spline.end, start_spline.start).all():
                return False
            
            if not np.isclose(end_spline.end_velocity, start_spline.start_velocity).all():
                return False
            
            if not np.isclose(end_spline.end_acceleration, start_spline.start_acceleration).all():
                return False
            
        return True
    
    def _build_trajectory_worker(self):
        trajectory = []
        for i, spline in enumerate(self.splines):
            start_velocity = 0.0 if i == 0 else trajectory[-1].v
            end_velocity = 0.0 if i == len(self.splines) - 1 else None
            
            spline_trajectory = spline.build_trajectory(start_velocity, end_velocity, trajectory[-1].t if trajectory else 0.0)
            
            if i > 0:
                spline_trajectory.pop(0) # Remove the first point to avoid duplicates
                
            trajectory.extend(spline_trajectory)
            
        # Serialize into numpy array
        
        arr = np.array([[p.x, p.y, p.theta, p.v, p.omega, p.t] for p in trajectory])
        shm = shared_memory.SharedMemory(create=True, size=arr.nbytes)
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
            unregister(self._shm._name, 'shared_memory')
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
            
    
            
        
            
        
        
    
    
    
    
    
        
    
