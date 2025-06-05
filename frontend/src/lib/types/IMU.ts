import { z } from 'zod';

export const IMUSchema = z.object({
    acceleration_x: z.number(),
    acceleration_y: z.number(),
    acceleration_z: z.number(),
    gyroscope_x: z.number(),
    gyroscope_y: z.number(),
    gyroscope_z: z.number(),
    temperature: z.number(),
});

export type IMU = z.infer<typeof IMUSchema>;