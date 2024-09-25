import json, cloudscraper, uuid, time
import urllib.parse
from colorama import Fore, Style, init
from tqdm import tqdm
import os
import requests  # Add this import for sending webhook messages

# Initialize colorama
init(autoreset=True)

username = ""
user_id = ""
bio = ""
coins = ""
trades_completed = ""
max_trades = 10
curr_trades = 0

available_songs = []
listed_songs = []
active_offers = []

scraper = cloudscraper.create_scraper()

print("Starting...")
print("Loading config...")
with open("config.json", "r") as f:
    config = json.load(f)
print("Config loaded.")
auth_token = config["auth"]
cookie = config["cf_cookie"]
webhook_url = config["discord_webhook_url"]  # Add this line
headers = {
    'content-type':'application/json',
    'version':'1.34.0',
    'platform':'android',
    'timezone':'Asia/Shanghai',
    'authorization':f'{auth_token}',
    'accept-encoding':'gzip',
    'user-agent':'okhttp/4.12.0',
    'cookie':f'{cookie}'
}

# Add this new function to send Discord webhook messages
def send_discord_webhook(message):
    payload = {"content": message}
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Discord webhook: {e}")

def updateUserInfo():
    url = "https://api2.soundmap.dev/trpc/initialState?batch=1&input=%7B%7D"
    res = scraper.get(url, headers=headers)
    if res.status_code != 200:
        print("Error: Failed to fetch user info.")
        with open("error.log", "a") as f:
            f.write(f"Error: Failed to fetch user info.\n")
            f.write(f"Response: {res.text}\n")
        return
    json_res = json.loads(res.text)
    user_data = json_res[0]["result"]["data"]["viewer"]
    return user_data

def fetchCollection():
    print(Fore.CYAN + "Fetching collection..." + Style.RESET_ALL)
    available_songs.clear()
    request_json = {"0":{"ownerId":f"{user_id}","partial":False},"1":{"userId":f"{user_id}"},"2":{"userId":f"{user_id}"}}
    encoded_json = urllib.parse.quote(json.dumps(request_json))
    url = f"https://api2.soundmap.dev/trpc/songs2,user2,userLeagueLeaderboardRank?batch=1&input={encoded_json}"
    res = scraper.get(url, headers=headers)
    if res.status_code != 200:
        print("Error: Failed to fetch collection. " + str(res.status_code))
        with open("error.log", "a") as f:
            f.write(f"Error: Failed to fetch collection.\n")
            f.write(f"Response: {res.text}\n")
        return
    json_res = json.loads(res.text)
    i = 0
    for song in json_res[0]["result"]["data"]["songs"]:
        # Ensure the song is not in listed_songs before adding to available_songs
        if song["songId"] not in [listed_song["id"] for listed_song in listed_songs] and song["rarity"] == "common":
            available_songs.append(song)
            i += 1
            if i >= 8 * max_trades:
                break
    print(Fore.GREEN + f"Collection fetched successfully, added {i} songs." + Style.RESET_ALL)

