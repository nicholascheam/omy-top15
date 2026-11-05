from django.contrib import admin
from django.urls import include, path
from core import views as core_views

urlpatterns = [
    # Custom Admin Routes (MUST be before the default admin route)
    path("admin/review", core_views.review_list, name="review_list"),
    path("admin/review/<int:ballot_id>", core_views.review_detail, name="review_detail"),
    
    # Default Django Admin
    path("admin/", admin.site.urls),
    
    # Core App Routes
    path("", include("core.urls")),
]