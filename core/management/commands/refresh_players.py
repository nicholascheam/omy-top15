from django.core.management.base import BaseCommand
from core.models import Player
from core.osu import fetch_rankings

class Command(BaseCommand):
    help = "Fetches Malaysian players from osu! API and updates the database."

    def handle(self, *args, **options):
        self.stdout.write("Fetching Malaysian rankings from osu!...")
        
        page = 1
        inserted = 0
        updated = 0
        stop_fetching = False
        
        # Keep track of everyone we find in this API run
        fetched_osu_ids = set()

        while not stop_fetching:
            self.stdout.write(f"Fetching page {page}...")
            rankings = fetch_rankings(country="MY", page=page)

            if not rankings:
                break

            for entry in rankings:
                pp = entry["pp"]
                
                # Contract: Stop fetching once pp < 8880
                if pp < 8880:
                    stop_fetching = True
                    break

                user_data = entry["user"]
                fetched_osu_ids.add(user_data["id"])
                
                player, created = Player.objects.update_or_create(
                    osu_user_id=user_data["id"],
                    defaults={
                        "username": user_data["username"],
                        "avatar_url": user_data["avatar_url"],
                        "country_code": user_data["country_code"],
                        "current_pp": int(pp), 
                        "is_active": True, # Reactivate them if they returned!
                    }
                )
                
                if created:
                    inserted += 1
                else:
                    updated += 1

            page += 1

        # Find all active players in the DB who were NOT in the API response
        dropped_players = Player.objects.filter(is_active=True).exclude(osu_user_id__in=fetched_osu_ids)
        dropped_count = dropped_players.count()
        
        if dropped_count > 0:
            dropped_players.update(is_active=False)
            self.stdout.write(self.style.WARNING(f"Deactivated {dropped_count} players who fell below 8880pp or left the rankings."))

        self.stdout.write(self.style.SUCCESS(
            f"Finished! Inserted: {inserted}, Updated: {updated}, Deactivated: {dropped_count}."
        ))