def createOffer():
    global available_songs, listed_songs, curr_trades, active_offers
    if curr_trades >= max_trades:
        print(Fore.YELLOW + "Max trades reached. Waiting for next cycle." + Style.RESET_ALL)
        return
    
    if not available_songs:
        print(Fore.YELLOW + "Not enough songs to create offer. Waiting for next cycle." + Style.RESET_ALL)
        return
    print(Fore.CYAN + "Creating offer..." + Style.RESET_ALL)
    offer_id = str(uuid.uuid4())
    songs_to_offer = []
    songs_to_remove = []

    # Collect up to 8 songs for the offer
    for i, song in enumerate(available_songs):
        if i >= 8:
            break
        # Check if the song is already listed in an active offer
        if any(listed_song["id"] == song["id"] for listed_song in listed_songs):
            print(Fore.YELLOW + f"Song {song['name']} is already listed in an active offer. Skipping." + Style.RESET_ALL)
            continue
        songs_to_offer.append(song["id"])
        print(Fore.GREEN + f"Adding {song['name']} by {song['artist']} to offer" + Style.RESET_ALL)
        songs_to_remove.append(song)

    if not songs_to_offer:
        print(Fore.YELLOW + "No valid songs to create an offer. Waiting for next cycle." + Style.RESET_ALL)
        return

    # Update available_songs after iterating
    for song in songs_to_remove:
        available_songs = [s for s in available_songs if s != song]
        
    trade_offer = {
        "0": {
            "songIds": songs_to_offer,
            "coins": 0,
            "note": "100 per",
            "offerId": offer_id
        }
    }
    
    res = scraper.post("https://api2.soundmap.dev/trpc/createTradeOffer?batch=1", headers=headers, json=trade_offer)
    if res.status_code != 200:
        print("Error: Failed to create offer.")
        with open("error.log", "a") as f:
            f.write(f"Error: Failed to create offer.\n")
            f.write(f"Response: {res.text}\n")
        return
    
    print(Fore.GREEN + f"Offer created successfully. id: {offer_id}" + Style.RESET_ALL)
    
    # Add songs to listed_songs with its offer ID
    offer_songs = []
    for song in songs_to_remove:
        song_with_offer = {**song, "offer_id": str(offer_id)}
        listed_songs.append(song_with_offer)
        offer_songs.append(song_with_offer)
    
    active_offers.append({
        "offer_id": str(offer_id),
        "timestamp": time.time(),
        "songs": offer_songs
    })
    curr_trades += 1

    

def deleteOffer(id):
    print(f"Deleting offer {id}...")
    json_rec = {
        "0": {
            "offerId": id
        }
    }
    try:
        res = scraper.post("https://api2.soundmap.dev/trpc/deleteTradeOffer?batch=1", headers=headers, json=json_rec)
        if res.status_code == 200:
            print(f"Offer {id} deleted successfully.")
        else:
            print(f"Failed to delete offer {id}. Status code: {res.status_code}")
            print(f"Response: {res.text}")
    except Exception as e:
        print(f"Error deleting offer {id}: {str(e)}")

def checkOffers():
    global active_offers, listed_songs, curr_trades, available_songs
    print("Checking open offers...")
    current_time = time.time()
    expired_offers = []
    
    # Identify expired offers
    for offer in active_offers[:]:
        if current_time - offer["timestamp"] >= 300:  # 5 minutes (300 seconds) expiration
            print(f"Offer {offer['offer_id']} has expired. Created at {offer['timestamp']}, current time: {current_time}")
            expired_offers.append(offer["offer_id"])
            active_offers.remove(offer)
            curr_trades -= 1  # Decrease current trades count
            send_discord_webhook(f"Offer {offer['offer_id']} has expired.")

    # Process expired offers
    for expired_offer_id in expired_offers:
        # Delete the offer from the server
        deleteOffer(expired_offer_id)
        
        # Update listed_songs and available_songs
        for song in listed_songs[:]:
            if song["offer_id"] == expired_offer_id:
                listed_songs.remove(song)
                available_songs.append(song)  # Return song to available_songs

    print(f"Removed {len(expired_offers)} expired offers.")
    print(f"Current active offers: {len(active_offers)}")
    print(f"Current listed songs: {len(listed_songs)}")
    print(f"Current available songs: {len(available_songs)}")

def get_songs_from_offer(offer_id):
    for offer in active_offers:
        if offer["offer_id"] == offer_id:
            return offer["songs"]
    return []

def acceptTrade(trade_request_id):
    global curr_trades, listed_songs, active_offers, available_songs
    print(f"Accepting trade request: {trade_request_id}")
    
    payload = {
        "0": {
            "tradeRequestId": trade_request_id
        }
    }
    
    res = scraper.post("https://api2.soundmap.dev/trpc/acceptTradeRequest?batch=1", headers=headers, json=payload)
    if res.status_code != 200:
        print("Error: Failed to accept trade.")
        with open("error.log", "a") as f:
            f.write(f"Error: Failed to accept trade.\n")
            f.write(f"Response: {res.text}\n")
        return
    
    print("Trade accepted successfully.")
    send_discord_webhook(f"Trade accepted: {trade_request_id}")  # Add this line
    curr_trades -= 1

    # We don't know the offer_id here, so we need to update our data structures after accepting the trade
    fetchCollection()  # Refresh our available songs
    updateActiveOffers()  # New function to update active offers

