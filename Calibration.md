# Calibration


## Feedforward calibration

Feedforward and motor calibration must be reset when changing motors, wheels, or the batteries. 

1. Calibrate left and right correction for `METERS_PER_TICK` by running `rpi/main.py --calibrate-wheel`. This test will drive the robot forward for a given duration at a given velocity and measure the error. The correction factor is applied to the left or right side to correct for the error. This is necessary because of manufacturing tolerances in the motors and wheels.
2. Calibrate the static friction gain (kS) for each motor by running `rpi/main.py --calibrate-ks`. This will test lower and lower PWM values until the motors stop moving.
3. Calibrate the velocity gain (kV) for each motor by running `rpi/main.py --calibrate-kv`. This will test various pwm values and measure the velocity of the robot. 
4. Calculate max velocity (v_max) for each motor by running `rpi/main.py --calibrate-max-velocity`. The lowest of the two max velocities is used as the max velocity for the robot. This is necessary because of differences in the motors and batteries.

## PID calibration

Feedforward contributes to most of the control effort, but PID is necessary to correct for errors and disturbances. PID calibration is not necessary for the robot to function, but it can improve performance.

[TODO: Add PID calibration instructions]

## Wheelbase calibration

Run `rpi/main.py --calibrate-wheelbase` to calibrate the wheelbase. This will drive the robot in a circle and measure the radius of the circle. The wheelbase is then calculated from the radius and the velocity of the robot.

## Magnetometer calibration

Run `backend/mag_calibration.py` to calibrate the magnetometer (NOTE: requires `/arduino/test/magnetomer/magnetometer.ino` to be uploaded to the microcontroller). This will collect magnetometer readings while the robot is rotated in various orientations. The collected data is then used to calculate the hard iron and soft iron calibration parameters, which are saved to `backend/mag_calibration.json`. These parameters are used to correct the magnetometer readings for accurate heading estimation.

## Pose EKF calibration

Calibrate the following config parameters:

```
P_THETA: float = 0.1 # Uncertainty in heading (radians)
P_GYRO_BIAS: float = 1.0e-4 # Uncertainty in gyro bias (rad/s)
P_THETA_BIAS: float = 0.0 # Initial covariance between heading and gyro bias

Q_THETA_1: float = 1.0e-4 # Process noise in heading (radians^2/s)
Q_BIAS: float = 1.0e-6 # Process noise in gyro
```

[TODO: Add further Pose EKF calibration instructions]

## RAMSETE calibration

Start with the default RAMSETE parameters (b = 2.0, zeta = 0.7) and test the robot's ability to follow a path. If the robot is oscillating around the path, try increasing the b parameter to make it more aggressive. If the robot is too slow to respond to changes in the path, try decreasing the zeta parameter to make it more responsive.

[TODO: Add RAMSETE calibration instructions]

## Pure Pursuit calibration

Try out different lookahead distances and see how it affects the robot's ability to follow a path. A smaller lookahead distance will make the robot more responsive but may cause it to oscillate, while a larger lookahead distance will make the robot smoother but less responsive.