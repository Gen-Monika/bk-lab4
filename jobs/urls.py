from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/businesses/", views.businesses, name="businesses"),
    path("api/hosts/", views.hosts, name="hosts"),
    path("api/plans/", views.plans, name="plans"),
    path("api/plans/<int:job_plan_id>/", views.plan_detail, name="plan_detail"),
    path("api/execute-plan/", views.execute_plan, name="execute_plan"),
    path("api/search-files/", views.search_files, name="search_files"),
    path("api/backup-files/", views.backup_files, name="backup_files"),
    path("api/records/", views.records, name="records"),
    path("api/records/<int:record_id>/refresh/", views.refresh_record, name="refresh_record"),
]

