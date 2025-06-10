import { z } from 'zod';
import { UltrasonicSensorSchema } from "./UltrasonicSensor";
import { IMUSchema } from "./IMU";

export const SensorDataSchema = z.object({
    ultrasonic: UltrasonicSensorSchema,
    imu: IMUSchema,
    ir_front: z.boolean(),
    ir_back: z.boolean(),
    battery: z.number().min(0).max(100),
});

export type SensorData = z.infer<typeof SensorDataSchema>;