import pygame
import time

# Initialize pygame and joystick
pygame.init()
pygame.joystick.init()

# Check for controllers
if pygame.joystick.get_count() == 0:
    print("No controllers found")
    exit()

# Get the first controller
controller = pygame.joystick.Joystick(0)
controller.init()

print(f"Controller: {controller.get_name()}")
print(f"Number of axes: {controller.get_numaxes()}")
print(f"Number of buttons: {controller.get_numbuttons()}")

# Main loop
clock = pygame.time.Clock()
running = True

while running:
    pygame.event.pump()

    # Read button states
    for i in range(controller.get_numbuttons()):
        if controller.get_button(i):
            print(f"Button {i} pressed")

    # Read analog stick values
    left_x = controller.get_axis(0)
    left_y = controller.get_axis(1)
    right_x = controller.get_axis(2)
    right_y = controller.get_axis(3)

    # Read triggers (usually axes 4 and 5)
    left_trigger = controller.get_axis(4)
    right_trigger = controller.get_axis(5)

    # Only print if there's significant input
    if left_x == -1:
        print("Going left")
    elif left_x == 1:
        print("Going right")
        
    if left_y == -1:
        print("Going forward")
    elif left_y == 1:
        print("Going backward")

    clock.tick(60)  # 60 FPS