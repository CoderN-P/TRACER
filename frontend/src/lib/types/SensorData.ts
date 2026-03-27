import { z } from 'zod';
import { UltrasonicSensorSchema } from "./UltrasonicSensor";
import { IMUSchema } from "./IMU";
import { MagnetometerSchema } from "./Magnetometer";
import { TOFSchema } from "./TOF";

export const SensorDataSchema = z.object({
    ultrasonic: UltrasonicSensorSchema,
    imu: IMUSchema,
    tof: TOFSchema,
    magnetometer: MagnetometerSchema,
    ir_front: z.boolean(),
    ir_back: z.boolean(),
    battery: z.number().min(0).max(100),
    timestamp: z.number().describe("Timestamp of the sensor data in microseconds since epoch"),
    left_encoder: z.number().describe("Left wheel encoder count"),
    right_encoder: z.number().describe("Right wheel encoder count"),
    motors_enabled: z.boolean().describe("Whether the motors are enabled or not"),
    packet_num: z.number().describe("Sequential packet number for tracking data packets"),
});

export type SensorData = z.infer<typeof SensorDataSchema>;