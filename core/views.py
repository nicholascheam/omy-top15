import logging
import requests
import urllib.parse
import secrets
import os
import io
import zipfile
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from django.db import transaction
from core.export import reflag_below_threshold, refresh_final_pp
from core.models import BallotAudit, BannedUser, OsuUser, Ballot, Player, ShareLink, VotingCycle, BallotEntry, Comment
from core.forms import BallotForm
from core.decorators import osu_login_required
from core.throttling import rate_limit
from core.flags import check_ballot_flags
from core.export import refresh_final_pp, reflag_below_threshold, generate_export_zip
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
    active_cycle = VotingCycle.objects.filter(status="active").first()
    has_ballot = False
    is_logged_in = "osu_user_id" in request.session
    
    if active_cycle and is_logged_in:
        user_id = request.session["osu_user_id"]
        has_ballot = Ballot.objects.filter(user_id=user_id, cycle=active_cycle).exists()

    return render(request, "home.html", {
        "active_cycle": active_cycle,
        "has_ballot": has_ballot,
        "is_logged_in": is_logged_in
    })

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
    request.session["login_time"] = timezone.now().timestamp()
    
    # 10. Redirect to the homepage
    return redirect("home")

@require_POST
def logout_view(request):
    # This completely clears the session (logs the user out)
    request.session.flush()
    return redirect("home")

@osu_login_required
@rate_limit("votes", max_requests=10, window_seconds=3600)
def vote(request):
    active_cycle = VotingCycle.objects.filter(status="active").first()
    if not active_cycle:
        return HttpResponse("There is no active voting cycle right now.", status=404)

    if BannedUser.objects.filter(osu_user_id=request.osu_user.osu_user_id).exists():
        return HttpResponseForbidden("You have been banned from participating in this voting cycle.")
    
    if active_cycle.end_time <= timezone.now():
        if request.method == "POST":
            # If they try to submit data after the deadline, block it with a 403
            return HttpResponseForbidden("Voting has closed for this cycle. You can no longer submit or edit your ballot.")
        else:
            # If they just visit the page, show a closed message
            return HttpResponse("<h2>Voting is Closed</h2><p>The deadline for this cycle has passed.</p>", status=403)

    existing_ballot = Ballot.objects.filter(user=request.osu_user, cycle=active_cycle).first()
    
    # If they already voted and are just visiting /vote, redirect to my_ballot
    if existing_ballot and request.method == "GET" and not request.GET.get("edit"):
        return redirect("my_ballot")

    if request.method == "POST":
        form = BallotForm(request.POST, request=request, cycle=active_cycle)
        
        if form.is_valid():
            entries_data = form.cleaned_data["entries"]
            comments_data = form.cleaned_data.get("comments") or {}

            player_ids = [entry["player_id"] for entry in entries_data]

            if Player.objects.filter(id__in=player_ids, osu_user_id=request.osu_user.osu_user_id).exists():

                return HttpResponseForbidden("You cannot vote for yourself.")

            with transaction.atomic():
                # Run the flags
                flag_reason = check_ballot_flags(request, entries_data, comments_data, active_cycle)

                # 1. Create or get the ballot
                ballot, created = Ballot.objects.update_or_create(
                    user=request.osu_user, 
                    cycle=active_cycle, 
                    defaults={"flag_reason": flag_reason}
                )
                
                # --- NEW: Capture old entries BEFORE deleting them ---
                old_entries = []
                if not created:
                    old_entries = list(ballot.entries.values("player_id", "rank_position", "points"))
                # ------------------------------------------------------

                # 2. Delete old entries
                ballot.entries.all().delete()
                
                # 3. Bulk create the new entries
                new_entries = []
                for entry in entries_data:
                    points = 16 - int(entry["rank"])
                    new_entries.append(
                        BallotEntry(
                            ballot=ballot,
                            player_id=entry["player_id"],
                            rank_position=int(entry["rank"]),
                            points=points
                        )
                    )
                BallotEntry.objects.bulk_create(new_entries)

                # 4. Handle comments
                for p_id_str, body in comments_data.items():
                    if body.strip():
                        Comment.objects.update_or_create(
                            user=request.osu_user,
                            player_id=int(p_id_str),
                            cycle=active_cycle,
                            defaults={"body": body}
                        )

                # 5. AUDIT LOG
                snapshot = {
                    "entries": entries_data,
                    "comments": comments_data
                }
                
                if created:
                    BallotAudit.objects.create(
                        ballot=ballot,
                        action="create",
                        actor=request.osu_user,
                        snapshot=snapshot
                    )
                else:
                    # --- NEW: Audit on Edit ---
                    BallotAudit.objects.create(
                        ballot=ballot,
                        action="edit",
                        actor=request.osu_user,
                        snapshot={
                            "before": old_entries,
                            "after": snapshot
                        }
                    )

            return redirect("/my-ballot?submitted=1")
    else:
        # GET request: We pass 'is_edit' to the template
        is_edit = request.GET.get("edit") == "1" and existing_ballot is not None
        form = BallotForm(request=request, cycle=active_cycle)
        
        existing_entries = []
        existing_comments = {}
        
        if is_edit:
            # Fetch the current entries and comments
            for entry in existing_ballot.entries.select_related("player").all():
                existing_entries.append({
                    "player_id": entry.player.id,
                    "osu_user_id": entry.player.osu_user_id,
                    "rank": entry.rank_position,
                    "username": entry.player.username,
                    "pp": entry.player.current_pp,
                    "avatar_url": entry.player.avatar_url
                })
            
            comments = Comment.objects.filter(user=request.osu_user, cycle=active_cycle)
            existing_comments = {c.player_id: c.body for c in comments}

    return render(request, "vote.html", {
        "form": form, 
        "cycle": active_cycle, 
        "is_edit": is_edit if request.method == "GET" else False,
        "existing_entries": existing_entries if request.method == "GET" else [],
        "existing_comments": existing_comments if request.method == "GET" else {}
    })

