import { z } from 'zod';
import { UltrasonicSensorSchema } from "./UltrasonicSensor";
import { IMUSchema } from "./IMU";
import { MagnetometerSchema } from "./Magnetometer";

export const SensorDataSchema = z.object({
    ultrasonic: UltrasonicSensorSchema,
    imu: IMUSchema,
    magnetometer: MagnetometerSchema,
    ir_front: z.boolean(),
    ir_back: z.boolean(),
    battery: z.number().min(0).max(100),
    timestamp: z.number().describe("Timestamp of the sensor data in microseconds since epoch"),
    leftEncoder: z.number().describe("Left wheel encoder count"),
    rightEncoder: z.number().describe("Right wheel encoder count"),
    
});

export type SensorData = z.infer<typeof SensorDataSchema>;