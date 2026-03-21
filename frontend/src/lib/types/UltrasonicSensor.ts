import { z } from 'zod';

export const UltrasonicSensorSchema = z.object({
    distance: z.number().min(-2, "Distance must be a non-negative number in cm"),
});

export type UltrasonicSensor = z.infer<typeof UltrasonicSensorSchema>;
    