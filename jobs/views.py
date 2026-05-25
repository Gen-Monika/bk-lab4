import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from hosts.cmdb import CmdbService, CmdbServiceError

from .models import JobExecutionRecord
from .services import JobService, JobServiceError, build_job_url, status_text


@ensure_csrf_cookie
def index(request):
    return render(request, "jobs/index.html")


@require_GET
def businesses(request):
    return _cmdb_response(lambda: CmdbService(request).list_businesses())


@require_GET
def hosts(request):
    bk_biz_id = _int_query(request, "bk_biz_id")
    if not bk_biz_id:
        return _bad_request("bk_biz_id is required")
    filters = {
        "bk_biz_id": bk_biz_id,
        "bk_set_ids": [],
        "bk_module_ids": [],
        "bk_host_name": request.GET.get("bk_host_name", "").strip(),
        "operator": request.GET.get("operator", "").strip(),
        "bk_bak_operator": request.GET.get("bk_bak_operator", "").strip(),
        "bk_host_innerip": request.GET.get("bk_host_innerip", "").strip(),
    }
    return _cmdb_response(lambda: CmdbService(request).list_hosts(filters))


@require_GET
def plans(request):
    bk_biz_id = _int_query(request, "bk_biz_id")
    if not bk_biz_id:
        return _bad_request("bk_biz_id is required")
    return _job_response(lambda: JobService(request).list_plans(bk_biz_id))


@require_GET
def plan_detail(request, job_plan_id):
    bk_biz_id = _int_query(request, "bk_biz_id")
    if not bk_biz_id:
        return _bad_request("bk_biz_id is required")
    return _job_response(lambda: JobService(request).get_plan_detail(bk_biz_id, job_plan_id))


@require_POST
def execute_plan(request):
    payload, error = _json_payload(request)
    if error:
        return _bad_request(error)
    parsed = _common_execution_payload(payload)
    if parsed["error"]:
        return _bad_request(parsed["error"])
    variables = payload.get("variables") or {}
    try:
        service = JobService(request)
        data = service.execute_plan(
            parsed["bk_biz_id"],
            parsed["job_plan_id"],
            parsed["host_ids"],
            variables,
        )
        record = _create_record(
            action=JobExecutionRecord.ACTION_PLAN,
            bk_biz_id=parsed["bk_biz_id"],
            job_plan_id=parsed["job_plan_id"],
            host_ids=parsed["host_ids"],
            execute_data=data,
            variables=variables,
        )
        return _ok({"record": record.to_dict(), "job": data})
    except JobServiceError as err:
        return _service_error(str(err))


@require_POST
def search_files(request):
    payload, error = _json_payload(request)
    if error:
        return _bad_request(error)
    parsed = _common_execution_payload(payload)
    if parsed["error"]:
        return _bad_request(parsed["error"])
    search_path = str(payload.get("search_path", "")).strip()
    suffix = str(payload.get("suffix", "")).strip().lstrip(".")
    if not search_path:
        return _bad_request("search_path is required")
    if not suffix:
        return _bad_request("suffix is required")
    variables = {"search_path": search_path, "suffix": suffix}
    return _execute_and_collect(
        request,
        action=JobExecutionRecord.ACTION_SEARCH,
        bk_biz_id=parsed["bk_biz_id"],
        job_plan_id=parsed["job_plan_id"],
        host_ids=parsed["host_ids"],
        variables=variables,
        search_path=search_path,
        suffix=suffix,
    )


@require_POST
def backup_files(request):
    payload, error = _json_payload(request)
    if error:
        return _bad_request(error)
    parsed = _common_execution_payload(payload)
    if parsed["error"]:
        return _bad_request(parsed["error"])
    search_path = str(payload.get("search_path", "")).strip()
    suffix = str(payload.get("suffix", "")).strip().lstrip(".")
    backup_path = str(payload.get("backup_path", "")).strip()
    if not search_path:
        return _bad_request("search_path is required")
    if not suffix:
        return _bad_request("suffix is required")
    if not backup_path:
        return _bad_request("backup_path is required")
    variables = {
        "search_path": search_path,
        "suffix": suffix,
        "backup_path": backup_path,
    }
    return _execute_and_collect(
        request,
        action=JobExecutionRecord.ACTION_BACKUP,
        bk_biz_id=parsed["bk_biz_id"],
        job_plan_id=parsed["job_plan_id"],
        host_ids=parsed["host_ids"],
        variables=variables,
        search_path=search_path,
        suffix=suffix,
        backup_path=backup_path,
    )


@require_GET
def records(request):
    rows = [record.to_dict() for record in JobExecutionRecord.objects.all()[:50]]
    return _ok(rows)


