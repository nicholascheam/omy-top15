import os
import requests

OSU_CLIENT_ID = os.environ.get("OSU_CLIENT_ID")
OSU_CLIENT_SECRET = os.environ.get("OSU_CLIENT_SECRET")
OSU_REDIRECT_URI = os.environ.get("OSU_REDIRECT_URI")

OSU_AUTHORIZE = "https://osu.ppy.sh/oauth/authorize"
OSU_TOKEN = "https://osu.ppy.sh/oauth/token"
OSU_ME = "https://osu.ppy.sh/api/v2/me"

def _fetch_me(access_token):
    """Fetches the current user's profile from the osu! API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    response = requests.get(OSU_ME, headers=headers)
    response.raise_for_status() # Throws an error if the request fails
    return response.json()