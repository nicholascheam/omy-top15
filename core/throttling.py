import time
from functools import wraps
from django.http import JsonResponse

# In-memory dictionary to store rate limits: {user_id: [timestamp1, timestamp2, ...]}
_rate_limit_data = {}

def rate_limit(bucket_name, max_requests, window_seconds):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Only rate limit POST requests
            if request.method != "POST":
                return view_func(request, *args, **kwargs)

            if not hasattr(request, "osu_user") or not request.osu_user:
                return view_func(request, *args, **kwargs) # Let the login decorator handle it

            user_id = request.osu_user.id
            bucket_key = f"{bucket_name}_{user_id}"
            now = time.time()

            # Get existing timestamps for this user and bucket
            timestamps = _rate_limit_data.get(bucket_key, [])

            # Filter out timestamps older than our window (e.g., 1 hour ago)
            timestamps = [t for t in timestamps if now - t < window_seconds]

            # Check if they hit the limit
            if len(timestamps) >= max_requests:
                return JsonResponse(
                    {"error": f"Rate limit exceeded. You can only perform this action {max_requests} times per hour."},
                    status=429
                )

            # Add current timestamp and save back to memory
            timestamps.append(now)
            _rate_limit_data[bucket_key] = timestamps

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator