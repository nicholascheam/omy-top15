import logging
import requests
import urllib.parse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from core.models import OsuUser
from core.decorators import osu_login_required
from core.osu import (
    OSU_CLIENT_ID, 
    OSU_CLIENT_SECRET, 
    OSU_REDIRECT_URI, 
    OSU_AUTHORIZE, 
    OSU_TOKEN,
    _fetch_me
)

logger = logging.getLogger("core")

def home(request):
    return render(request, "home.html")

def login_redirect(request):
    # Build the authorization URL
    params = {
        "client_id": OSU_CLIENT_ID,
        "redirect_uri": OSU_REDIRECT_URI,
        "response_type": "code",
        "scope": "public",
    }
    
    # URL-encode the parameters
    import urllib.parse
    url = f"{OSU_AUTHORIZE}?{urllib.parse.urlencode(params)}"
    
    return redirect(url)

def oauth_callback(request):
    # 1. Read the code from the URL query string
    code = request.GET.get("code")
    if not code:
        return HttpResponse("Error: No authorization code provided by osu!", status=400)

    # 2. Prepare the POST payload
    payload = {
        "client_id": OSU_CLIENT_ID,
        "client_secret": OSU_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": OSU_REDIRECT_URI,
    }

    # 3. Send the request to osu!
    response = requests.post(OSU_TOKEN, data=payload)
    
    if response.status_code != 200:
        # If osu! rejects the code, print the error and stop
        return HttpResponse(f"Error exchanging token: {response.text}", status=response.status_code)

    # 4. Parse the JSON response
    data = response.json()
    access_token = data.get("access_token")

    # 5. Save the token in the Django session so we can use it in Step 25
    request.session["osu_access_token"] = access_token

    # 6. Fetch the user profile from osu!
    me = _fetch_me(access_token)
    
    # 7. osu! sends join_date as an ISO string, so we must parse it for Django
    join_date = parse_datetime(me["join_date"])

    # 8. Upsert (Update or Create) the user in our database
    user, created = OsuUser.objects.update_or_create(
        osu_user_id=me["id"],
        defaults={
            "username": me["username"],
            "avatar_url": me["avatar_url"],
            "country_code": me["country_code"],
            "join_date": join_date,
        }
    )

    # 9. Store the user's database ID in the session
    request.session["osu_user_id"] = user.id
    
    # 10. Redirect to the homepage
    return redirect("home")

@require_POST
def logout_view(request):
    # This completely clears the session (logs the user out)
    request.session.flush()
    return redirect("home")

@osu_login_required
def protected_test(request):
    return HttpResponse(f"Welcome to the secret area, {request.osu_user.username}!")