def updateActiveOffers():
    global active_offers, listed_songs, curr_trades
    print("Updating active offers...")
    url = "https://api2.soundmap.dev/trpc/openTradeOffers,openTradeRequests?batch=1&input=%7B%7D"
    res = scraper.get(url, headers=headers)
    if res.status_code != 200:
        print(f"Error: Failed to fetch active offers. Status code: {res.status_code}")
        print(f"Response: {res.text}")
        return

    try:
        json_res = json.loads(res.text)
        new_active_offers = []
        new_listed_songs = []

        # Create a dictionary of existing offers for quick lookup
        existing_offers = {offer['offer_id']: offer for offer in active_offers}

        if json_res and len(json_res) > 0 and 'result' in json_res[0] and 'data' in json_res[0]['result']:
            offers_data = json_res[0]['result']['data']
            
            for offer_data in offers_data:
                trade_offer = offer_data['tradeOffer']
                offer_id = trade_offer['id']
                offer_songs = []
                
                for song in offer_data['songs']:
                    song_with_offer = {**song, "offer_id": offer_id}
                    offer_songs.append(song_with_offer)
                    new_listed_songs.append(song_with_offer)
                
                # If the offer already exists, keep its original timestamp
                if offer_id in existing_offers:
                    new_active_offers.append({
                        "offer_id": offer_id,
                        "timestamp": existing_offers[offer_id]["timestamp"],
                        "songs": offer_songs,
                        "coins": trade_offer['coins'],
                        "note": trade_offer['note']
                    })
                else:
                    # If it's a new offer, use the current time as timestamp
                    new_active_offers.append({
                        "offer_id": offer_id,
                        "timestamp": time.time(),
                        "songs": offer_songs,
                        "coins": trade_offer['coins'],
                        "note": trade_offer['note']
                    })

        active_offers = new_active_offers
        listed_songs = new_listed_songs
        curr_trades = len(active_offers)
        print(f"Updated active offers: {len(active_offers)}")
        print(f"Updated listed songs: {len(listed_songs)}")
        print(f"Updated curr_trades: {curr_trades}")
    except Exception as e:
        print(f"Error parsing active offers: {str(e)}")
        print(f"Response: {res.text}")

def checkTrades():
    print("Checking trades...")
    response = scraper.get("https://api2.soundmap.dev/trpc/notifs,userLeagueLeaderboardRank?batch=1&input=%7B%7D", headers=headers)
    if response.status_code != 200:
        print("Error: Failed to check trades.")
        with open("error.log", "a") as f:
            f.write(f"Error: Failed to check trades.\n")
            f.write(f"Response: {response.text}\n")
        return

    json_res = json.loads(response.text)
    
    for result in json_res:
        if 'result' in result and 'data' in result["result"]:
            notifs = result["result"]["data"].get("notifs", [])
            for notif in notifs:
                if notif.get("type") == "trade_request":
                    request = notif.get("request", {})
                    if request.get("accepted") is False:
                        print("Trade request found.")
                        
                        # Extract the requested songs
                        requested_songs = notif.get("offeredSongs", [])
                        if requested_songs:
                            song_count = len(requested_songs)
                            print(f"Number of requested songs: {song_count}")
                            if song_count > 0:
                                requested_song_id = requested_songs[0].get("id")
                                print(f"First requested song ID: {requested_song_id}")
                            
                            # Search for matching song in listed_songs
                            matching_song = next((song for song in listed_songs if song["id"] == requested_song_id), None)
                            
                            if matching_song:
                                print(f"Matching offer ID found: {matching_song['offer_id']}")
                                # Example: Accept or reject based on coins (100 as threshold)
                                if request.get("coins") >= 100 * song_count:
                                    acceptTrade(request.get("id"))  # Use the trade request ID
                                else:
                                    rejectTrade(request.get("id"))
                            else:
                                print("No matching offer found for the requested song.")
                                print("Current listed_songs:")
                                for song in listed_songs:
                                    print(f"ID: {song['id']}, Name: {song['name']}")
                                rejectTrade(request.get("id"))
                        else:
                            print("No requested songs found in the trade request.")
                            rejectTrade(request.get("id"))

