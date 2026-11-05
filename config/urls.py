from django.contrib import admin
from django.urls import include, path
from core import views as core_views

urlpatterns = [
    # Custom Admin Routes (MUST be before the default admin route)
    path("admin/review", core_views.review_list, name="review_list"),
    path("admin/review/<int:ballot_id>", core_views.review_detail, name="review_detail"),
    path("admin/review/<int:ballot_id>/void", core_views.review_void, name="review_void"),
    path("admin/review/<int:ballot_id>/unvoid", core_views.review_unvoid, name="review_unvoid"),
    path("admin/review/bulk-void", core_views.review_bulk_void, name="review_bulk_void"),
    path("admin/export", core_views.export_results, name="export_results"),

    # Default Django Admin
    path("admin/", admin.site.urls),
    
    # Core App Routes
    path("", include("core.urls")),
]