@require_POST
def refresh_record(request, record_id):
    try:
        record = JobExecutionRecord.objects.get(id=record_id)
    except JobExecutionRecord.DoesNotExist:
        return _bad_request("record not found")
    try:
        service = JobService(request)
        status_data = service.get_instance_status(record.bk_biz_id, record.job_instance_id)
        step = service.first_step(status_data)
        if step:
            record.step_instance_id = step.get("step_instance_id") or record.step_instance_id
            record.status = int(step.get("status", 0) or 0)
            record.status_text = status_text(record.status)
        record.save()
        return _ok({"record": record.to_dict(), "status": status_data})
    except JobServiceError as err:
        return _service_error(str(err))


def _execute_and_collect(
    request,
    action,
    bk_biz_id,
    job_plan_id,
    host_ids,
    variables,
    search_path="",
    suffix="",
    backup_path="",
):
    try:
        service = JobService(request)
        execute_data = service.execute_plan(bk_biz_id, job_plan_id, host_ids, variables)
        job_instance_id = execute_data["job_instance_id"]
        status_data, step = service.wait_for_first_step(bk_biz_id, job_instance_id)
        logs = []
        if step and int(step.get("status", 0) or 0) == 3:
            logs = service.collect_step_logs(
                bk_biz_id,
                job_instance_id,
                step.get("step_instance_id"),
                host_ids,
            )
        record = _create_record(
            action=action,
            bk_biz_id=bk_biz_id,
            job_plan_id=job_plan_id,
            host_ids=host_ids,
            execute_data=execute_data,
            variables=variables,
            step=step,
            search_path=search_path,
            suffix=suffix,
            backup_path=backup_path,
            result_summary=_summarize_logs(logs),
        )
        return _ok({"record": record.to_dict(), "status": status_data, "logs": logs})
    except JobServiceError as err:
        return _service_error(str(err))


def _create_record(
    action,
    bk_biz_id,
    job_plan_id,
    host_ids,
    execute_data,
    variables,
    step=None,
    search_path="",
    suffix="",
    backup_path="",
    result_summary="",
):
    job_instance_id = execute_data.get("job_instance_id", 0)
    job_instance_name = execute_data.get("job_instance_name", "")
    status = int(step.get("status", 2) if step else 2)
    step_instance_id = step.get("step_instance_id", 0) if step else 0
    return JobExecutionRecord.objects.create(
        action=action,
        bk_biz_id=bk_biz_id,
        bk_host_ids=",".join(str(host_id) for host_id in host_ids),
        job_plan_id=job_plan_id,
        job_instance_id=job_instance_id,
        job_instance_name=job_instance_name,
        step_instance_id=step_instance_id or 0,
        status=status,
        status_text=status_text(status),
        search_path=search_path or variables.get("search_path", ""),
        suffix=suffix or variables.get("suffix", ""),
        backup_path=backup_path or variables.get("backup_path", ""),
        job_url=build_job_url(job_instance_id),
        result_summary=result_summary,
    )


def _summarize_logs(logs):
    if not logs:
        return ""
    parts = []
    for row in logs:
        host_id = row.get("bk_host_id", "")
        file_count = row.get("bk_file_cnt")
        if file_count is not None:
            parts.append("{}: {} files".format(host_id, file_count))
        elif row.get("message"):
            parts.append("{}: {}".format(host_id, row["message"]))
        else:
            parts.append("{}: completed".format(host_id))
    return "; ".join(parts)


def _common_execution_payload(payload):
    bk_biz_id = _safe_int(payload.get("bk_biz_id"))
    job_plan_id = _safe_int(payload.get("job_plan_id"))
    host_ids = _host_ids(payload.get("host_ids"))
    if not bk_biz_id:
        return {"error": "bk_biz_id is required"}
    if not job_plan_id:
        return {"error": "job_plan_id is required"}
    if not host_ids:
        return {"error": "host_ids is required"}
    return {
        "error": "",
        "bk_biz_id": bk_biz_id,
        "job_plan_id": job_plan_id,
        "host_ids": host_ids,
    }


def _host_ids(value):
    if isinstance(value, str):
        items = [item for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        items = value
    else:
        return []
    result = []
    for item in items:
        host_id = _safe_int(item)
        if host_id:
            result.append(host_id)
    return result


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_payload(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}"), ""
    except (UnicodeDecodeError, ValueError):
        return {}, "invalid JSON payload"


def _int_query(request, key):
    return _safe_int(request.GET.get(key))


def _ok(data):
    return JsonResponse({"result": True, "message": "success", "data": data})


def _bad_request(message):
    return JsonResponse({"result": False, "message": message, "data": None}, status=400)


def _service_error(message):
    return JsonResponse({"result": False, "message": message, "data": None}, status=502)


def _cmdb_response(loader):
    try:
        return _ok(loader())
    except CmdbServiceError as err:
        return _service_error(str(err))


def _job_response(loader):
    try:
        return _ok(loader())
    except JobServiceError as err:
        return _service_error(str(err))

