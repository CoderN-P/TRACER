import threading
import time

import matplotlib.pyplot as plt
import numpy as np

from .models import Robot, SerialManager


class MagnetometerCalibrator:
    def __init__(self, port: str | None = None, timeout: float = 1.0):
        self.port = port or SerialManager.find_port()
        self.timeout = timeout

        self.serial_manager: SerialManager | None = None
        self.running = False
        self.last_data_time = 0.0

        self.lock = threading.Lock()
        self.mag_data: list[list[float]] = []
        self.x_data: list[float] = []
        self.y_data: list[float] = []
        self.z_data: list[float] = []

        self.hard_iron_offset: np.ndarray | None = None
        self.soft_iron_matrix: np.ndarray | None = None

        self.fig = None
        self.ax = None
        self.scatter = None
        self.guide_circles = []
        self.ellipsoid_surface = None

    def setup_plot(self):
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_xlabel("X (μT)")
        self.ax.set_ylabel("Y (μT)")
        self.ax.set_zlabel("Z (μT)")
        self.ax.set_title("Magnetometer Calibration")
        self.scatter = self.ax.scatter([], [], [], c="b", marker="o", label="Measurements")
        self._add_guide_circles()
        self.ax.legend()
        self.ax.set_box_aspect([1, 1, 1])
        plt.ion()
        plt.show(block=False)

    def _add_guide_circles(self):
        radius = 30
        theta = np.linspace(0, 2 * np.pi, 100)

        xy = self.ax.plot(radius * np.cos(theta), radius * np.sin(theta), np.zeros_like(theta), "b-", alpha=0.5, linewidth=2, label="XY plane")[0]
        xz = self.ax.plot(radius * np.cos(theta), np.zeros_like(theta), radius * np.sin(theta), "r-", alpha=0.5, linewidth=2, label="XZ plane")[0]
        yz = self.ax.plot(np.zeros_like(theta), radius * np.cos(theta), radius * np.sin(theta), "g-", alpha=0.5, linewidth=2, label="YZ plane")[0]

        self.guide_circles = [xy, xz, yz]
        self.ax.text(radius, 0, 0, "XY Plane", color="blue")
        self.ax.text(radius, 0, radius, "XZ Plane", color="red")
        self.ax.text(0, radius, radius, "YZ Plane", color="green")

    def _update_guide_circles(self, center_x, center_y, center_z, radius):
        if not self.guide_circles:
            return

        theta = np.linspace(0, 2 * np.pi, 100)
        self.guide_circles[0].set_data_3d(center_x + radius * np.cos(theta), center_y + radius * np.sin(theta), np.full_like(theta, center_z))
        self.guide_circles[1].set_data_3d(center_x + radius * np.cos(theta), np.full_like(theta, center_y), center_z + radius * np.sin(theta))
        self.guide_circles[2].set_data_3d(np.full_like(theta, center_x), center_y + radius * np.cos(theta), center_z + radius * np.sin(theta))

    def callback(self, packet: bytes):
        try:
            sensor_data = Robot.bytes_to_sensor_data(packet)
            mag = sensor_data.magnetometer
            
            if not mag.new:
                return
            
            x, y, z = mag.x, mag.y, mag.z

            if any(v > 100 or v < -100 for v in (x, y, z)):
                return

            with self.lock:
                self.mag_data.append([x, y, z])
                self.x_data.append(x)
                self.y_data.append(y)
                self.z_data.append(z)
                self.last_data_time = time.time()
                sample_count = len(self.mag_data)

            if sample_count % 10 == 0:
                print(f"Received: X={x:.2f} μT, Y={y:.2f} μT, Z={z:.2f} μT - Total samples: {sample_count}")
                if sample_count < 50:
                    print("Keep collecting data - move in all directions!")
                elif sample_count == 50:
                    print("\nGood progress! Now focus on filling the guide circles.")
                elif sample_count == 100:
                    print("\nExcellent! Continue rotating to cover all orientations.")
                elif sample_count == 200:
                    print("\nGreat dataset! When finished, hold still to auto-calculate calibration.")

        except Exception:
            return

    def update_plot(self):
        with self.lock:
            if not self.x_data:
                return

            xs = self.x_data.copy()
            ys = self.y_data.copy()
            zs = self.z_data.copy()

        self.scatter._offsets3d = (xs, ys, zs)

        max_range = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        if max_range <= 0:
            max_range = 1.0

        mid_x = (max(xs) + min(xs)) / 2
        mid_y = (max(ys) + min(ys)) / 2
        mid_z = (max(zs) + min(zs)) / 2

        self.ax.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
        self.ax.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
        self.ax.set_zlim(mid_z - max_range / 2, mid_z + max_range / 2)
        self._update_guide_circles(mid_x, mid_y, mid_z, max_range / 2)

        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def calculate_calibration(self):
        with self.lock:
            if len(self.mag_data) < 10:
                print("Not enough data for calibration")
                return False
            data = np.array(self.mag_data)

        try:
            offset = np.mean(data, axis=0)
            centered_data = data - offset
            h = np.dot(centered_data.T, centered_data) / len(centered_data)
            eigenvalues, eigenvectors = np.linalg.eigh(h)

            idx = np.argsort(eigenvalues)[::-1]
            eigenvalues = np.clip(eigenvalues[idx], 1e-12, None)
            eigenvectors = eigenvectors[:, idx]

            scale = np.sqrt(eigenvalues)
            w = eigenvectors @ np.diag(1 / scale) @ eigenvectors.T

            corrected = (w @ centered_data.T).T
            mean_radius = np.mean(np.linalg.norm(corrected, axis=1))
            target_field = 50.0
            scaling_factor = target_field / max(mean_radius, 1e-12)

            self.hard_iron_offset = offset
            self.soft_iron_matrix = w * scaling_factor

            print("\n----- Calibration Results -----")
            print(
                "Hard Iron Offset (μT): "
                f"[{self.hard_iron_offset[0]:.2f}, {self.hard_iron_offset[1]:.2f}, {self.hard_iron_offset[2]:.2f}]"
            )
            print("Soft Iron Matrix:")
            for row in self.soft_iron_matrix:
                print(f"  [{row[0]:.4f}, {row[1]:.4f}, {row[2]:.4f}]")

            self.plot_calibration()
            self.save_calibration()
            return True
        except Exception as error:
            print(f"Error calculating calibration: {error}")
            return False

    def save_calibration(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        try:
            with open("mag_calibration_results.txt", "w") as file:
                file.write("# Magnetometer Calibration Results\n")
                file.write(f"# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                file.write("# Hard Iron Offset (μT)\n")
                file.write(
                    "hard_iron_offset = "
                    f"[{self.hard_iron_offset[0]:.6f}, {self.hard_iron_offset[1]:.6f}, {self.hard_iron_offset[2]:.6f}]\n\n"
                )
                file.write("# Soft Iron Matrix\n")
                file.write("soft_iron_matrix = [\n")
                for row in self.soft_iron_matrix:
                    file.write(f"    [{row[0]:.6f}, {row[1]:.6f}, {row[2]:.6f}],\n")
                file.write("]\n")
            print("Calibration saved to mag_calibration_results.txt")
        except Exception as error:
            print(f"Error saving calibration to text file: {error}")

        try:
            with self.lock:
                data = np.array(self.mag_data)
            centered_data = data - self.hard_iron_offset
            calibrated_data = np.dot(centered_data, self.soft_iron_matrix)

            csv_filename = f"mag_calibration_data_{timestamp}.csv"
            with open(csv_filename, "w") as file:
                file.write("# Magnetometer Calibration Data\n")
                file.write(f"# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write("raw_x,raw_y,raw_z,calibrated_x,calibrated_y,calibrated_z\n")
                for index in range(len(data)):
                    file.write(
                        f"{data[index, 0]:.6f},{data[index, 1]:.6f},{data[index, 2]:.6f},"
                        f"{calibrated_data[index, 0]:.6f},{calibrated_data[index, 1]:.6f},{calibrated_data[index, 2]:.6f}\n"
                    )
            print(f"Raw and calibrated data saved to {csv_filename}")
        except Exception as error:
            print(f"Error saving data to CSV: {error}")

    def _create_ellipsoid_surface(self):
        if self.hard_iron_offset is None or self.soft_iron_matrix is None:
            return None

        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 20)
        x = np.outer(np.cos(u), np.sin(v))
        y = np.outer(np.sin(u), np.sin(v))
        z = np.outer(np.ones_like(u), np.cos(v))

        sphere_points = np.vstack([x.flatten(), y.flatten(), z.flatten()]).T

        with self.lock:
            data = np.array(self.mag_data)

        centered_data = data - self.hard_iron_offset
        avg_radius = np.mean(np.sqrt(np.sum(centered_data**2, axis=1)))
        sphere_points *= avg_radius

        ellipsoid_points = np.dot(sphere_points, np.linalg.inv(self.soft_iron_matrix)) + self.hard_iron_offset
        x_ellipsoid = ellipsoid_points[:, 0].reshape(x.shape)
        y_ellipsoid = ellipsoid_points[:, 1].reshape(y.shape)
        z_ellipsoid = ellipsoid_points[:, 2].reshape(z.shape)

        return self.ax.plot_surface(x_ellipsoid, y_ellipsoid, z_ellipsoid, rstride=1, cstride=1, color="r", alpha=0.1, linewidth=0.5)

    def _calculate_plane_coverage(self, data, plane="xy"):
        grid_size = 6
        if plane == "xy":
            x_idx, y_idx = 0, 1
        elif plane == "xz":
            x_idx, y_idx = 0, 2
        else:
            x_idx, y_idx = 1, 2

        x = data[:, x_idx]
        y = data[:, y_idx]

        x_min, x_max = np.min(x), np.max(x)
        y_min, y_max = np.min(y), np.max(y)

        margin = 0.05
        x_range = x_max - x_min
        y_range = y_max - y_min
        x_min -= margin * x_range
        x_max += margin * x_range
        y_min -= margin * y_range
        y_max += margin * y_range

        x_edges = np.linspace(x_min, x_max, grid_size + 1)
        y_edges = np.linspace(y_min, y_max, grid_size + 1)
        hist, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])
        return np.sum(hist > 0) / (grid_size * grid_size) * 100

    def _assess_calibration_quality(self, calibrated_data):
        radii = np.sqrt(np.sum(calibrated_data**2, axis=1))
        mean_radius = np.mean(radii)
        std_radius = np.std(radii)
        relative_std = (std_radius / max(mean_radius, 1e-12)) * 100

        xy_coverage = self._calculate_plane_coverage(calibrated_data, plane="xy")
        xz_coverage = self._calculate_plane_coverage(calibrated_data, plane="xz")
        yz_coverage = self._calculate_plane_coverage(calibrated_data, plane="yz")

        print("\n----- Calibration Quality Assessment -----")
        print(f"Mean radius: {mean_radius:.2f} μT")
        print(f"Standard deviation: {std_radius:.2f} μT")
        print(f"Relative standard deviation: {relative_std:.2f}%")
        print(f"Coverage: XY plane: {xy_coverage:.1f}%, XZ plane: {xz_coverage:.1f}%, YZ plane: {yz_coverage:.1f}%")

        if relative_std < 5.0 and min(xy_coverage, xz_coverage, yz_coverage) > 60:
            print("Calibration Quality: EXCELLENT")
        elif relative_std < 10.0 and min(xy_coverage, xz_coverage, yz_coverage) > 40:
            print("Calibration Quality: GOOD")
        elif relative_std < 15.0 and min(xy_coverage, xz_coverage, yz_coverage) > 20:
            print("Calibration Quality: ACCEPTABLE")
        else:
            print("Calibration Quality: POOR - Consider recalibrating")
        print("---------------------------------------")

    def plot_calibration(self):
        if self.hard_iron_offset is None or self.soft_iron_matrix is None:
            return

        if self.ellipsoid_surface is not None:
            self.ellipsoid_surface.remove()

        with self.lock:
            data = np.array(self.mag_data)

        centered_data = data - self.hard_iron_offset
        calibrated_data = np.dot(centered_data, self.soft_iron_matrix)

        self.ax.scatter([self.hard_iron_offset[0]], [self.hard_iron_offset[1]], [self.hard_iron_offset[2]], c="r", s=100, marker="x", label="Hard Iron Offset")
        self.ax.scatter(calibrated_data[:, 0], calibrated_data[:, 1], calibrated_data[:, 2], c="g", marker=".", label="Calibrated")

        self.ellipsoid_surface = self._create_ellipsoid_surface()
        rms_error = np.sqrt(
            np.mean(
                np.sum(
                    (
                        np.linalg.norm(calibrated_data, axis=1)
                        - np.mean(np.linalg.norm(calibrated_data, axis=1))
                    )
                    ** 2
                )
            )
        )
        self.ax.set_title(f"Magnetometer Calibration\nRMS Error: {rms_error:.3f} μT")
        self.ax.legend()
        self._assess_calibration_quality(calibrated_data)
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def print_instructions(self):
        print("\n" + "=" * 60)
        print("MAGNETOMETER CALIBRATION INSTRUCTIONS")
        print("=" * 60)
        print("1. Move the robot in figure-eight patterns covering all orientations")
        print("2. Fill the guide circles for XY, XZ, and YZ planes")
        print("3. Keep moving until you have broad 3D coverage")
        print("4. Hold still for the timeout duration to auto-calculate")
        print("5. Press Ctrl+C to stop manually")
        print("=" * 60 + "\n")

    def cleanup(self):
        self.running = False
        if self.serial_manager is not None:
            self.serial_manager.stop()
        print("Calibration completed. Resources cleaned up.")

    def run(self):
        if not self.port:
            print("No serial port found. Please connect the robot.")
            return False

        self.serial_manager = SerialManager(self.port, 921600)
        self.running = True
        self.last_data_time = time.time()

        self.print_instructions()
        self.setup_plot()
        self.serial_manager.start_read(callback=self.callback)

        try:
            while self.running:
                self.update_plot()
                with self.lock:
                    sample_count = len(self.mag_data)
                    age = time.time() - self.last_data_time if self.last_data_time > 0 else 0

                if sample_count >= 10 and age > self.timeout:
                    print("Data timeout - calculating calibration...")
                    self.calculate_calibration()
                    break

                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Interrupted by user - calculating calibration with current data...")
            self.calculate_calibration()
        finally:
            self.cleanup()

        return True


def calibrate_mag(port: str | None = None, timeout: float = 1.0):
    calibrator = MagnetometerCalibrator(port=port, timeout=timeout)
    calibrator.run()