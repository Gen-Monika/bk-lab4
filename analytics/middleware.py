import logging
import time

from django.db import DatabaseError
from django.db.models import F
from django.utils.deprecation import MiddlewareMixin

from .models import ApiRequestCount, UserBehaviorEvent

logger = logging.getLogger(__name__)

TRACKED_ENDPOINTS = {
    "/hosts/api/businesses/": ("CMDB", "business-list"),
    "/hosts/api/sets/": ("CMDB", "set-list"),
    "/hosts/api/modules/": ("CMDB", "module-list"),
    "/hosts/api/hosts/": ("CMDB", "host-list"),
    "/jobs/api/businesses/": ("CMDB", "job-business-list"),
    "/jobs/api/hosts/": ("CMDB", "job-host-list"),
    "/jobs/api/plans/": ("JOB", "plan-list"),
    "/jobs/api/execute-plan/": ("JOB", "execute-plan"),
    "/jobs/api/search-files/": ("JOB", "search-file"),
    "/jobs/api/backup-files/": ("JOB", "backup-file"),
    "/jobs/api/records/": ("JOB", "execution-record"),
}


class RecordUserBehaviorMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._analytics_started_at = time.monotonic()
        return None

    def process_response(self, request, response):
        category, api_name = resolve_behavior(request.path)
        if not category:
            return response
        try:
            username = resolve_username(request)
            started_at = getattr(request, "_analytics_started_at", None)
            duration_ms = 0
            if started_at is not None:
                duration_ms = int((time.monotonic() - started_at) * 1000)
            counter, _ = ApiRequestCount.objects.get_or_create(
                api_category=category,
                api_name=api_name,
                defaults={
                    "request_count": 0,
                    "last_username": username,
                    "last_path": request.path[:512],
                },
            )
            counter.request_count = F("request_count") + 1
            counter.last_username = username
            counter.last_path = request.path[:512]
            counter.save(update_fields=["request_count", "last_username", "last_path", "updated_at"])
            counter.refresh_from_db()
            UserBehaviorEvent.objects.create(
                username=username,
                api_category=category,
                api_name=api_name,
                method=request.method,
                path=request.path[:512],
                status_code=getattr(response, "status_code", 0) or 0,
                duration_ms=duration_ms,
            )
        except DatabaseError:
            logger.exception("Failed to record user behavior")
        except Exception:
            logger.exception("Unexpected analytics middleware error")
        return response


def resolve_behavior(path):
    normalized = normalize_path(path)
    normalized = strip_deployment_prefix(normalized)
    if normalized.startswith("/hosts/api/hosts/") and normalized != "/hosts/api/hosts/":
        return "CMDB", "host-detail"
    if normalized.startswith("/jobs/api/plans/") and normalized != "/jobs/api/plans/":
        return "JOB", "plan-detail"
    if normalized.startswith("/jobs/api/records/") and normalized.endswith("/refresh/"):
        return "JOB", "refresh-record"
    return TRACKED_ENDPOINTS.get(normalized, ("", ""))


def normalize_path(path):
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path += "/"
    return path


def strip_deployment_prefix(path):
    for marker in ("/hosts/", "/jobs/"):
        marker_index = path.find(marker)
        if marker_index > 0:
            return path[marker_index:]
    return path


def resolve_username(request):
    user = getattr(request, "user", None)
    username = getattr(user, "username", "") if user is not None else ""
    return username or "anonymous"
