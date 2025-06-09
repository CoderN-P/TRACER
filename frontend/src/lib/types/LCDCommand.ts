import { z } from 'zod';

export const LCDCommandSchema = z.object({
    line_1: z.string().max(16),
    line_2: z.string().max(16),
});

export type LCDCommand = z.infer<typeof LCDCommandSchema>;