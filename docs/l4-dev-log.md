# L4 BKVision Behavior Analytics Development Log

Date: 2026-05-26

## Summary

Started the fourth BlueKing SaaS course project from the finished JOB console. The provided BKVision front-end and back-end packages were not usable as normal source packages, so the implementation keeps the working SaaS features and adds a local behavior collection layer for BKVision visualization.

## Changes

- Added the `analytics` Django app for user behavior and API call statistics.
- Added `RecordUserBehaviorMiddleware` to collect CMDB and JOB API visits without interrupting business requests.
- Added `ApiRequestCount` and `UserBehaviorEvent` database tables for aggregated API counters and recent behavior events.
- Added `/analytics/` as the behavior analytics dashboard page.
- Added `/analytics/api/summary/` as the local statistics API used by the dashboard.
- Set the application root route to the analytics dashboard for the L4 experiment entry point.
- Added `BKVISION_DASHBOARD_URL` support for embedding a published BKVision dashboard through an iframe.
- Reused the polished visual theme controls and draggable desktop pet interaction from the previous labs.
- Kept the JOB log search and backup workflow as the behavior source for the analytics experiment.
- Updated behavior path matching to support BlueKing deployment prefixes such as `/stag--bk-lab4/`.
- Added explicit return links from the JOB and CMDB pages back to the analytics dashboard.

## Verification

- `python manage.py check`
- `python manage.py test analytics jobs`

## Maintenance Update

- Synced the JOB execution status parser from L3 so terminated and platform-specific status values no longer render as `unknown` in inherited Execution Records.
- Added regression coverage for refreshing a terminated JOB execution record.
- Synced active JOB auto-refresh, result backfill, archive controls, and archived-item visual separation from L3 so the inherited JOB console remains consistent.
- Added structured JOB script templates under `docs/job_scripts/`; scripts emit `BK_JOB_RESULT={...}` for BKVision-related JOB operations that need file count and size data.
- Added a unified structured JOB script that supports both search and backup by detecting whether `backup_path` is provided, matching single-script JOB plans.
