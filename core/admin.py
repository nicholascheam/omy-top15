from django.contrib import admin
from django.core.management import call_command
from django.contrib import messages
from .models import (
    OsuUser, VotingCycle, Player, Ballot, 
    BallotEntry, Comment, ShareLink, BallotAudit
)

# Register the simple models normally
admin.site.register(OsuUser)
admin.site.register(VotingCycle)
admin.site.register(Ballot)
admin.site.register(BallotEntry)
admin.site.register(Comment)
admin.site.register(ShareLink)
admin.site.register(BallotAudit)

# Custom Admin for Player
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('username', 'osu_user_id', 'current_pp', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('username', 'osu_user_id')

    @admin.action(description="🔄 Refresh player pool from osu! API")
    def refresh_player_pool(self, request, queryset):
        try:
            call_command("refresh_players")
            self.message_user(request, "Successfully refreshed players from osu! API.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error refreshing players: {e}", messages.ERROR)

    actions = ['refresh_player_pool']