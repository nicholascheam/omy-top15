import io
import zipfile
from openpyxl import Workbook
from collections import defaultdict
from core.models import Ballot, Comment, Player
from core.models import Player, Ballot, VotingCycle
from core.osu import fetch_user_pp

def refresh_final_pp(cycle):
    # Get all unique players who received at least one vote in this cycle
    voted_player_ids = Ballot.objects.filter(cycle=cycle).values_list("entries__player_id", flat=True).distinct()
    players = Player.objects.filter(id__in=voted_player_ids)
    
    updated_count = 0
    for player in players:
        final_pp = fetch_user_pp(player.osu_user_id)
        if final_pp is not None:
            player.current_pp = int(final_pp)
            player.save()
            updated_count += 1
            
    return updated_count

def reflag_below_threshold(cycle):
    ballots = Ballot.objects.filter(cycle=cycle)
    flagged_count = 0
    
    for ballot in ballots:
        # Get the players in this ballot who are below 8880pp
        low_pp_entries = ballot.entries.filter(player__current_pp__lt=8880)
        
        if low_pp_entries.exists():
            low_pp_names = [e.player.username for e in low_pp_entries]
            flag_text = f"Below 8880pp at close: {', '.join(low_pp_names)}"
            
            # Append to existing flags (or create new)
            if ballot.flag_reason:
                if flag_text not in ballot.flag_reason: # Prevent duplicate flags if run twice
                    ballot.flag_reason += f" | {flag_text}"
            else:
                ballot.flag_reason = flag_text
                
            ballot.save()
            flagged_count += 1
            
    return flagged_count

def generate_export_zip(cycle):
    """Generates the complete zip file with Excel and text files."""
    
    # 1. Fetch all NON-VOIDED ballots for this cycle
    ballots = Ballot.objects.filter(cycle=cycle, is_voided=False).select_related("user").prefetch_related("entries__player")
    total_ballots = Ballot.objects.filter(cycle=cycle).count()
    voided_ballots = total_ballots - ballots.count()

    wb = Workbook()
    # Remove the default sheet
    wb.remove(wb.active)

    ws_summary = wb.create_sheet("Summary")
    ws_summary.append(["Cycle Name", cycle.name])
    ws_summary.append(["Start Time", cycle.start_time.strftime("%Y-%m-%d %H:%M")])
    ws_summary.append(["End Time", cycle.end_time.strftime("%Y-%m-%d %H:%M")])
    ws_summary.append(["Total Ballots", total_ballots])
    ws_summary.append(["Valid Ballots", ballots.count()])
    ws_summary.append(["Voided Ballots", voided_ballots])
    ws_summary.append(["Final PP Threshold", 8880])
    ws_summary.append(["Player Pool Size", Player.objects.filter(is_active=True).count()])

    # Aggregate points and rank counts
    player_stats = defaultdict(lambda: {"points": 0, "times_ranked": 0, "ranks": [0]*16})
    
    for ballot in ballots:
        for entry in ballot.entries.all():
            pid = entry.player.id
            player_stats[pid]["points"] += entry.points
            player_stats[pid]["times_ranked"] += 1
            player_stats[pid]["ranks"][entry.rank_position] += 1
            player_stats[pid]["player_obj"] = entry.player # Store object for easy access

    # Sort by total points descending
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]["points"], reverse=True)

    ws_rankings = wb.create_sheet("Final Rankings")
    headers = ["Rank", "Player", "Total Points", "Times Ranked"] + [f"#{i} votes" for i in range(1, 16)]
    ws_rankings.append(headers)
    
    for rank, (pid, stats) in enumerate(sorted_players, 1):
        row = [rank, stats["player_obj"].username, stats["points"], stats["times_ranked"]]
        # Add counts for Rank 1 through 15
        for i in range(1, 16):
            row.append(stats["ranks"][i])
        ws_rankings.append(row)

    # Logic: Sum of points, but drop the highest and lowest points awarded to that player
    trimmed_stats = defaultdict(lambda: {"points_given": []})
    
    for ballot in ballots:
        for entry in ballot.entries.all():
            trimmed_stats[entry.player.id]["points_given"].append(entry.points)
            trimmed_stats[entry.player.id]["player_obj"] = entry.player

    trimmed_rankings = []
    for pid, data in trimmed_stats.items():
        points = sorted(data["points_given"])
        # Drop highest and lowest if they have more than 2 votes
        if len(points) > 2:
            trimmed_total = sum(points[1:-1])
        else:
            trimmed_total = sum(points)
        trimmed_rankings.append((data["player_obj"].username, trimmed_total))
        
    trimmed_rankings.sort(key=lambda x: x[1], reverse=True)

    ws_trimmed = wb.create_sheet("Trimmed Rankings")
    ws_trimmed.append(["Rank", "Player", "Trimmed Total"])
    for rank, (username, trimmed_total) in enumerate(trimmed_rankings, 1):
        ws_trimmed.append([rank, username, trimmed_total])

    ws_wide = wb.create_sheet("Ballots (Wide)")
    wide_headers = ["Voter", "Join Date", "Submitted", "Updated"] + [f"Rank {i}" for i in range(1, 16)]
    ws_wide.append(wide_headers)
    
    for ballot in ballots:
        row = [ballot.user.username, ballot.user.join_date.strftime("%Y-%m-%d"), ballot.submitted_at.strftime("%Y-%m-%d %H:%M"), ballot.updated_at.strftime("%Y-%m-%d %H:%M")]
        # Get entries sorted by rank
        entries = ballot.entries.all().order_by("rank_position")
        for entry in entries:
            row.append(entry.player.username)
        ws_wide.append(row)

    ws_long = wb.create_sheet("Ballots (Long)")
    ws_long.append(["Voter", "Rank", "Player"])
    
    for ballot in ballots:
        entries = ballot.entries.all().order_by("rank_position")
        for entry in entries:
            ws_long.append([ballot.user.username, entry.rank_position, entry.player.username])

    ws_comments = wb.create_sheet("Comments")
    ws_comments.append(["Player", "Voter", "Comment", "Created"])
    
    # Only fetch comments from NON-VOIDED ballots for this cycle
    valid_comments = Comment.objects.filter(
        cycle=cycle, 
        user__in=ballots.values_list("user", flat=True)
    ).select_related("player", "user").order_by("player__username", "-created_at")
    
    for c in valid_comments:
        ws_comments.append([c.player.username, c.user.username, c.body, c.created_at.strftime("%Y-%m-%d %H:%M")])

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        
        # 1. Save Excel file to memory
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        zip_file.writestr(f"{cycle.name}_results.xlsx", excel_buffer.getvalue())
        
        # 2. Generate .txt files for comments
        # Group comments by player
        player_comments = defaultdict(list)
        for c in valid_comments:
            player_comments[c.player.username].append(f"[{c.created_at.strftime('%Y-%m-%d %H:%M')}] {c.user.username}: {c.body}")
            
        for username, comments in player_comments.items():
            # Sanitize username for filename (remove / and \)
            safe_username = username.replace("/", "_").replace("\\", "_")
            file_content = f"Comments for {username}\n" + "="*40 + "\n\n" + "\n\n".join(comments)
            zip_file.writestr(f"comments/{safe_username}.txt", file_content)

    return zip_buffer.getvalue()