from django.contrib import admin
from .models import (
    OsuUser, VotingCycle, Player, Ballot, 
    BallotEntry, Comment, ShareLink, BallotAudit
)

admin.site.register(OsuUser)
admin.site.register(VotingCycle)
admin.site.register(Player)
admin.site.register(Ballot)
admin.site.register(BallotEntry)
admin.site.register(Comment)
admin.site.register(ShareLink)
admin.site.register(BallotAudit)