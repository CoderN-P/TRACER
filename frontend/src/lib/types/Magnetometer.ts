import { z } from 'zod';

export const MagnetometerSchema = z.object({
  x: z.number().describe("Magnetic field strength in the X direction in microteslas (µT)"),
  y: z.number().describe("Magnetic field strength in the Y direction in microteslas (µT)"),
  z: z.number().describe("Magnetic field strength in the Z direction in microteslas (µT)"),
  heading: z.number().describe("Heading calculated from magnetometer data in degrees"),
  new: z.boolean().describe("Indicates if the magnetometer data is new and has not been processed yet"),
});

export type Magnetometer = z.infer<typeof MagnetometerSchema>;

