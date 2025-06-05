import { z } from 'zod';

export const DistanceEntrySchema = z.object({
    distance: z.number(),
    timestamp: z.string().datetime(),
});

export type DistanceEntry = z.infer<typeof DistanceEntrySchema>;
