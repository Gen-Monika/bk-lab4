import os

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import ApiRequestCount, UserBehaviorEvent


def dashboard(request):
    embed_url = os.getenv("BKVISION_DASHBOARD_URL", "")
    if embed_url.startswith("http://"):
        embed_url = "https://" + embed_url[len("http://"):]
    return render(request, "analytics/dashboard.html", {"embed_url": embed_url})


@require_GET
def summary(request):
    counts = [row.to_dict() for row in ApiRequestCount.objects.all()]
    events = [row.to_dict() for row in UserBehaviorEvent.objects.all()[:80]]
    user_backup_counts = {}
    for event in UserBehaviorEvent.objects.filter(api_name="backup-file"):
        user_backup_counts[event.username] = user_backup_counts.get(event.username, 0) + 1
    return JsonResponse(
        {
            "result": True,
            "message": "success",
            "data": {
                "counts": counts,
                "events": events,
                "user_backup_counts": [
                    {"username": username, "count": count}
                    for username, count in sorted(user_backup_counts.items())
                ],
            },
        }
    )

