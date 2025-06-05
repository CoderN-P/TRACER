import { z } from 'zod';

export const JoystickSchema = z.object({
    left_y: z.number(),
    right_x: z.number(),
});

export type Joystick = z.infer<typeof JoystickSchema>;