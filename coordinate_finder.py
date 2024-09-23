import pyautogui
import time

print("Move your mouse to the desired location and wait for 5 seconds...")
time.sleep(5)

# Get the current mouse position
x, y = pyautogui.position()
print(f"Mouse position: ({x}, {y})")