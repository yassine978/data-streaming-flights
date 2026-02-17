# test_api.py — Run this to verify your OpenSky credentials work
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID")
CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET")

# STEP 1: Get an OAuth2 access token
token_url = (
    "https://auth.opensky-network.org/auth/realms/"
    "opensky-network/protocol/openid-connect/token"
)

token_response = requests.post(
    token_url,
    data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
)

if token_response.status_code != 200:
    print(f"Error: Failed to get token: {token_response.status_code}")
    print(token_response.text)
    exit(1)

token = token_response.json()["access_token"]
print("Good Token obtained successfully")

# STEP 2: Call the API - get flights over Europe

api_url = "https://opensky-network.org/api/states/all"

params = {
    "lamin": 35.0,   # min latitude  (south border of Europe)
    "lamax": 72.0,   # max latitude  (north border of Europe)
    "lomin": -10.0,  # min longitude (west border of Europe)
    "lomax": 40.0,   # max longitude (east border of Europe)
}

headers = {"Authorization": f"Bearer {token}"}

api_response = requests.get(api_url, params=params, headers=headers)

if api_response.status_code != 200:
    print(f"Error: API call failed: {api_response.status_code}")
    print(api_response.text)
    exit(1)

data = api_response.json()

# STEP 3: Show results

states = data.get("states", [])
print(f"\nGood API working! Received {len(states)} flights over Europe\n")

# Show first 3 flights
print("Sample flights:")
for state in states[:3]:
    print(json.dumps({
        "icao24":         state[0],
        "callsign":       state[1],
        "origin_country": state[2],
        "longitude":      state[5],
        "latitude":       state[6],
        "altitude_m":     state[7],
        "on_ground":      state[8],
        "velocity_ms":    state[9],
        "heading":        state[10],
    }, indent=2))