import { z } from 'zod';

export const TOFSchema = z.object({
  distance_front: z
    .number()
    .describe('Distance measured by the front Time-of-Flight sensor in centimeters'),
});

export type TOF = z.infer<typeof TOFSchema>;
