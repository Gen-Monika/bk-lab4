from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from jobs.models import JobExecutionRecord
from jobs.services import status_text
from jobs import views

TEST_BUSINESSES = [
    {"bk_biz_id": 2, "bk_biz_name": "Arena Ops"},
]

TEST_HOSTS = [
    {
        "bk_host_id": 1001,
        "bk_biz_id": 2,
        "bk_host_innerip": "10.0.1.11",
        "bk_host_name": "login-01",
        "bk_os_name": "CentOS",
        "operator": "alice",
        "bk_bak_operator": "bob",
    }
]


class FakeCmdbApi:
    def search_business(self, params):
        return {"result": True, "data": {"info": TEST_BUSINESSES}}

    def list_biz_hosts(self, params):
        return {"result": True, "data": {"info": TEST_HOSTS}}


class FakeJobV3Api:
    def get_job_plan_list(self, params):
        return {
            "result": True,
            "data": {
                "data": [
                    {
                        "id": 3001,
                        "name": "Search game logs",
                        "creator": "alice",
                        "update_time": "2026-05-26 01:00:00",
                    }
                ]
            },
        }

    def get_job_plan_detail(self, params):
        return {
            "result": True,
            "data": {"id": params["job_plan_id"], "name": "Search game logs"},
        }

    def execute_job_plan(self, params):
        return {
            "result": True,
            "data": {
                "job_instance_id": 99001,
                "job_instance_name": "Search game logs",
            },
        }

    def get_job_instance_status(self, params):
        return {
            "result": True,
            "data": {
                "step_instance_list": [
                    {
                        "step_instance_id": 88001,
                        "status": 3,
                    }
                ]
            },
        }

    def get_job_instance_ip_log(self, params):
        return {
            "result": True,
            "data": {
                "bk_host_id": params["bk_host_id"],
                "log_content": (
                    '{"bk_file_list": "game.log", '
                    '"bk_file_cnt": 1, '
                    '"bk_file_total_size": 128}'
                ),
            },
        }


class TerminatedJobV3Api(FakeJobV3Api):
    def get_job_instance_status(self, params):
        return {
            "result": True,
            "data": {
                "step_instance_list": [
                    {
                        "step_instance_id": 88002,
                        "status": "terminated",
                    }
                ]
            },
        }


class FakeBlueKingClient:
    def __init__(self):
        self.cc = FakeCmdbApi()
        self.jobv3 = FakeJobV3Api()


class JobConsoleTests(TestCase):
    def setUp(self):
        for view in (
            views.index,
            views.businesses,
            views.hosts,
            views.plans,
            views.plan_detail,
            views.execute_plan,
            views.search_files,
            views.backup_files,
            views.records,
            views.refresh_record,
        ):
            view.login_exempt = True
        self.client = Client(enforce_csrf_checks=False)
        self.cmdb_client_patch = patch(
            "hosts.cmdb.get_client_by_request",
            return_value=FakeBlueKingClient(),
        )
        self.job_client_patch = patch(
            "jobs.services.get_client_by_request",
            return_value=FakeBlueKingClient(),
        )
        self.cmdb_client_patch.start()
        self.job_client_patch.start()

    def tearDown(self):
        self.job_client_patch.stop()
        self.cmdb_client_patch.stop()

    def test_index_page_renders(self):
        response = self.client.get(reverse("jobs:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "JOB Log Backup Console")

    def test_cmdb_host_scope(self):
        response = self.client.get(reverse("jobs:businesses"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["bk_biz_name"], "Arena Ops")

        response = self.client.get(reverse("jobs:hosts"), {"bk_biz_id": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["bk_host_name"], "login-01")

    def test_job_plan_list_and_detail(self):
        response = self.client.get(reverse("jobs:plans"), {"bk_biz_id": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["id"], 3001)

        response = self.client.get(reverse("jobs:plan_detail", args=[3001]), {"bk_biz_id": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["name"], "Search game logs")

    def test_search_files_creates_record(self):
        response = self.client.post(
            reverse("jobs:search_files"),
            data={
                "bk_biz_id": 2,
                "job_plan_id": 3001,
                "host_ids": [1001],
                "search_path": "/project",
                "suffix": "log",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["logs"][0]["bk_file_list"], "game.log")
        self.assertEqual(payload["record"]["job_instance_id"], 99001)

        response = self.client.get(reverse("jobs:records"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["status_text"], "success")

    def test_refresh_record_handles_terminated_status(self):
        record = JobExecutionRecord.objects.create(
            action=JobExecutionRecord.ACTION_SEARCH,
            bk_biz_id=2,
            bk_host_ids="1001",
            job_plan_id=3001,
            job_instance_id=99002,
            job_instance_name="Search game logs",
            status=2,
            status_text="waiting",
        )

        with patch(
            "jobs.services.get_client_by_request",
            return_value=type(
                "TerminatedClient",
                (),
                {"cc": FakeCmdbApi(), "jobv3": TerminatedJobV3Api()},
            )(),
        ):
            response = self.client.post(
                reverse("jobs:refresh_record", args=[record.id]),
                data="{}",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["record"]
        self.assertEqual(payload["status_text"], "terminated")
        self.assertEqual(status_text("terminated"), "terminated")
