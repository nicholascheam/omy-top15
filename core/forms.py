from django import forms
from django.utils import timezone
from datetime import datetime
from core.models import Player

class BallotForm(forms.Form):
    # The frontend will send JSON. Django 5 forms have a JSONField.
    entries = forms.JSONField()
    comments = forms.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        # We pop these out so the form can use them for validation
        self.request = kwargs.pop('request', None)
        self.cycle = kwargs.pop('cycle', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        entries = cleaned_data.get('entries')
        comments = cleaned_data.get('comments', {})

        if not self.request or not self.cycle:
            raise forms.ValidationError("Form is missing request or cycle context.")

        if entries is not None:
            # Run all the contract checks
            self.validate_count(entries)
            self.validate_distinct(entries)
            self.validate_eligible(entries)
            self.validate_not_self(entries)
            self.validate_deadline()
            self.validate_join_date()
            
        if comments:
            self.validate_comment_lengths(comments)

        return cleaned_data

    def validate_count(self, entries):
        if len(entries) != 15:
            raise forms.ValidationError("You must select exactly 15 players.")

    def validate_distinct(self, entries):
        player_ids = [e.get('player_id') for e in entries]
        if len(set(player_ids)) != 15:
            raise forms.ValidationError("You cannot select the same player twice.")

    def validate_eligible(self, entries):
        player_ids = [e.get('player_id') for e in entries]
        valid_count = Player.objects.filter(id__in=player_ids, is_active=True).count()
        if valid_count != 15:
            raise forms.ValidationError("One or more selected players are not eligible (inactive or deleted).")

    def validate_not_self(self, entries):
        player_ids = [e.get('player_id') for e in entries]
        # Check if any of the selected players have the same osu_user_id as the voter
        if Player.objects.filter(id__in=player_ids, osu_user_id=self.request.osu_user.osu_user_id).exists():
            raise forms.ValidationError("You cannot vote for yourself.")

    def validate_deadline(self):
        if self.cycle.end_time <= timezone.now():
            raise forms.ValidationError("Voting has closed for this cycle.")

    def validate_join_date(self):
        cutoff = timezone.make_aware(datetime(2026, 1, 1))
        if self.request.osu_user.join_date >= cutoff:
            raise forms.ValidationError("Your osu! account was created too recently to vote.")

    def validate_comment_lengths(self, comments):
        for p_id, body in comments.items():
            if len(body) > 500:
                raise forms.ValidationError(f"Comment for player {p_id} exceeds 500 characters.")