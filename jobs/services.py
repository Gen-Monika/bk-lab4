import json
import logging
import os
import time

from blueking.component.shortcuts import get_client_by_request

logger = logging.getLogger(__name__)

MAX_STATUS_ATTEMPTS = int(os.getenv("JOB_STATUS_ATTEMPTS", "10"))
STATUS_ATTEMPT_INTERVAL = float(os.getenv("JOB_STATUS_INTERVAL", "0.3"))
WAITING_STATUSES = {1, 2, 4, 7, 8, 9, 10, 11, 12}
SUCCESS_STATUS = 3
STATUS_TEXT = {
    1: "not started",
    2: "running",
    3: "success",
    4: "failed",
    5: "skipped",
    6: "ignored",
    7: "waiting",
    8: "forced",
    9: "state abnormal",
    10: "stopping",
    11: "terminated",
    12: "queueing",
}

STATUS_ALIASES = {
    "waiting": "waiting",
    "pending": "waiting",
    "running": "running",
    "success": "success",
    "succeeded": "success",
    "failed": "failed",
    "failure": "failed",
    "error": "failed",
    "terminated": "terminated",
    "terminate": "terminated",
    "stopping": "stopping",
    "stopped": "terminated",
    "cancelled": "terminated",
    "canceled": "terminated",
    "aborted": "failed",
    "queueing": "queueing",
    "queued": "queueing",
    "not started": "not started",
    "已终止": "terminated",
    "终止": "terminated",
    "停止中": "stopping",
    "已停止": "terminated",
    "排队中": "queueing",
    "等待": "waiting",
    "运行中": "running",
    "成功": "success",
    "失败": "failed",
}


class JobServiceError(Exception):
    pass


class JobService:
    def __init__(self, request):
        self.client = get_client_by_request(request)

    def list_plans(self, bk_biz_id):
        params = {
            "bk_scope_type": "biz",
            "bk_scope_id": bk_biz_id,
            "start": 0,
            "length": 200,
        }
        data = self._call(self.client.jobv3.get_job_plan_list, params)
        rows = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), list) else None
        if rows is None:
            rows = data.get("info") if isinstance(data, dict) else data
        return rows or []

    def get_plan_detail(self, bk_biz_id, job_plan_id):
        params = {
            "bk_scope_type": "biz",
            "bk_scope_id": bk_biz_id,
            "job_plan_id": job_plan_id,
        }
        return self._call(self.client.jobv3.get_job_plan_detail, params)

    def execute_plan(self, bk_biz_id, job_plan_id, host_ids, variables=None):
        global_vars = [
            {
                "name": "host_list",
                "server": {"host_id_list": host_ids},
            }
        ]
        for name, value in (variables or {}).items():
            if value not in (None, ""):
                global_vars.append({"name": name, "value": value})
        params = {
            "bk_scope_type": "biz",
            "bk_scope_id": bk_biz_id,
            "job_plan_id": job_plan_id,
            "global_var_list": global_vars,
        }
        data = self._call(self.client.jobv3.execute_job_plan, params)
        job_instance_id = data.get("job_instance_id") if isinstance(data, dict) else None
        if not job_instance_id:
            raise JobServiceError("JOB did not return a job_instance_id.")
        return data

    def wait_for_first_step(self, bk_biz_id, job_instance_id):
        latest = None
        for _ in range(MAX_STATUS_ATTEMPTS):
            latest = self.get_instance_status(bk_biz_id, job_instance_id)
            step = self.first_step(latest)
            if not step:
                time.sleep(STATUS_ATTEMPT_INTERVAL)
                continue
            status = int(step.get("status", 0) or 0)
            if status == SUCCESS_STATUS or status not in WAITING_STATUSES:
                return latest, step
            time.sleep(STATUS_ATTEMPT_INTERVAL)
        return latest, self.first_step(latest)

    def get_instance_status(self, bk_biz_id, job_instance_id):
        params = {
            "bk_scope_type": "biz",
            "bk_scope_id": bk_biz_id,
            "job_instance_id": job_instance_id,
        }
        return self._call(self.client.jobv3.get_job_instance_status, params)

    def get_ip_log(self, bk_biz_id, job_instance_id, step_instance_id, bk_host_id):
        params = {
            "bk_scope_type": "biz",
            "bk_scope_id": bk_biz_id,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
            "bk_host_id": bk_host_id,
        }
        return self._call(self.client.jobv3.get_job_instance_ip_log, params)

    def collect_step_logs(self, bk_biz_id, job_instance_id, step_instance_id, host_ids):
        rows = []
        for host_id in host_ids:
            data = self.get_ip_log(bk_biz_id, job_instance_id, step_instance_id, host_id)
            raw_content = data.get("log_content", "") if isinstance(data, dict) else ""
            parsed = parse_log_content(raw_content)
            if isinstance(parsed, dict):
                row = parsed
            else:
                row = {"log_content": parsed}
            row["bk_host_id"] = data.get("bk_host_id", host_id) if isinstance(data, dict) else host_id
            rows.append(row)
        return rows

    def _call(self, api, params):
        try:
            result = api(params)
        except Exception as err:
            logger.exception("JOB API call failed")
            raise JobServiceError("JOB request failed. Please check JOB access and retry.") from err
        if not result.get("result"):
            message = result.get("message") or "JOB request returned an error."
            logger.warning("JOB API returned error: %s", message)
            raise JobServiceError(message)
        return result.get("data") or {}

    @staticmethod
    def first_step(status_data):
        steps = status_data.get("step_instance_list") if isinstance(status_data, dict) else None
        if isinstance(steps, list) and steps:
            return steps[0]
        return None


def parse_log_content(content):
    if content is None:
        return ""
    text = str(content).strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except ValueError:
        return text


def status_text(status):
    if isinstance(status, str):
        text = status.strip()
        if not text:
            return "unknown"
        lowered = text.lower()
        if lowered in STATUS_ALIASES:
            return STATUS_ALIASES[lowered]
        if text in STATUS_ALIASES:
            return STATUS_ALIASES[text]
        try:
            status = int(text)
        except (TypeError, ValueError):
            return text
    try:
        status = int(status)
    except (TypeError, ValueError):
        return "unknown"
    return STATUS_TEXT.get(status, "status-{}".format(status))


def resolve_status_value(status_data, step=None):
    for source in (step or {}, status_data or {}):
        if not isinstance(source, dict):
            continue
        for key in (
            "status",
            "status_code",
            "job_instance_status",
            "status_name",
            "status_text",
            "display_status",
        ):
            value = source.get(key)
            if value not in (None, ""):
                return value
    return None


def build_job_url(job_instance_id):
    host = os.getenv("BKPAAS_JOB_URL") or "https://job.ce.bktencent.com"
    return "{}/?jobInstanceId={}".format(host.rstrip("/"), job_instance_id)
