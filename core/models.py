from django.db import models
from django.core.validators import MaxLengthValidator

class OsuUser(models.Model):
    osu_user_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=64)
    avatar_url = models.URLField(max_length=255)
    country_code = models.CharField(max_length=2)
    join_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

class VotingCycle(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
    ]

    name = models.CharField(max_length=64, unique=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Player(models.Model):
    osu_user_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=64)
    avatar_url = models.URLField(max_length=255)
    country_code = models.CharField(max_length=2, default="MY")
    current_pp = models.IntegerField()
    is_active = models.BooleanField(default=True)
    last_refreshed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.current_pp}pp)"

class Ballot(models.Model):
    user = models.ForeignKey(OsuUser, on_delete=models.CASCADE)
    cycle = models.ForeignKey(VotingCycle, on_delete=models.CASCADE)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fields for the Admin Review / Veto phase (Phase H)
    flag_reason = models.TextField(blank=True, default="")
    is_voided = models.BooleanField(default=False)
    void_reason = models.TextField(blank=True, default="")
    voided_by = models.ForeignKey(
        OsuUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="+"
    )
    voided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # This ensures one ballot per user per cycle at the database level
        constraints = [
            models.UniqueConstraint(
                fields=["user", "cycle"], 
                name="unique_ballot_per_user_cycle"
            )
        ]

    def __str__(self):
        return f"Ballot by {self.user.username} for {self.cycle.name}"

class BallotEntry(models.Model):
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE, related_name="entries")
    player = models.ForeignKey(Player, on_delete=models.PROTECT)
    rank_position = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            # 1. A rank (1-15) can only appear once per ballot
            models.UniqueConstraint(
                fields=["ballot", "rank_position"], 
                name="unique_rank_per_ballot"
            ),
            # 2. A player can only be picked once per ballot
            models.UniqueConstraint(
                fields=["ballot", "player"], 
                name="unique_player_per_ballot"
            ),
            # 3. Rank must be between 1 and 15
            models.CheckConstraint(
                check=models.Q(rank_position__gte=1) & models.Q(rank_position__lte=15),
                name="rank_between_1_and_15"
            ),
            # 4. Points must be between 1 and 15
            models.CheckConstraint(
                check=models.Q(points__gte=1) & models.Q(points__lte=15),
                name="points_between_1_and_15"
            ),
        ]

    def __str__(self):
        return f"Rank {self.rank_position}: {self.player.username} on Ballot {self.ballot.id}"

class Comment(models.Model):
    user = models.ForeignKey(OsuUser, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    cycle = models.ForeignKey(VotingCycle, on_delete=models.CASCADE)
    
    # max_length=500 is enforced by Django's validation (full_clean) and forms
    body = models.TextField(
        max_length=500,
        validators=[MaxLengthValidator(500)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "player", "cycle"], 
                name="unique_comment_per_user_player_cycle"
            )
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.player.username} ({self.cycle.name})"

class ShareLink(models.Model):
    ballot = models.OneToOneField(Ballot, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ShareLink for Ballot {self.ballot.id} (revoked: {self.revoked})"

class BallotAudit(models.Model):
    ACTION_CHOICES = [
        ("create", "Create"),
        ("edit", "Edit"),
        ("void", "Void"),
        ("unvoid", "Unvoid"),
    ]
    
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        OsuUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"{self.action.upper()} on Ballot {self.ballot.id} by {actor_name}"

class BannedUser(models.Model):
    osu_user_id = models.BigIntegerField(unique=True)
    banned_by = models.ForeignKey(OsuUser, on_delete=models.SET_NULL, null=True, blank=True)
    banned_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Banned osu_user_id: {self.osu_user_id}"