import { z } from 'zod';

export const MotorCommandSchema = z.object({
    left_motor: z.number(),
    right_motor: z.number(),
});

export type MotorCommand = z.infer<typeof MotorCommandSchema>;