def rejectTrade(trade_id):
    print("Rejecting trade...")
    payload = {
        "0": {
            "tradeRequestId": trade_id
        }
    }
    
    res = scraper.post("https://api2.soundmap.dev/trpc/rejectTradeRequest?batch=1", headers=headers, json=payload)
    if res.status_code != 200:
        print("Error: Failed to reject trade.")
        with open("error.log", "a") as f:
            f.write(f"Error: Failed to reject trade.\n")
            f.write(f"Response: {res.text}\n")
        return
    print("Trade rejected successfully.")
    send_discord_webhook(f"Trade rejected: {trade_id}")  # Add this line
        

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_ui(user_info, logs, loading_bar=None):
    clear_screen()
    terminal_width = os.get_terminal_size().columns
    left_width = min(40, terminal_width // 2)
    right_width = terminal_width - left_width - 3

    print(f"{'SoundMap Trading Bot':^{terminal_width}}")
    print('=' * terminal_width)
    print(f"{'User Info':<{left_width}}|{'Logs':^{right_width}}")
    print('-' * terminal_width)

    user_info_lines = [
        f"Username: {user_info['username']}",
        f"User ID: {user_info['id'][:8]}...",
        f"Coins: {user_info['coins']}",
        f"Trades Completed: {user_info['tradesCompleted']}",
        f"Available Songs: {len(available_songs)}",
        f"Listed Songs: {len(listed_songs)}",
        f"Public Offers: {curr_trades}/{max_trades}",
    ]

    log_lines = logs[-10:]  # Show last 10 log entries
    max_lines = max(len(user_info_lines), len(log_lines), 10)

    for i in range(max_lines):
        left_content = user_info_lines[i] if i < len(user_info_lines) else ""
        right_content = log_lines[i] if i < len(log_lines) else ""
        print(f"{left_content:<{left_width}}|{right_content:<{right_width}}")

    if loading_bar:
        print('=' * terminal_width)
        print(loading_bar)

    print('=' * terminal_width)

# ... (rest of the code remains the same)

# Update the main loop
logs = []

print("Fetching user info...")
user_info = updateUserInfo()
username = user_info["username"]
user_id = user_info["id"]
bio = user_info["bio"]
coins = user_info["coins"]
trades_completed = user_info["tradesCompleted"]
if not user_info["premium"]:
    max_trades = 3
    logs.append("User is not premium. Max trades set to 3.")

send_discord_webhook(f"Bot started for user: {username}")  # Add this line

print_ui(user_info, logs)
input("Press Enter to continue.")

while True:
    user_info = updateUserInfo()
    fetchCollection()
    logs.append("Collection fetched.")
    print_ui(user_info, logs)
    time.sleep(2)

    updateActiveOffers()
    logs.append("Active offers updated.")
    print_ui(user_info, logs)
    time.sleep(2)

    checkOffers()
    logs.append("Offers checked.")
    print_ui(user_info, logs)
    time.sleep(2)

    checkTrades()
    logs.append("Trades checked.")
    print_ui(user_info, logs)
    time.sleep(2)

    if curr_trades < max_trades:
        createOffer()
        logs.append("Offer created.")
    else:
        logs.append("Max trades reached. Skipping offer creation.")

    print_ui(user_info, logs)

    for i in range(70):
        loading_bar = f"Next cycle in... [{'=' * i}{' ' * (49-i)}] {i*2}%"
        print_ui(user_info, logs, loading_bar)
        time.sleep(0.1)

    # Trim logs to keep only the last 50 entries
    logs = logs[-50:]
