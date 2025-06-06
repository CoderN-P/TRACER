import { z } from 'zod';

export const UltrasonicSensorSchema = z.object({
    distance: z.number().min(-1, "Distance must be a non-negative number in cm"),
});

export type UltrasonicSensor = z.infer<typeof UltrasonicSensorSchema>;
    