@osu_login_required
def my_ballot(request):
    # 1. Find the active cycle
    active_cycle = VotingCycle.objects.filter(status="active").first()
    if not active_cycle:
        return HttpResponse("There is no active voting cycle right now.", status=404)

    # 2. Try to find this specific user's ballot
    ballot = Ballot.objects.filter(user=request.osu_user, cycle=active_cycle).first()
    
    # 3. Handle the empty state (they haven't voted yet)
    if not ballot:
        return render(request, "my_ballot.html", {"ballot": None, "cycle": active_cycle})

    # 4. Fetch the entries ordered by rank
    entries = ballot.entries.select_related("player").order_by("rank_position")
    
    # 5. Fetch this user's comments for this cycle
    comments = Comment.objects.filter(user=request.osu_user, cycle=active_cycle)
    comment_dict = {c.player_id: c.body for c in comments}

    # 6. Attach the comment to the entry object so the template can easily read it
    for entry in entries:
        entry.comment_body = comment_dict.get(entry.player_id, "")

    # 7. Check for a Share Link
    share_link = getattr(ballot, "sharelink", None)
    has_active_link = share_link is not None and not share_link.revoked

    return render(request, "my_ballot.html", {
        "ballot": ballot, 
        "entries": entries, 
        "cycle": active_cycle,
        "share_link": share_link,
        "has_active_link": has_active_link
    })

@osu_login_required
def edit_ballot(request):
    # Simply redirect to the vote view with ?edit=1
    return redirect("/vote?edit=1")

@osu_login_required
def search_players(request):
    query = request.GET.get("q", "").strip()
    
    # If the query is exactly 1 character, return empty (avoiding huge queries)
    if len(query) == 1:
        return JsonResponse({"results": []})
        
    players = Player.objects.filter(is_active=True)
    
    # If they typed 2+ characters, filter by name. Otherwise, just get the top 50.
    if len(query) >= 2:
        players = players.filter(username__icontains=query)
        
    players = players.order_by("-current_pp")[:150] 

    results = [
        {
            "id": p.id,
            "osu_user_id": p.osu_user_id,
            "username": p.username,
            "pp": p.current_pp,
            "avatar_url": p.avatar_url
        }
        for p in players
    ]
    
    return JsonResponse({"results": results})

