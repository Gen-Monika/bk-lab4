# BKVision Behavior Analytics Console

BlueKing Django SaaS course project for collecting user behavior data from CMDB and JOB workflows, storing it in the SaaS database, and embedding a BKVision dashboard.

## Features

- CMDB business, set, module, host, and host detail workflow from the previous labs.
- JOB plan selection, log search, backup execution, and execution record workflow.
- Django middleware that records selected API visits as behavior events.
- Local database tables for API request counters and recent user behavior events.
- `/analytics/` dashboard with total calls, tracked API count, backup action count, local event tables, and BKVision iframe embedding.
- `BKVISION_DASHBOARD_URL` environment variable for switching the embedded BKVision dashboard after publishing it on BlueKing.
- Visual theme controls and draggable desktop pet interaction reused as lightweight project polish.
- Paged Help guides with screenshots for the BKVision dashboard, inherited CMDB host workflow, and inherited JOB execution workflow.

## Routes

- `/jobs/`: JOB log backup console
- `/hosts/`: CMDB host query console
- `/analytics/`: BKVision behavior analytics dashboard
- `/analytics/api/summary/`: local behavior summary API
- `/`: redirects to `/analytics/`

Tracked API categories include CMDB business, set, module, host, host detail, JOB plan list, JOB plan detail, search file, backup file, execution record, and record refresh.

## Local Development

Use the shared Python environment and set BlueKing environment variables as in the previous labs.

```powershell
$env:BKPAAS_ENVIRONMENT = "test"
$env:BKPAAS_MAJOR_VERSION = "3"
$env:BK_PAAS_HOST = "https://ce.bktencent.com"
$env:BK_URL = "https://ce.bktencent.com"
$env:APP_ID = "bk-lab4"
$env:APP_TOKEN = "local-test-token"
$env:BKPAAS_APP_ID = "bk-lab4"
$env:BKPAAS_APP_SECRET = "local-test-token"
$env:BK_PAAS2_URL = "https://ce.bktencent.com"
$env:BK_COMPONENT_API_URL = "https://bkapi.ce.bktencent.com"
$env:BKPAAS_JOB_URL = "https://job.ce.bktencent.com"
$env:BKVISION_DASHBOARD_URL = ""
python manage.py migrate
python manage.py runserver 127.0.0.1:8005
```

After BKVision is configured on the platform, set `BKVISION_DASHBOARD_URL` to the published dashboard URL and redeploy or restart the local server.

Recommended checks:

```powershell
python manage.py check
python manage.py test analytics jobs
```

## Course Material Note

The provided `BKVision - front-end code package.zip` and `BKVision - back-end code package.zip` are Git LFS pointer files rather than complete zip archives. This project implements the required behavior collection and embedding workflow with Django middleware, local database tables, and a dashboard page that can host the BKVision iframe.

## Structured JOB Results

The inherited JOB console supports structured file results when the JOB script prints a line starting with `BK_JOB_RESULT=`. Reusable templates are stored in `docs/job_scripts/`, including `search_or_backup_structured.sh`, which can handle both search and backup based on whether `backup_path` is provided.

When the BlueKing account does not have permission to create or edit JOB execution plans, the application still works with the existing plan and falls back to summary-style results. This keeps the behavior analytics workflow usable while preserving the optional structured-output path for environments with full JOB permissions.

The analytics, CMDB, and JOB frontends include Help guides that open once on first entry and remain available from the top toolbar. Compressed guide screenshots are stored under `static/analytics/help/`, `static/hosts/help/`, and `static/jobs/help/`.
