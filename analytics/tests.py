from django.test import Client, TestCase
from django.urls import reverse

from analytics.middleware import resolve_behavior
from analytics.models import ApiRequestCount, UserBehaviorEvent


class AnalyticsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_renders(self):
        response = self.client.get(reverse("analytics:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BKVision Behavior Dashboard")
        self.assertContains(response, "BKVISION_DASHBOARD_URL")
        self.assertContains(response, "petDock")
        self.assertContains(response, "toggleArchivedCounts")
        self.assertContains(response, "toggleArchivedEvents")
        self.assertContains(response, "selectCounts")
        self.assertContains(response, "selectEvents")
        self.assertContains(response, "archiveSelectedCounts")
        self.assertContains(response, "archiveSelectedEvents")
        self.assertContains(response, "data-count-archive")
        self.assertContains(response, "data-event-archive")

    def test_summary_returns_counts_and_events(self):
        ApiRequestCount.objects.create(
            api_category="JOB",
            api_name="backup-file",
            request_count=2,
            last_username="alice",
            last_path="/jobs/api/backup-files/",
        )
        UserBehaviorEvent.objects.create(
            username="alice",
            api_category="JOB",
            api_name="backup-file",
            method="POST",
            path="/jobs/api/backup-files/",
            status_code=200,
            duration_ms=12,
        )

        response = self.client.get(reverse("analytics:summary"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["counts"][0]["api_name"], "backup-file")
        self.assertEqual(payload["events"][0]["id"], UserBehaviorEvent.objects.get().id)
        self.assertEqual(payload["events"][0]["username"], "alice")
        self.assertEqual(payload["user_backup_counts"], [{"username": "alice", "count": 1}])

    def test_middleware_records_tracked_api(self):
        response = self.client.get(reverse("analytics:summary"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ApiRequestCount.objects.exists())

        response = self.client.get(reverse("jobs:records"))

        self.assertEqual(response.status_code, 200)
        counter = ApiRequestCount.objects.get(api_category="JOB", api_name="execution-record")
        self.assertEqual(counter.request_count, 1)
        event = UserBehaviorEvent.objects.get(api_category="JOB", api_name="execution-record")
        self.assertEqual(event.path, "/jobs/api/records/")
        self.assertEqual(event.status_code, 200)

    def test_dynamic_paths_are_grouped(self):
        self.assertEqual(resolve_behavior("/hosts/api/hosts/1001"), ("CMDB", "host-detail"))
        self.assertEqual(resolve_behavior("/jobs/api/plans/3001/"), ("JOB", "plan-detail"))
        self.assertEqual(resolve_behavior("/jobs/api/records/8/refresh/"), ("JOB", "refresh-record"))
        self.assertEqual(
            resolve_behavior("/stag--bk-lab4/jobs/api/records/"),
            ("JOB", "execution-record"),
        )
        self.assertEqual(
            resolve_behavior("/stag--bk-lab4/hosts/api/hosts/1001/"),
            ("CMDB", "host-detail"),
        )
