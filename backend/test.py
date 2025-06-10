import time, struct
import serial

# Open serial port
arduino = serial.Serial('/dev/cu.usbserial-120', 115200, timeout=1)
print("Connected to Arduino")

while True:
    try:
        # Clear any pending data
        arduino.reset_input_buffer()

        # Record start time
        command = input("Enter command (e.g., 'm', 's', 'd', 'l): ").strip().lower()
        
        if command == 'm':
            speed_left, speed_right = map(lambda x: int(x), input("Enter left and right speeds (e.g., 100 -100): ").split())
            # Send command to request sensor data
            if abs(speed_left) > 0 or abs(speed_right) > 0:
                cmd_packet = struct.pack("<Bhh", 0x01, speed_left, speed_right)
            else:
                cmd_packet = struct.pack("<B", 0x04)  # Stop command
        elif command == 's':
            # Send command to stop motors
            cmd_packet = struct.pack("<B", 0x04)
        elif command == 'd':
            # Send command to request sensor data
            cmd_packet = struct.pack("<B", 0x03)
        elif command == 'l':
            l1 = input("Enter line 1 (max 16 chars): ")[:16].ljust(16)
            l2 = input("Enter line 2 (max 16 chars): ")[:16].ljust(16)
            cmd_packet = struct.pack("<B16s16s", 0x02, l1.encode('utf-8'), l2.encode('utf-8'))
        else:
            print("Invalid command")
            continue
    
        
        checksum = sum(cmd_packet) & 0xFF
        arduino.write(cmd_packet + bytes([checksum]))

        # Wait for response with timeout
        timeout = 1.0  # seconds
        response_received = False
        response_time = None

        start_time = time.time()

        while time.time() - start_time < timeout and not response_received:
            if arduino.in_waiting >= 24:  # Full sensor packet size
                # Record when we got the data
                response_time = time.time() - start_time

                # Read the data (start with header)
                start_byte = arduino.read(1)

                if start_byte[0] == 0xAA:  # Valid start byte
                    # Read the rest of the packet
                    data = start_byte + arduino.read(23)
                    response_received = True

                    print(f"Response received in {response_time*1000:.2f} ms")
                    fields = struct.unpack('<BfhhhhhhfBBB', data)
                    start, distance, ax, ay, az, gx, gy, gz, temp, ir_flags, battery, received_checksum = fields
            
                    # Calculate checksum (sum of all bytes except start byte and checksum byte)
                    calculated_checksum = sum(data[1:-1]) & 0xFF
                    valid = calculated_checksum == received_checksum
            
                    if not valid:
                        print(f"Invalid checksum: calculated={calculated_checksum}, received={received_checksum}")
                        continue
            
                    # Extract IR flags
                    ir_front = not bool(ir_flags & 0b00000001)
                    ir_back = not bool(ir_flags & 0b00000010)
            
                    print(
                        f"Distance: {distance}cm, "
                        f"Accel: ({ax/16384:.2f}g, {ay/16384:.2f}g, {az/16384:.2f}g), "
                        f"Gyro: ({gx/131:.2f}°/s, {gy/131:.2f}°/s, {gz/131:.2f}°/s), "
                        f"Temp: {temp:.1f}°C, "
                        f"IR Front: {'Floor' if ir_front else 'Cliff'}, "
                        f"IR Back: {'Floor' if ir_back else 'Cliff'}",
                        f"Battery: {battery}%"
                    )
                else:
                    print(f"Invalid start byte: {hex(start_byte[0])}")

        if not response_received:
            print("Timeout waiting for response")
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
