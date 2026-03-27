import { z } from 'zod';

export const DistanceEntrySchema = z.object({
    distance_left: z.number(),
    distance_right: z.number(),
    distance_front: z.number(),
    distance: z.number(),
    timestamp: z.string().datetime(),
});

export type DistanceEntry = z.infer<typeof DistanceEntrySchema>;
