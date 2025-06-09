import { z } from 'zod';
import {CommandType} from "$lib/types/CommandType";
import {LCDCommandSchema} from "$lib/types/LCDCommand";
import {MotorCommandSchema} from "$lib/types/MotorCommand";

export const CommandSchema = z.object({
    ID: z.string(),
    command_type: z.nativeEnum(CommandType),
    command: z.union([LCDCommandSchema, MotorCommandSchema]).nullable(),
    duration: z.number(),
    pause_duration: z.number()
});

export type Command = z.infer<typeof CommandSchema>;