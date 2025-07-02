#!/usr/bin/env python3
"""
Magnetometer Calibration Tool

This script reads magnetometer data from a serial port in the format "x, y, z\n" (values in μT),
plots the data in real-time, and calculates hard iron and soft iron calibration offsets
when no new data is received for over a second.

Usage:
    python mag_calibration.py [--port /dev/tty.usbserial-XX] [--baud 115200]
"""

import argparse
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import serial
import serial.tools.list_ports
import sys
import threading
from scipy import linalg

def find_serial_port():
    """Find the first available serial port."""
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        print(f"Found port: {p.device}")
        if "usbserial" in p.device or "ttyACM" in p.device or "ttyUSB" in p.device:
            return p.device
    return None



class MagnetometerCalibrator:
    def __init__(self, port=None, baud_rate=115200):
        self.port = port or find_serial_port()
        self.baud_rate = baud_rate
        self.serial_conn = None
        
        # Data storage
        self.mag_data = []
        self.x_data = []
        self.y_data = []
        self.z_data = []
        
        # Plotting
        self.fig = None
        self.ax = None
        self.scatter = None
        self.ellipsoid = None
        
        # Calibration results
        self.hard_iron_offset = None
        self.soft_iron_matrix = None
        
        # State tracking
        self.running = True
        self.last_data_time = 0
        self.data_timeout = 1.0  # 1 second timeout

    def connect_serial(self):
        """Connect to the serial port."""
        try:
            print(f"Connecting to {self.port} at {self.baud_rate} baud...")
            self.serial_conn = serial.Serial(self.port, self.baud_rate, timeout=0.1)
            print("Connection established.")
            return True
        except Exception as e:
            print(f"Error connecting to serial port: {e}")
            return False

    def setup_plot(self):
        """Initialize the 3D plot."""
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlabel('X (μT)')
        self.ax.set_ylabel('Y (μT)')
        self.ax.set_zlabel('Z (μT)')
        self.ax.set_title('Magnetometer Calibration')
        
        # Empty scatter plot that will be updated
        self.scatter = self.ax.scatter([], [], [], c='b', marker='o', label='Measurements')
        
        # Add visualization of the 3 planes as circles
        # These will serve as visual guides for the calibration
        self.guide_circles = []
        self._add_guide_circles()
        
        # Add a legend
        self.ax.legend()
        
        # Equal aspect ratio
        self.ax.set_box_aspect([1, 1, 1])
        
        plt.ion()  # Interactive mode on
        plt.show(block=False)
        
    def _add_guide_circles(self):
        """Add guide circles for each plane to help with calibration."""
        # Default radius for guide circles (can adjust based on your sensor's typical range)
        radius = 30  # This will be updated during plot updates based on actual data
        
        # Create circles with 100 points
        theta = np.linspace(0, 2*np.pi, 100)
        
        # XY-plane circle (blue)
        x_xy = radius * np.cos(theta)
        y_xy = radius * np.sin(theta)
        z_xy = np.zeros_like(theta)
        xy_circle = self.ax.plot(x_xy, y_xy, z_xy, 'b-', alpha=0.5, linewidth=2, label='XY plane')[0]
        self.guide_circles.append(xy_circle)
        
        # XZ-plane circle (red)
        x_xz = radius * np.cos(theta)
        y_xz = np.zeros_like(theta)
        z_xz = radius * np.sin(theta)
        xz_circle = self.ax.plot(x_xz, y_xz, z_xz, 'r-', alpha=0.5, linewidth=2, label='XZ plane')[0]
        self.guide_circles.append(xz_circle)
        
        # YZ-plane circle (green)
        x_yz = np.zeros_like(theta)
        y_yz = radius * np.cos(theta)
        z_yz = radius * np.sin(theta)
        yz_circle = self.ax.plot(x_yz, y_yz, z_yz, 'g-', alpha=0.5, linewidth=2, label='YZ plane')[0]
        self.guide_circles.append(yz_circle)
        
        # Add annotations for each circle
        self.ax.text(radius, 0, 0, "XY Plane", color='blue')
        self.ax.text(radius, 0, radius, "XZ Plane", color='red')
        self.ax.text(0, radius, radius, "YZ Plane", color='green')

    def update_plot(self):
        """Update the plot with new data."""
        if not self.x_data:
            return
            
        # Update scatter plot
        self.scatter._offsets3d = (self.x_data, self.y_data, self.z_data)
        
        # Adjust axes limits if needed
        max_range = max(
            max(self.x_data) - min(self.x_data),
            max(self.y_data) - min(self.y_data),
            max(self.z_data) - min(self.z_data)
        )
        
        mid_x = (max(self.x_data) + min(self.x_data)) / 2
        mid_y = (max(self.y_data) + min(self.y_data)) / 2
        mid_z = (max(self.z_data) + min(self.z_data)) / 2
        
        # Set axes limits
        self.ax.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
        self.ax.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
        self.ax.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
        
        # Update guide circles based on current data range
        self._update_guide_circles(mid_x, mid_y, mid_z, max_range/2)
        
        # Draw updated plot
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def read_serial_data(self):
        """Read and parse data from the serial port."""
        while self.running:
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('utf-8').strip()
                        self.process_line(line)
                    else:
                        # Check if we've had a data timeout
                        if time.time() - self.last_data_time > self.data_timeout and self.last_data_time > 0:
                            if len(self.mag_data) > 10:  # Ensure we have enough data
                                print("Data timeout - calculating calibration...")
                                self.calculate_calibration()
                                self.last_data_time = time.time()  # Reset to avoid repeated calculations
                                self.serial_conn.close()
                except Exception as e:
                    print(f"Error reading serial data: {e}")
            time.sleep(0.01)

    def process_line(self, line):
        """Process a line of data from the serial port."""
        try:
            # Parse "x, y, z" format
            parts = line.split(',')
            if len(parts) >= 3:
                # Parse the q8_7 int16 format values
                x_raw = int(parts[0].strip())
                y_raw = int(parts[1].strip())
                z_raw = int(parts[2].strip())
                
                # Convert to μT using the helper function
                x = q8_7_to_float(x_raw)
                y = q8_7_to_float(y_raw)
                z = q8_7_to_float(z_raw)
                
                self.last_data_time = time.time()
                
                if any([v > 100 or v < -100 for v in (x, y, z)]):
                    raise ValueError(f"Values out of expected range (-100 to 100 μT): {x}, {y}, {z} (raw: {x_raw}, {y_raw}, {z_raw})")
                
                # Store data
                self.mag_data.append([x, y, z])
                self.x_data.append(x)
                self.y_data.append(y)
                self.z_data.append(z)
                
                # Update time of last data received
                
                
                # Print received data with guidance
                sample_count = len(self.mag_data)
                if sample_count % 10 == 0:  # Only print every 10th sample to reduce console spam
                    print(f"Received: X={x:.2f} μT, Y={y:.2f} μT, Z={z:.2f} μT (raw: {x_raw}, {y_raw}, {z_raw}) - Total samples: {sample_count}")
                    
                    # Progress indicators
                    if sample_count < 50:
                        print("Keep collecting data - move in all directions!")
                    elif sample_count == 50:
                        print("\nGood progress! Now focus on filling the guide circles.")
                    elif sample_count == 100:
                        print("\nExcellent! Continue rotating to cover all orientations.")
                    elif sample_count == 200:
                        print("\nGreat dataset! When finished, hold still for 1 second to calculate calibration.")
                
        except ValueError as e:
            print(f"Skipping invalid data: {line} - {e}")

    def calculate_calibration(self):
        """Calculate hard iron and soft iron calibration parameters."""
        if len(self.mag_data) < 10:
            print("Not enough data for calibration")
            return False
            
        try:
            # Convert data to numpy array
            data = np.array(self.mag_data)
            
            # Hard iron offset is the average of min and max for each axis
            x_min, x_max = np.min(data[:, 0]), np.max(data[:, 0])
            y_min, y_max = np.min(data[:, 1]), np.max(data[:, 1])
            z_min, z_max = np.min(data[:, 2]), np.max(data[:, 2])
            
            # Hard iron offsets (center of the ellipsoid)
            self.hard_iron_offset = np.array([
                (x_min + x_max) / 2,
                (y_min + y_max) / 2,
                (z_min + z_max) / 2
            ])
            
            # Calculate the soft iron transformation matrix
            # We'll use PCA (Principal Component Analysis) to get the ellipsoid axes
            offset = np.mean(data, axis=0)
            centered_data = data - offset

            # PCA / eigen decomposition
            H = np.dot(centered_data.T, centered_data) / len(centered_data)
            eigenvalues, eigenvectors = np.linalg.eigh(H)  # Use eigh for symmetric matrix

            # Sort by descending eigenvalue magnitude
            idx = np.argsort(eigenvalues)[::-1]
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]

            # Compute soft iron correction matrix (whitening transform)
            scale = np.sqrt(eigenvalues)
            W = eigenvectors @ np.diag(1 / scale) @ eigenvectors.T

            corrected = (W @ (data - offset).T).T
            mean_radius = np.mean(np.linalg.norm(corrected, axis=1))  # ~1.7 µT in your case
            
            # Compute scale to bring mean radius to Earth's field (~50 µT)
            target_field = 50.0
            scaling_factor = target_field / mean_radius
            
            # Scale W
            W_scaled = W * scaling_factor

            self.hard_iron_offset = offset
            self.soft_iron_matrix = W_scaled
            
            print("\n----- Calibration Results -----")
            print(f"Hard Iron Offset (μT): [{self.hard_iron_offset[0]:.2f}, {self.hard_iron_offset[1]:.2f}, {self.hard_iron_offset[2]:.2f}]")
            print("Soft Iron Matrix:")
            for row in self.soft_iron_matrix:
                print(f"  [{row[0]:.4f}, {row[1]:.4f}, {row[2]:.4f}]")
            
            # Save calibration to file
            self.plot_calibration()
            self.save_calibration()
            
            return True
        except Exception as e:
            print(f"Error calculating calibration: {e}")
            return False
    
    def save_calibration(self):
        """Save calibration results to files."""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        # Save calibration parameters to text file
        try:
            with open('mag_calibration_results.txt', 'w') as f:
                f.write("# Magnetometer Calibration Results\n")
                f.write(f"# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("# Hard Iron Offset (μT)\n")
                f.write(f"hard_iron_offset = [{self.hard_iron_offset[0]:.6f}, {self.hard_iron_offset[1]:.6f}, {self.hard_iron_offset[2]:.6f}]\n\n")
                
                f.write("# Soft Iron Matrix\n")
                f.write("soft_iron_matrix = [\n")
                for row in self.soft_iron_matrix:
                    f.write(f"    [{row[0]:.6f}, {row[1]:.6f}, {row[2]:.6f}],\n")
                f.write("]\n")
                
            print(f"Calibration saved to mag_calibration_results.txt")
        except Exception as e:
            print(f"Error saving calibration to text file: {e}")
            
        # Save raw and calibrated data to CSV
        try:
            data = np.array(self.mag_data)
            centered_data = data - self.hard_iron_offset
            calibrated_data = np.dot(centered_data, self.soft_iron_matrix)
            
            csv_filename = f'mag_calibration_data_{timestamp}.csv'
            with open(csv_filename, 'w') as f:
                f.write("# Magnetometer Calibration Data\n")
                f.write(f"# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("raw_x,raw_y,raw_z,calibrated_x,calibrated_y,calibrated_z\n")
                
                for i in range(len(data)):
                    f.write(f"{data[i,0]:.6f},{data[i,1]:.6f},{data[i,2]:.6f},")
                    f.write(f"{calibrated_data[i,0]:.6f},{calibrated_data[i,1]:.6f},{calibrated_data[i,2]:.6f}\n")
                    
            print(f"Raw and calibrated data saved to {csv_filename}")
        except Exception as e:
            print(f"Error saving data to CSV: {e}")

    def plot_calibration(self):
        """Plot the calibration results."""
        if self.hard_iron_offset is None or self.soft_iron_matrix is None:
            return
            
        # Clear the previous ellipsoid if it exists
        if hasattr(self, 'ellipsoid_surface') and self.ellipsoid_surface:
            self.ellipsoid_surface.remove()

        # Original data points are already plotted in blue
        
        # Add the center (hard iron offset) point
        self.ax.scatter([self.hard_iron_offset[0]], 
                       [self.hard_iron_offset[1]], 
                       [self.hard_iron_offset[2]], 
                       c='r', s=100, marker='x', label='Hard Iron Offset')
        
        # Calculate and plot calibrated data
        data = np.array(self.mag_data)
        centered_data = data - self.hard_iron_offset
        calibrated_data = np.dot(centered_data, self.soft_iron_matrix)
        
        # Add calibrated points in green
        self.ax.scatter(calibrated_data[:, 0], 
                       calibrated_data[:, 1], 
                       calibrated_data[:, 2], 
                       c='g', marker='.', label='Calibrated')
        
        # Add the ellipsoid surface
        self.ellipsoid_surface = self._create_ellipsoid_surface()
        
        # Update title with calibration stats
        rms_error = np.sqrt(np.mean(np.sum((np.linalg.norm(calibrated_data, axis=1) - 
                                             np.mean(np.linalg.norm(calibrated_data, axis=1)))**2)))
        self.ax.set_title(f'Magnetometer Calibration\nRMS Error: {rms_error:.3f} μT')
        
        # Update the legend
        self.ax.legend()
        
        # Display calibration quality assessment
        self._assess_calibration_quality(calibrated_data)
        
        # Update the plot
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

        # Create and plot the ellipsoid surface
        self.ellipsoid_surface = self._create_ellipsoid_surface()
        if self.ellipsoid_surface is not None:
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
            
        

    def _create_ellipsoid_surface(self):
        """Create a wireframe ellipsoid surface to visualize the calibration."""
        if self.hard_iron_offset is None or self.soft_iron_matrix is None:
            return None

        # Create a unit sphere
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 20)
        x = np.outer(np.cos(u), np.sin(v))
        y = np.outer(np.sin(u), np.sin(v))
        z = np.outer(np.ones_like(u), np.cos(v))
        
        # Stack the sphere coordinates
        sphere_points = np.vstack([x.flatten(), y.flatten(), z.flatten()]).T
        
        # Calculate the average radius of the data from the center
        data = np.array(self.mag_data)
        centered_data = data - self.hard_iron_offset
        avg_radius = np.mean(np.sqrt(np.sum(centered_data**2, axis=1)))
        
        # Scale the sphere to the average radius
        sphere_points = sphere_points * avg_radius
        
        # Transform the sphere using the inverse of the soft iron matrix to get the ellipsoid
        # Note: we use the inverse because we're going from sphere to ellipsoid
        ellipsoid_points = np.dot(sphere_points, np.linalg.inv(self.soft_iron_matrix))
        
        # Add the hard iron offset to position the ellipsoid correctly
        ellipsoid_points = ellipsoid_points + self.hard_iron_offset
        
        # Reshape back to the grid
        x_ellipsoid = ellipsoid_points[:, 0].reshape(x.shape)
        y_ellipsoid = ellipsoid_points[:, 1].reshape(y.shape)
        z_ellipsoid = ellipsoid_points[:, 2].reshape(z.shape)
        
        # Create the surface
        return self.ax.plot_surface(
            x_ellipsoid, y_ellipsoid, z_ellipsoid, 
            rstride=1, cstride=1, color='r', alpha=0.1, linewidth=0.5
        )

    def run(self):
        """Main function to run the calibration tool."""
        if not self.connect_serial():
            return False
        
        # Print instructions for the user
        self.print_instructions()
            
        self.setup_plot()
        
        # Start the serial reading thread
        serial_thread = threading.Thread(target=self.read_serial_data)
        serial_thread.daemon = True
        serial_thread.start()
        
        # Main loop for plotting
        try:
            while self.running:
                self.update_plot()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        print("Calibration completed. Resources cleaned up.")

    def _update_guide_circles(self, center_x, center_y, center_z, radius):
        """Update the guide circles based on current data range."""
        if not self.guide_circles:
            return

        # Create circles with 100 points
        theta = np.linspace(0, 2*np.pi, 100)
        
        # XY-plane circle (blue)
        x_xy = center_x + radius * np.cos(theta)
        y_xy = center_y + radius * np.sin(theta)
        z_xy = np.full_like(theta, center_z)
        self.guide_circles[0].set_data_3d(x_xy, y_xy, z_xy)
        
        # XZ-plane circle (red)
        x_xz = center_x + radius * np.cos(theta)
        y_xz = np.full_like(theta, center_y)
        z_xz = center_z + radius * np.sin(theta)
        self.guide_circles[1].set_data_3d(x_xz, y_xz, z_xz)
        
        # YZ-plane circle (green)
        x_yz = np.full_like(theta, center_x)
        y_yz = center_y + radius * np.cos(theta)
        z_yz = center_z + radius * np.sin(theta)
        self.guide_circles[2].set_data_3d(x_yz, y_yz, z_yz)

    def print_instructions(self):
        """Print calibration instructions for the user."""
        print("\n" + "="*60)
        print("MAGNETOMETER CALIBRATION INSTRUCTIONS")
        print("="*60)
        print("1. Expected data format: 'x, y, z' with q8_7 int16 values (raw int16 values)")
        print("2. Move the magnetometer in figure-eight patterns covering all orientations")
        print("3. Try to fill the guide circles (red, green, blue) with data points")
        print("4. Cover each plane thoroughly - XY (blue), XZ (red), and YZ (green)")
        print("5. Keep the sensor moving until you see good coverage in all directions")
        print("6. When you stop moving the sensor for 1+ seconds, calibration will calculate")
        print("7. Calibration results will be saved to 'mag_calibration_results.txt'")
        print("8. Press Ctrl+C to exit when finished")
        print("="*60)
        print("NOTE: The script expects q8_7 int16 format values (divide by 128 to get μT)")
        print("Example: '1280, -640, 384' represents '10.0, -5.0, 3.0' μT")
        print("="*60 + "\n")

    def _assess_calibration_quality(self, calibrated_data):
        """Assess the quality of the calibration and display metrics."""
        # Calculate the mean radius and standard deviation
        radii = np.sqrt(np.sum(calibrated_data**2, axis=1))
        mean_radius = np.mean(radii)
        std_radius = np.std(radii)
        
        # Calculate relative standard deviation as a percentage
        relative_std = (std_radius / mean_radius) * 100
        
        # Calculate coverage metrics for each plane
        xy_coverage = self._calculate_plane_coverage(calibrated_data, plane='xy')
        xz_coverage = self._calculate_plane_coverage(calibrated_data, plane='xz')
        yz_coverage = self._calculate_plane_coverage(calibrated_data, plane='yz')
        
        # Print assessment
        print("\n----- Calibration Quality Assessment -----")
        print(f"Mean radius: {mean_radius:.2f} μT")
        print(f"Standard deviation: {std_radius:.2f} μT")
        print(f"Relative standard deviation: {relative_std:.2f}%")
        print(f"Coverage: XY plane: {xy_coverage:.1f}%, XZ plane: {xz_coverage:.1f}%, YZ plane: {yz_coverage:.1f}%")
        
        # Quality assessment
        if relative_std < 5.0 and min(xy_coverage, xz_coverage, yz_coverage) > 60:
            print("Calibration Quality: EXCELLENT")
        elif relative_std < 10.0 and min(xy_coverage, xz_coverage, yz_coverage) > 40:
            print("Calibration Quality: GOOD")
        elif relative_std < 15.0 and min(xy_coverage, xz_coverage, yz_coverage) > 20:
            print("Calibration Quality: ACCEPTABLE")
        else:
            print("Calibration Quality: POOR - Consider recalibrating")
            if xy_coverage < 40:
                print("  - Improve XY plane coverage (rotate in horizontal plane)")
            if xz_coverage < 40:
                print("  - Improve XZ plane coverage (pitch movements)")
            if yz_coverage < 40:
                print("  - Improve YZ plane coverage (roll movements)")
        
        print("---------------------------------------")
    
    def _calculate_plane_coverage(self, data, plane='xy'):
        """Calculate coverage percentage for a given plane."""
        # Divide the plane into a 6x6 grid and check how many cells have points
        grid_size = 6
        
        if plane == 'xy':
            x_idx, y_idx = 0, 1
        elif plane == 'xz':
            x_idx, y_idx = 0, 2
        else:  # yz
            x_idx, y_idx = 1, 2
            
        # Get the data for the two dimensions we're interested in
        x = data[:, x_idx]
        y = data[:, y_idx]
        
        # Find the min/max to create our grid
        x_min, x_max = np.min(x), np.max(x)
        y_min, y_max = np.min(y), np.max(y)
        
        # Add a small margin to avoid edge effects
        margin = 0.05
        x_range = x_max - x_min
        y_range = y_max - y_min
        x_min -= margin * x_range
        x_max += margin * x_range
        y_min -= margin * y_range
        y_max += margin * y_range
        
        # Create grid cells
        x_edges = np.linspace(x_min, x_max, grid_size + 1)
        y_edges = np.linspace(y_min, y_max, grid_size + 1)
        
        # Count points in each cell
        H, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])
        
        # Calculate coverage - percentage of cells that have at least one point
        coverage = np.sum(H > 0) / (grid_size * grid_size) * 100
        
        return coverage
    
    def load_calibration(self, filename='mag_calibration_results.txt'):
        """Load calibration parameters from a file."""
        try:
            # Define empty values in case loading fails
            hard_iron_offset = None
            soft_iron_matrix = None
            
            with open(filename, 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if line.startswith('hard_iron_offset'):
                        # Extract the vector from the line
                        values = line.split('[')[1].split(']')[0].split(',')
                        hard_iron_offset = np.array([float(v.strip()) for v in values])
                    
                    if line.startswith('soft_iron_matrix'):
                        # Extract the matrix, assuming it's on the next 3 lines
                        matrix = []
                        for j in range(i+1, i+4):  # Read the next 3 lines
                            if j < len(lines) and '[' in lines[j]:
                                values = lines[j].split('[')[1].split(']')[0].split(',')
                                matrix.append([float(v.strip()) for v in values])
                        if len(matrix) == 3:
                            soft_iron_matrix = np.array(matrix)
            
            if hard_iron_offset is not None and soft_iron_matrix is not None:
                print(f"Successfully loaded calibration from {filename}")
                return hard_iron_offset, soft_iron_matrix
            else:
                print(f"Failed to load calibration from {filename} - invalid format")
                return None, None
                
        except FileNotFoundError:
            print(f"Calibration file {filename} not found")
            return None, None
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return None, None
            
    def compare_with_previous_calibration(self, filename='mag_calibration_results.txt'):
        """Compare current calibration with a previously saved one."""
        prev_hard_iron, prev_soft_iron = self.load_calibration(filename)
        
        if prev_hard_iron is None or prev_soft_iron is None:
            return False
            
        if self.hard_iron_offset is None or self.soft_iron_matrix is None:
            print("No current calibration to compare with")
            return False
            
        # Calculate the difference between hard iron offsets
        hard_iron_diff = np.linalg.norm(self.hard_iron_offset - prev_hard_iron)
        
        # Calculate the difference between soft iron matrices using Frobenius norm
        soft_iron_diff = np.linalg.norm(self.soft_iron_matrix - prev_soft_iron, 'fro')
        
        print("\n----- Calibration Comparison -----")
        print(f"Hard Iron Offset Difference: {hard_iron_diff:.4f} μT")
        print(f"Soft Iron Matrix Difference: {soft_iron_diff:.4f}")
        
        # Interpret the differences
        if hard_iron_diff < 1.0 and soft_iron_diff < 0.1:
            print("Calibration Stability: EXCELLENT - Very similar to previous calibration")
        elif hard_iron_diff < 3.0 and soft_iron_diff < 0.3:
            print("Calibration Stability: GOOD - Close to previous calibration")
        else:
            print("Calibration Stability: POOR - Significant difference from previous calibration")
            print("This could indicate:")
            print("  - Environmental changes")
            print("  - Sensor position changes")
            print("  - Different interference sources")
            print("  - Issues with calibration procedure")
            
        print("---------------------------------------")
        return True
        

def main():
    """Main entry point."""
    print("\n=== Magnetometer Calibration Tool ===")
    print("This tool helps calibrate your magnetometer by calculating hard and soft iron offsets.")
    print("Follow the on-screen instructions to perform a proper calibration.")
    
    parser = argparse.ArgumentParser(description='Magnetometer Calibration Tool')
    parser.add_argument('--port', help='Serial port to use')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--compare', help='Compare with previous calibration file', action='store_true')
    parser.add_argument('--load', help='Load previous calibration file', default=None)
    parser.add_argument('--sim', help='Run in simulation mode (without serial device)', action='store_true')
    parser.add_argument('--timeout', type=float, default=1.0, help='Data timeout in seconds')
    args = parser.parse_args()
    
    calibrator = MagnetometerCalibrator(port=args.port, baud_rate=args.baud)
    
    # Set timeout if specified
    if args.timeout != 1.0:
        calibrator.data_timeout = args.timeout
        
    # Handle simulation mode if requested
    if args.sim:
        print("Running in simulation mode - generating random magnetometer data")
        # We'll create a simulation thread instead of connecting to serial
        sim_thread = threading.Thread(target=lambda: simulate_mag_data(calibrator))
        sim_thread.daemon = True
        sim_thread.start()
        calibrator.run()
    else:
        # Normal mode with serial connection
        result = calibrator.run()
        
        # Compare with previous calibration if requested
        if result and args.compare:
            calibrator.compare_with_previous_calibration()


def simulate_mag_data(calibrator):
    """Generate simulated magnetometer data for testing."""
    # Create an ellipsoid with known hard iron and soft iron parameters
    hard_iron = np.array([10.0, -5.0, 3.0])
    
    # Create a soft iron matrix that's not perfectly orthogonal
    soft_iron = np.array([
        [0.9, 0.1, 0.05],
        [0.1, 1.1, -0.1],
        [0.05, -0.1, 0.9]
    ])
    
    # Base radius of our simulated field
    base_radius = 40.0
    
    while calibrator.running:
        # Generate random point on a unit sphere
        theta = np.random.uniform(0, np.pi * 2)
        phi = np.random.uniform(0, np.pi)
        
        x = np.cos(theta) * np.sin(phi)
        y = np.sin(theta) * np.sin(phi)
        z = np.cos(phi)
        
        # Convert to numpy array
        point = np.array([x, y, z])
        
        # Scale to our desired radius
        point = point * base_radius
        
        # Apply soft iron distortion (inverse of what we'd apply in calibration)
        point = np.dot(point, np.linalg.inv(soft_iron))
        
        # Apply hard iron offset
        point = point + hard_iron
        
        # Add some noise
        noise = np.random.normal(0, 0.5, 3)
        point = point + noise
        
        # Convert floating-point values to q8_7 int16 format using helper function
        x_q8_7 = float_to_q8_7(point[0])
        y_q8_7 = float_to_q8_7(point[1])
        z_q8_7 = float_to_q8_7(point[2])
        
        # Format as a comma-separated string of integers
        data_line = f"{x_q8_7}, {y_q8_7}, {z_q8_7}"
        
        # Process the line as if it came from serial
        calibrator.process_line(data_line)
        
        # Sleep to simulate realistic data rate
        time.sleep(0.05)

def q8_7_to_float(value):
    """Convert q8_7 int16 fixed-point value to float.
    
    Args:
        value: Integer in q8_7 format (8 integer bits, 7 fractional bits)
        
    Returns:
        Floating point value
    """
    return value / 128.0

def float_to_q8_7(value):
    """Convert float to q8_7 int16 fixed-point value.
    
    Args:
        value: Floating point value
        
    Returns:
        Integer in q8_7 format, clipped to int16 range
    """
    int_value = int(round(value * 128))
    # Clip to int16 range
    return max(-32768, min(32767, int_value))

if __name__ == "__main__":
    main()