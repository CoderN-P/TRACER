import matplotlib.pyplot as plt
from .models.Communication.LidarReader import LidarReader
import asyncio

def lidar_test(port=None):
    """
    Continuously plot cartesian LIDAR scans.
    
    Args:
        port: Serial port for the LIDAR device (default: /dev/ttyUSB0)
    """
    # Initialize LIDAR reader
    lidar_reader = LidarReader(port=port or '/dev/ttyUSB0')
    
    # Set up matplotlib for continuous plotting
    plt.ion()  # Enable interactive mode
    fig, ax = plt.subplots(figsize=(8, 8))
    plt.show(block=False)
    
    
    def plot_callback(scan):
        """Callback function to plot each completed scan."""
        # Clear previous plot
        ax.clear()
        
        # Convert polar to cartesian coordinates
        cartesian_points = scan.to_cartesian()
        
        if cartesian_points:
            # Unzip the points
            x_coords, y_coords, quality = zip(*cartesian_points)
            # Plot the points
            
            scatter = ax.scatter(
                x_coords,
                y_coords,
                c=quality,
                cmap="viridis",
                vmin=0,
                vmax=63,
                s=8,
                edgecolors="none",
            )
            ax.scatter(
                0,
                0,
                c="red",
                marker="x",
                s=80,
                linewidths=2,
                label="LIDAR",
            )

            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Y (mm)')
            ax.set_title('LIDAR Cartesian Scan')
            ax.axis('equal')
            ax.grid(True, alpha=0.3)
            ax.legend(loc="upper right")
            
            if not hasattr(plot_callback, "colorbar"):
                plot_callback.colorbar = fig.colorbar(scatter, ax=ax)
                plot_callback.colorbar.set_label("Return Quality (0-63)")
            else:
                plot_callback.colorbar.update_normal(scatter)
            
            # Fixed viewing window (±5 m)
            ax.set_xlim(-5, 5)
            ax.set_ylim(-5, 5)
        
        # Update the plot
        fig.canvas.draw_idle()
        plt.pause(0.001)
    
    
    # Run the scan loop
    try:
        asyncio.run(lidar_reader.scan_loop(plot_callback))
    except KeyboardInterrupt:
        print("LIDAR test stopped by user")
    finally:
        plt.close(fig)
