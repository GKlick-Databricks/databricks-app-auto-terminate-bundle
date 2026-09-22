# Databricks App Auto-Terminate Bundle

A **Declarative Automation Bundle (DAB)** that automatically stops Databricks Apps before the weekend and starts them again Monday morning — saving compute costs for non-production environments.

## What It Does

| Job | Default Schedule | Action |
|-----|-----------------|--------|
| **App Auto-Terminate — Stop** | Friday 8:00 PM ET | Stops all specified apps |
| **App Auto-Terminate — Start** | Monday 7:00 AM ET | Starts all specified apps |

Both jobs call a single worker notebook (`src/app_lifecycle_manager.py`) that:
- Accepts 1–N app names (comma-separated)
- Skips apps already in the desired state
- Handles per-app errors without blocking other apps
- Raises on failures so the job surfaces issues

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

Or override at deploy time:

```bash
databricks bundle deploy -t prod \
  -v app_names="prod-app-1,prod-app-2" \
  -v timezone="America/Chicago"
```

### Per-Environment Overrides

Set different apps per target in `databricks.yml`:

```yaml
targets:
  dev:
    variables:
      app_names: "dev-dashboard,dev-api"
  prod:
    variables:
      app_names: "prod-dashboard,prod-api,prod-reports"
```

## Cron Reference

Format: `seconds minutes hours day-of-month month day-of-week`

| Example | Expression |
|---------|------------|
| Friday 6 PM | `0 0 18 ? * FRI` |
| Friday 10 PM | `0 0 22 ? * FRI` |
| Monday 6 AM | `0 0 6 ? * MON` |
| Monday 9 AM | `0 0 9 ? * MON` |
| Weekdays 8 AM | `0 0 8 ? * MON-FRI` |

## Managing the Bundle

```bash
# Check deployed state
databricks bundle summary -t dev

# Trigger a manual run
databricks bundle run app_cleanup_stop -t dev
databricks bundle run app_cleanup_start -t dev

# Tear down all resources
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
| Schedule not firing | Ensure `pause_status: UNPAUSED` in jobs.yml |
| Wrong timezone | Update `timezone` variable to your IANA timezone |
| Need to add an app | Append to `app_names` variable, redeploy |
| Need to remove an app | Remove from `app_names` variable, redeploy |
