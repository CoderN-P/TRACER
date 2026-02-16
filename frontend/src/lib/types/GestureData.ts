import { z } from "zod";

/**
 * Represents accelerometer data from wireless sifive board. Units are Gs
 */
export const AccelerometerDataSchema = z.object({
  x: z.number().default(0.0),
  y: z.number().default(0.0),
  z: z.number().default(0.0)
});

export type AccelerometerData = z.infer<typeof AccelerometerDataSchema>;

/**
 * Represents ambient light data from wireless sifive board.
 */
export const AmbientLightDataSchema = z.object({
  lux: z.number().default(0.0),
  ch0: z.number().int().default(0),
  ch1: z.number().int().default(0)
});

export type AmbientLightData = z.infer<typeof AmbientLightDataSchema>;

/**
 * Represents magnetometer data from wireless sifive board.
 */
export const MagnetometerDataSchema = z.object({
  x: z.number().default(0.0),
  y: z.number().default(0.0),
  z: z.number().default(0.0)
});

export type MagnetometerData = z.infer<typeof MagnetometerDataSchema>;

/**
 * Represents magnetometer angle data from wireless sifive board.
 */
export const MagnetometerAngleDataSchema = z.object({
  heading: z.number().default(0.0),
  pitch: z.number().default(0.0),
  roll: z.number().default(0.0)
});

export type MagnetometerAngleData = z.infer<typeof MagnetometerAngleDataSchema>;

/**
 * Represents gesture data from wireless sifive board.
 */
export const GestureDataSchema = z.object({
  temperature: z.number().default(0.0),
  accelerometer: AccelerometerDataSchema.default({}),
  light: AmbientLightDataSchema.default({}),
  magnetometer: MagnetometerDataSchema.default({}),
  mag_angles: MagnetometerAngleDataSchema.default({})
});

export type GestureData = z.infer<typeof GestureDataSchema>;

// Export all schemas and types
export default {
  AccelerometerDataSchema,
  AmbientLightDataSchema,
  MagnetometerDataSchema,
  MagnetometerAngleDataSchema,
  GestureDataSchema
};
