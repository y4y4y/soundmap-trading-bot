import psutil
import pygetwindow as gw
import pyautogui
import sys
import time
import cv2

def findProcess():
    name = "BlueStacks"
    
    # Find the process
    for process in psutil.process_iter(['name']):
        if name.lower() in process.info['name'].lower():
            pid = process.pid
            
            # Find the window associated with the process
            try:
                windows = gw.getWindowsWithTitle(name)
                if not windows:
                    print(f"Process '{name}' found, but no visible window.")
                    return

                window = windows[0]
                
                # Move the window to the top-left corner
                window.moveTo(0, 0)
                
                # Try to activate the window, but handle errors
                focusGame(window)

                print(f"Process '{name}' found and moved to top-left corner.")
                return window
            except Exception as e:
                print(f"Error handling window: {e}")
                return 
    
    print(f"Process '{name}' not found.")
    sys.exit()

def focusGame(window):
    # Try to activate the window, but handle errors
    try:
        window.activate()
        print("Game window focused.")
    except Exception as e:
        print(f"Error activating window: {e}. The window may not be in a state to be activated.")

def clickTradeButton(x, y):
    # Move the mouse to the specified coordinates and click
    pyautogui.click(x, y)
    print(f"Clicked trade button at ({x}, {y}).")

def openTrades():
    time.sleep(2)
    print("Opening trades...")
    pyautogui.click(596, 64)

def closeTrades():
    time.sleep(2)
    print("Closing trades...")
    pyautogui.click(38, 57)

def refreshTrades():
    # Simulate pulling down to refresh the trades page
    print("Refreshing trades...")
    # Adjust these coordinates based on your screen
    pull_down_start_x = 300  # Starting x coordinate for pull down
    pull_down_start_y = 500  # Starting y coordinate for pull down
    pull_down_end_y = 700     # Ending y coordinate for pull down

    # Move to the starting position and click and drag down
    pyautogui.moveTo(pull_down_start_x, pull_down_start_y)
    pyautogui.mouseDown()  # Press the mouse button down
    pyautogui.moveTo(pull_down_start_x, pull_down_end_y, duration=0.5)  # Drag down
    pyautogui.mouseUp()    # Release the mouse button
    print("Trades refreshed.")

def checkForTradeOffer():
    # Check if the trade offer screen is displayed
    print("Checking for trade offer...")
    trade_offer_image = 'trade_offer.png'  # Path to your screenshot
    try: 
        location = pyautogui.locateOnScreen(trade_offer_image, confidence=0.8)  # Adjust confidence as needed
    except Exception as e:
        print(f"Error checking for trade offer: {e}")
        return False

    if location:
        print("Trade offer screen detected!")
        return True
    else:
        print("Trade offer screen not detected.")
        return False
    
def acceptTradeOffer():
    print("Accepting trade offer...")
    accept_button_x = 458  # Replace with your x coordinate
    accept_button_y = 560  # Replace with your y coordinate
    clickTradeButton(accept_button_x, accept_button_y)
    time.sleep(1)
    clickTradeButton(accept_button_x, accept_button_y)
    time.sleep(1)
    clickTradeButton(407, 554)
    print("Trade offer accepted.")

# Call the function
print("Starting...")
print("Searching for process...")
time.sleep(2)  # Add a small delay before searching
process = findProcess()
input("Press Enter once you opened SoundMap")
time.sleep(5)
# Adjust the x and y coordinates as needed
trade_button_x = 246  # Replace with your x coordinate
trade_button_y = 1129  # Replace with your y coordinate
clickTradeButton(trade_button_x, trade_button_y)
print("Process handling completed")
time.sleep(2)
openTrades()
time.sleep(2)
refreshTrades()
time.sleep(2)

# Call the refreshTrades function
if checkForTradeOffer():
    print("Trade offer detected")
    acceptTradeOffer()
    time.sleep(2)
    refreshTrades()
    time.sleep(2)

else:
    print("No trade offer detected")



