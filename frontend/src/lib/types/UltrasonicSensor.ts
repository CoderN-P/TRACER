import { z } from 'zod';

const UltrasonicSensorInputSchema = z.object({
    distance_left: z.number().describe("Distance measured by the left ultrasonic sensor in centimeters"),
    distance_right: z.number().describe("Distance measured by the right ultrasonic sensor in centimeters"),
    distance: z.number().optional().describe("Compatibility distance metric in centimeters"),
});

export const UltrasonicSensorSchema = UltrasonicSensorInputSchema.transform((value) => ({
    ...value,
    distance: value.distance ?? Math.min(value.distance_left, value.distance_right),
}));

export type UltrasonicSensor = z.infer<typeof UltrasonicSensorSchema>;
    