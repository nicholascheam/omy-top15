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

def _get_app_token():
    """Fetches a client-credentials token to access public API endpoints."""
    payload = {
        "client_id": OSU_CLIENT_ID,
        "client_secret": OSU_CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "public",
    }
    response = requests.post(OSU_TOKEN, data=payload)
    response.raise_for_status()
    return response.json().get("access_token")

def fetch_rankings(country="MY", page=1):
    """Fetches a page of the performance rankings for a specific country."""
    token = _get_app_token()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    
    url = "https://osu.ppy.sh/api/v2/rankings/osu/performance"
    params = {
        "country": country,
        "page": page,
        "per_page": 50,
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    # We only want the 'ranking' array from the response
    return response.json().get("ranking", [])

def fetch_user_pp(osu_user_id):
    """Fetches the current pp for a specific user from the osu! API."""
    token = _get_app_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    url = f"https://osu.ppy.sh/api/v2/users/{osu_user_id}/osu"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("statistics", {}).get("pp", 0.0)
    return None