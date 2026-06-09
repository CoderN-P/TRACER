import { z } from 'zod';

export const RobotStateSchema = z.object({
  x: z.number().describe("X position of the robot in meters"),
  y: z.number().describe("Y position of the robot in meters"),
  yaw: z.number().describe("Heading of the robot in radians"),
  pitch: z.number().describe("Pitch of the robot in radians"),
  roll: z.number().describe("Roll of the robot in radians"),
  linear_velocity: z.number().describe("Linear velocity of the robot in cm/s in its forward direction"),
  angular_velocity: z.number().describe("Angular velocity of the robot in radians/s"),
  v_left: z.number().describe("Velocity of the left motor"),
  v_right: z.number().describe("Velocity of the right motor"),
});

export type RobotState = z.infer<typeof RobotStateSchema>;

