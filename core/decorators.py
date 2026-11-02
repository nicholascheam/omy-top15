from functools import wraps
from django.shortcuts import redirect
from core.models import OsuUser

def osu_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user_id = request.session.get("osu_user_id")
        
        if not user_id:
            return redirect("login")
            
        try:
            request.osu_user = OsuUser.objects.get(id=user_id)
        except OsuUser.DoesNotExist:
            request.session.flush()
            return redirect("login")
            
        return view_func(request, *args, **kwargs)
        
    return _wrapped_view