import requests
from dotenv import load_dotenv
import os

load_dotenv()


def geocode_google(address, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
    
    return None, None


# Get an API key from Google Cloud Console
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API")
lat, lon = geocode_google("921 CENTRAL AVE San Francisco CA", GOOGLE_API_KEY)
print(lat, lon)