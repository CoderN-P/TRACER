import { z } from 'zod';

export const LogEntrySchema = z.object({
    timestamp: z.string().datetime(),
    message: z.string(),
    icon: z.string().optional(),
});

export type LogEntry = z.infer<typeof LogEntrySchema>;