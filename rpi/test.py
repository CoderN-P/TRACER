import asyncio
from rplidarc1 import RPLidar

async def main():
    # Targets the exact serial address your Mac printed
    port = '/dev/serial0'
    baudrate = 460800

    print("Initializing LiDAR connection...")
    lidar = RPLidar(port, baudrate)

    async def scan():
        try:
            print("Pinging scan register...")
            async for scan_data in lidar.simple_scan():
                if scan_data:
                    print(f"Success! Captured {len(scan_data)} tracking points.")
                    break
        except Exception as e:
            print(f"Scanning loop crash: {e}")
        finally:
            lidar.reset()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(scan())

if __name__ == "__main__":
    asyncio.run(main())
