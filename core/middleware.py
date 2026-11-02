from datetime import datetime
from django.utils import timezone
from core.models import OsuUser

class Pre2026GateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Default to False if not logged in
        request.voter_eligible = False
        
        user_id = request.session.get("osu_user_id")
        if user_id:
            try:
                user = OsuUser.objects.get(id=user_id)
                
                # Create a timezone-aware datetime for Jan 1, 2026
                cutoff_date = timezone.make_aware(datetime(2026, 1, 1))
                
                # If their join date is BEFORE the cutoff, they can vote
                if user.join_date < cutoff_date:
                    request.voter_eligible = True
                    
            except OsuUser.DoesNotExist:
                pass
                
        response = self.get_response(request)
        return response