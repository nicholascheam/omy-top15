from django.utils import timezone
from datetime import timedelta
from core.models import Player

def check_ballot_flags(request, entries_data, comments_data, cycle):
    """Returns a string of flag reasons, or an empty string if the ballot is clean."""
    flags = []
    user = request.osu_user
    now = timezone.now()

    # 1. Inactive Player
    player_ids = [e["player_id"] for e in entries_data]
    inactive_players = Player.objects.filter(id__in=player_ids, is_active=False)
    for p in inactive_players:
        flags.append(f"Contains inactive player: {p.username}")

    # 2. Rapid Submit
    login_time = request.session.get("login_time")
    if login_time:
        # If they submitted within 60 seconds of logging in
        if (now.timestamp() - login_time) < 60:
            # AND they didn't write any comments
            if not comments_data or all(not str(v).strip() for v in comments_data.values()):
                flags.append("Rapid submit: < 60s from login with no comments")

    # 3. New Account
    cutoff_2026 = timezone.make_aware(timezone.datetime(2026, 1, 1))
    thirty_days_ago = now - timedelta(days=30)
    if user.join_date > thirty_days_ago and user.join_date < cutoff_2026:
        flags.append("Voter is a very new osu! account (created < 30 days ago)")

    # 4. Outlier PP
    # Check the current_pp of the players they voted for
    low_pp_players = Player.objects.filter(id__in=player_ids, current_pp__lt=7000)
    for p in low_pp_players:
        flags.append(f"Contains unusually low-pp player: {p.username} ({p.current_pp}pp)")

    return " | ".join(flags)