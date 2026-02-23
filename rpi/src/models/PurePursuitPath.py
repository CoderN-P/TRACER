class PurePursuitPath:
    def __init__(self, waypoints):
        self.waypoints = waypoints # List of (x, y) tuples representing the path waypoints
        self.current_index = 0

    def get_current_waypoint(self):
        if self.current_index < len(self.waypoints):
            return self.waypoints[self.current_index]
        else:
            return None

    def advance_to_next_waypoint(self):
        if self.current_index < len(self.waypoints) - 1:
            self.current_index += 1