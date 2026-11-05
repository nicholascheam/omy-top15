import random
import string
from django.utils import timezone
import datetime
from core.models import OsuUser, VotingCycle, Player, Ballot, BallotEntry, Comment

# ==========================================
# SETUP
# ==========================================
cycle = VotingCycle.objects.filter(status="active").first()
if not cycle:
    cycle = VotingCycle.objects.first()

# Ensure we have at least 30 players to vote for
players = list(Player.objects.filter(is_active=True)[:30])
if len(players) < 15:
    print("❌ ERROR: You need at least 15 active players in the database.")
    exit()

# Ensure the cycle is accepting votes
cycle.end_time = timezone.now() + datetime.timedelta(days=1)
cycle.save()

def random_string(length=50):
    """Generates a random string for comments."""
    return ''.join(random.choices(string.ascii_letters + ' ', k=length))

print(f"Starting simulation for cycle: {cycle.name}")
print("Generating 20 random voters...")

# ==========================================
# GENERATE VOTERS
# ==========================================
for i in range(1, 21):
    # 1. Create the voter (random join date in 2024 or 2025)
    join_year = random.choice([2024, 2025])
    join_date = timezone.make_aware(datetime.datetime(join_year, random.randint(1, 12), random.randint(1, 28)))
    
    user, _ = OsuUser.objects.get_or_create(
        osu_user_id=100000 + i,
        defaults={
            "username": f"voter_{i}",
            "avatar_url": "https://a.ppy.sh/1",
            "country_code": "MY",
            "join_date": join_date
        }
    )

    # Clean up any old ballots for this test user so we can re-run the script
    Ballot.objects.filter(user=user, cycle=cycle).delete()

    # 2. Create the Ballot
    ballot = Ballot.objects.create(user=user, cycle=cycle)
    
    # Randomly flag some ballots to test the review queue
    if random.random() < 0.2: # 20% chance of being flagged
        ballot.flag_reason = "Simulated flag: rapid submit"
        ballot.save()

    # 3. Pick 15 random players and create entries
    selected_players = random.sample(players, 15)
    entries = []
    for rank, player in enumerate(selected_players, 1):
        entries.append(BallotEntry(
            ballot=ballot,
            player=player,
            rank_position=rank,
            points=16 - rank
        ))
        # 4. Randomly add comments (30% chance per player)
        if random.random() < 0.3:
            Comment.objects.create(
                user=user,
                player=player,
                cycle=cycle,
                body=f"Simulated comment: {random_string(random.randint(20, 100))}"
            )
            
    BallotEntry.objects.bulk_create(entries)

print("✅ Simulation complete! 20 ballots generated.")
print("Now go to /admin/review and download the Export Zip to test the Excel generation.")