# Databricks App Auto-Terminate Bundle

A **Declarative Automation Bundle (DAB)** that automatically stops Databricks Apps before the weekend and starts them again Monday morning — saving compute costs for non-production environments.

## How It Works

This bundle creates two scheduled Lakeflow Jobs in your workspace:

| Job | Default Schedule | Action |
|-----|-----------------|--------|
| **App Auto-Terminate — Stop** | Friday 8:00 PM ET | Stops all specified apps |
| **App Auto-Terminate — Start** | Monday 7:00 AM ET | Starts all specified apps |

Both jobs call a single worker notebook (`src/app_lifecycle_manager.py`) that:
- Accepts 1–N app names (comma-separated)
- Skips apps already in the desired state
- Handles per-app errors without blocking other apps
- Raises on failures so the job surfaces issues

## What "Stop" Actually Means

Stopping an app **only shuts down the app's own compute container** — the web process that serves the app's URL. It does **not** affect any other resources in your workspace.

### ✅ NOT affected by stopping an app

| Resource | Behavior |
|----------|----------|
| **Model Serving endpoints** | Continue running independently — they have their own lifecycle |
| **SQL Warehouses** | Unaffected — governed by their own auto-stop settings |
| **Lakebase databases** | Remain active and accessible by other consumers |
| **Unity Catalog objects** (tables, volumes, models) | Persist as-is — metadata and data are untouched |
| **Secrets** | Remain in place in their scopes |
| **Other jobs, pipelines, or apps** | Completely independent — no cross-impact |
| **App service principal** | Stays intact — credentials and permissions are preserved |
| **App configuration & source code** | Preserved — the app redeploys from the same config on start |

### ⚠️ What IS affected

| Impact | Details |
|--------|---------|
| **App URL becomes unavailable** | HTTP requests to the app's URL will fail while stopped |
| **Downstream callers** | Any service, webhook, or integration that calls the app's URL will receive errors until the app restarts |
| **Scheduled app-internal tasks** | If the app itself runs internal schedulers or background workers, those stop with the app |

### On Restart (Monday Morning)

When the start job fires, the app boots back up from its existing deployment — same source code, same config, same service principal. It automatically reconnects to all referenced resources (warehouses, endpoints, databases, etc.). No manual intervention required.

## Prerequisites

- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) v0.230+
- Authenticated profile: `databricks auth login --host <workspace-url>`
- Workspace permissions to create jobs and manage apps

## Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/GKlick-Databricks/databricks-app-auto-terminate-bundle.git
cd databricks-app-auto-terminate-bundle

# 2. Set your app names in databricks.yml (see Configuration below)

# 3. Validate
databricks bundle validate -t dev

# 4. Deploy
databricks bundle deploy -t dev
```

That's it — the jobs are live and will run on schedule.

## Configuration

Edit the `variables` section in `databricks.yml`:

```yaml
variables:
  app_names:
    default: "my-app-1,my-app-2,my-app-3"   # Your apps here
  stop_cron:
    default: "0 0 20 ? * FRI"               # Friday 8 PM
  start_cron:
    default: "0 0 7 ? * MON"                # Monday 7 AM
  timezone:
    default: "America/New_York"
```

Or override at deploy time without editing files:

```bash
databricks bundle deploy -t prod \
  -v app_names="prod-app-1,prod-app-2" \
  -v timezone="America/Chicago"
```

### Per-Environment Overrides

Manage different apps per environment in `databricks.yml`:

```yaml
targets:
  dev:
    variables:
      app_names: "dev-dashboard,dev-api"
  prod:
    variables:
      app_names: "prod-dashboard,prod-api,prod-reports"
```

### Adding or Removing Apps

Just update the `app_names` variable and redeploy — no code changes needed:

```bash
# Add a new app
databricks bundle deploy -t dev -v app_names="app-1,app-2,new-app-3"
```

## Cron Reference

Format: `seconds minutes hours day-of-month month day-of-week`

| Schedule | Expression |
|----------|------------|
| Friday 6 PM | `0 0 18 ? * FRI` |
| Friday 10 PM | `0 0 22 ? * FRI` |
| Monday 6 AM | `0 0 6 ? * MON` |
| Monday 9 AM | `0 0 9 ? * MON` |
| Weekdays 8 AM | `0 0 8 ? * MON-FRI` |

## Managing the Bundle

```bash
# Check deployed state
databricks bundle summary -t dev

# Trigger a manual stop (e.g. before a holiday)
databricks bundle run app_cleanup_stop -t dev

# Trigger a manual start (e.g. after a holiday)
databricks bundle run app_cleanup_start -t dev

# Remove all bundle resources from workspace
databricks bundle destroy -t dev
```

## Project Structure

```
databricks-app-auto-terminate-bundle/
├── databricks.yml              # Bundle config, variables, targets
├── README.md                   # This file
├── resources/
│   └── jobs.yml                # Job definitions (stop + start)
└── src/
    └── app_lifecycle_manager.py # Worker notebook
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Job fails with "app not found" | Verify the app name matches exactly (case-sensitive) |
| Apps not stopping/starting | Check the job run output for per-app error details |
| Schedule not firing | Ensure `pause_status: UNPAUSED` in `resources/jobs.yml` |
| Wrong timezone | Update `timezone` variable to your IANA timezone |
| App slow to start on Monday | Normal — first boot cold-starts the container; subsequent requests are fast |
| Downstream service errors on weekend | Expected — the app URL is unavailable while stopped; callers should handle gracefully |