@osu_login_required
@rate_limit("comments", max_requests=10, window_seconds=3600)
def submit_comment(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    player_id = request.POST.get("player_id")
    body = request.POST.get("body", "").strip()

    # 1. Validation
    if not player_id:
        return JsonResponse({"error": "Missing player_id"}, status=400)
    
    if len(body) > 500:
        return JsonResponse({"error": "Comment exceeds 500 characters"}, status=400)

    try:
        player = Player.objects.get(id=player_id, is_active=True)
    except Player.DoesNotExist:
        return JsonResponse({"error": "Player not found or inactive"}, status=404)

    active_cycle = VotingCycle.objects.filter(status="active").first()
    if not active_cycle:
        return JsonResponse({"error": "No active cycle"}, status=404)

    # 2. Upsert the comment
    comment, created = Comment.objects.update_or_create(
        user=request.osu_user,
        player=player,
        cycle=active_cycle,
        defaults={"body": body}
    )

    return JsonResponse({
        "status": "success", 
        "created": created,
        "comment_id": comment.id,
        "body": comment.body
    })

@osu_login_required
@rate_limit("comments", max_requests=10, window_seconds=3600)
def edit_comment(request, comment_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return JsonResponse({"error": "Comment not found"}, status=404)

    # 1. Verify ownership
    if comment.user != request.osu_user:
        return JsonResponse({"error": "You do not own this comment"}, status=403)

    # 2. Get and validate the new body
    body = request.POST.get("body", "").strip()
    if len(body) > 500:
        return JsonResponse({"error": "Comment exceeds 500 characters"}, status=400)

    # 3. Update and save
    comment.body = body
    comment.save()

    return JsonResponse({"status": "success", "comment_id": comment.id, "body": comment.body})

@osu_login_required
def delete_comment(request, comment_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return JsonResponse({"error": "Comment not found"}, status=404)

    # Verify ownership before deleting
    if comment.user != request.osu_user:
        return JsonResponse({"error": "You do not own this comment"}, status=403)

    # Delete it
    comment.delete()

    return JsonResponse({"status": "success", "message": "Comment deleted"})

@osu_login_required
def create_share(request):
    if request.method != "POST":
        return HttpResponse("POST required", status=405)

    active_cycle = VotingCycle.objects.filter(status="active").first()
    if not active_cycle:
        return HttpResponse("No active cycle", status=404)

    ballot = Ballot.objects.filter(user=request.osu_user, cycle=active_cycle).first()
    if not ballot:
        return HttpResponse("No ballot found", status=404)

    # Generate a secure random token (32 bytes = ~43 characters)
    new_token = secrets.token_urlsafe(32)

    # Upsert the share link (rotates the token if it already exists)
    share, created = ShareLink.objects.update_or_create(
        ballot=ballot,
        defaults={"token": new_token, "revoked": False}
    )

    # Redirect back to the success banner if requested
    if request.GET.get("next") == "submitted":
        return redirect("/my-ballot?submitted=1")
    
    return redirect("my_ballot")

def public_share(request, token):
    # 1. Look up the ShareLink by token. If it doesn't exist or is revoked, 404.
    try:
        share_link = ShareLink.objects.get(token=token, revoked=False)
    except ShareLink.DoesNotExist:
        return HttpResponse("404 - Share link not found or revoked", status=404)

    ballot = share_link.ballot
    cycle = ballot.cycle
    entries = ballot.entries.select_related("player").order_by("rank_position")

    # Note: We intentionally do NOT pass comments or user identity here.
    return render(request, "share_public.html", {
        "ballot": ballot,
        "entries": entries,
        "cycle": cycle
    })

@osu_login_required
def revoke_share(request):
    if request.method != "POST":
        return HttpResponse("POST required", status=405)

    active_cycle = VotingCycle.objects.filter(status="active").first()
    ballot = Ballot.objects.filter(user=request.osu_user, cycle=active_cycle).first()
    
    if ballot:
        ShareLink.objects.filter(ballot=ballot).update(revoked=True)

    return redirect("my_ballot")

@osu_login_required
def review_list(request):
    # Check if the user is an admin
    admin_ids_str = os.environ.get("ADMIN_OSU_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
    
    if request.osu_user.osu_user_id not in admin_ids:
        return HttpResponseForbidden("403 Forbidden: You are not an admin.")

    # Get all ballots that have a non-empty flag_reason
    flagged_ballots = Ballot.objects.exclude(flag_reason="").order_by("-submitted_at")
    
    # Fetch all cycles, newest first
    all_cycles = VotingCycle.objects.all().order_by('-start_time')

    return render(request, "admin_review_list.html", {
        "flagged_ballots": flagged_ballots,
        "all_cycles": all_cycles
    })

@osu_login_required
def review_detail(request, ballot_id):
    # Admin check
    admin_ids_str = os.environ.get("ADMIN_OSU_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
    if request.osu_user.osu_user_id not in admin_ids:
        return HttpResponseForbidden("403 Forbidden: You are not an admin.")

    # Fetch the ballot
    try:
        ballot = Ballot.objects.get(id=ballot_id)
    except Ballot.DoesNotExist:
        return HttpResponse("Ballot not found", status=404)

    # Fetch entries and comments
    entries = ballot.entries.select_related("player").order_by("rank_position")
    comments = Comment.objects.filter(user=ballot.user, cycle=ballot.cycle)
    comment_dict = {c.player_id: c.body for c in comments}

    for entry in entries:
        entry.comment_body = comment_dict.get(entry.player_id, "")

    return render(request, "admin_review_detail.html", {
        "ballot": ballot,
        "entries": entries
    })

@osu_login_required
def review_void(request, ballot_id):
    # Admin check
    admin_ids_str = os.environ.get("ADMIN_OSU_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
    if request.osu_user.osu_user_id not in admin_ids:
        return HttpResponseForbidden("403 Forbidden: You are not an admin.")

    if request.method != "POST":
        return HttpResponseForbidden("POST required")

    try:
        ballot = Ballot.objects.get(id=ballot_id)
    except Ballot.DoesNotExist:
        return HttpResponse("Ballot not found", status=404)

    # Get the reason from the form, default to a generic message if left blank
    reason = request.POST.get("void_reason", "").strip()
    if not reason:
        reason = "Voided by admin without specific reason."

    # Update the ballot
    ballot.is_voided = True
    ballot.void_reason = reason
    ballot.voided_by = request.osu_user
    ballot.voided_at = timezone.now()
    ballot.save()

    BallotAudit.objects.create(
        ballot=ballot,
        action="void",
        actor=request.osu_user,
        snapshot={"reason": reason}
    )
    
    if request.POST.get("ban_user") == "1":
        BannedUser.objects.get_or_create(
            osu_user_id=ballot.user.osu_user_id,
            defaults={"banned_by": request.osu_user, "reason": reason}
        )

    return redirect("review_detail", ballot_id=ballot.id)

@osu_login_required
def review_unvoid(request, ballot_id):
    # Admin check
    admin_ids_str = os.environ.get("ADMIN_OSU_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
    if request.osu_user.osu_user_id not in admin_ids:
        return HttpResponseForbidden("403 Forbidden: You are not an admin.")

    if request.method != "POST":
        return HttpResponseForbidden("POST required")

    try:
        ballot = Ballot.objects.get(id=ballot_id)
    except Ballot.DoesNotExist:
        return HttpResponse("Ballot not found", status=404)

    # Revert the ballot to a clean state
    ballot.is_voided = False
    ballot.void_reason = ""
    ballot.voided_by = None
    ballot.voided_at = None
    ballot.save()

    BallotAudit.objects.create(
        ballot=ballot,
        action="unvoid",
        actor=request.osu_user,
        snapshot={}
    )

    return redirect("review_detail", ballot_id=ballot.id)

@osu_login_required
def review_bulk_void(request):
    admin_ids_str = os.environ.get("ADMIN_OSU_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
    if request.osu_user.osu_user_id not in admin_ids:
        return HttpResponseForbidden("403 Forbidden: You are not an admin.")

    if request.method != "POST":
        return HttpResponseForbidden("POST required")

    # Get list of ballot IDs from the checkboxes
    ballot_ids = request.POST.getlist("ballot_ids")
    if ballot_ids:
        # Update all selected ballots atomically
        Ballot.objects.filter(id__in=ballot_ids).update(
            is_voided=True,
            void_reason="Bulk voided by admin.",
            voided_by=request.osu_user,
            voided_at=timezone.now()
        )

    return redirect("review_list")

@osu_login_required
def export_results(request):
    if request.method != "POST":
        return HttpResponse("POST required", status=405)

    admin_ids_str = os.environ.get("ADMIN_OSU_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
    if request.osu_user.osu_user_id not in admin_ids:
        return HttpResponseForbidden("403 Forbidden: You are not an admin.")

    cycle_id = request.POST.get("cycle_id")
    cycle = VotingCycle.objects.filter(id=cycle_id).first()
    
    if not cycle:
        return HttpResponse("Cycle not found.", status=404)
        
    # Enforce the rule
    if cycle.status != "closed":
        return HttpResponse("You must mark this cycle as 'closed' before exporting.", status=400)
    
    # 1. Refresh PP and Re-flag
    refresh_final_pp(cycle)
    reflag_below_threshold(cycle)
    
    # 2. Generate Zip
    zip_data = generate_export_zip(cycle)

    # 3. Return as download
    response = HttpResponse(zip_data, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{cycle.name}_export.zip"'
    return response