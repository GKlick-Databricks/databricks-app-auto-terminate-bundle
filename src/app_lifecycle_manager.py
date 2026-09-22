# Databricks notebook source


# COMMAND ----------

# MAGIC %md
# MAGIC # App Lifecycle Manager — Start / Stop Databricks Apps
# MAGIC
# MAGIC Worker notebook called by the scheduled **App Auto-Terminate** jobs.
# MAGIC
# MAGIC | Parameter | Description | Example |
# MAGIC |-----------|-------------|---------|
# MAGIC | `app_names` | Comma-separated app names, or `__ALL__` to target every app in the workspace | `my-app-1,my-app-2` or `__ALL__` |
# MAGIC | `action` | `start` or `stop` | `stop` |
# MAGIC
# MAGIC When `app_names` is `__ALL__` (or empty), the notebook discovers all apps via the SDK and filters by state:
# MAGIC - **stop** targets apps whose compute is `ACTIVE` (running)
# MAGIC - **start** targets apps whose compute is not `ACTIVE` (stopped)

# COMMAND ----------

import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import ApplicationState, ComputeState

# -- Parameters ----------------------------------------------------------------
dbutils.widgets.text("app_names", "", "App Names (comma-separated, or __ALL__ for every active app)")
dbutils.widgets.dropdown("action", "stop", ["stop", "start"], "Action")

raw_names = dbutils.widgets.get("app_names")
action = dbutils.widgets.get("action")

assert action in ("start", "stop"), f"Invalid action: {action}"

w = WorkspaceClient()

# Resolve app names — __ALL__ discovers every app in the workspace
if raw_names.strip().upper() == "__ALL__" or not raw_names.strip():
    print("Discovering all apps in the workspace…")
    all_apps = list(w.apps.list())
    def is_running(app):
        """Check if app is running via app_status or compute_status."""
        if app.app_status and app.app_status.state == ApplicationState.RUNNING:
            return True
        if app.compute_status and app.compute_status.state == ComputeState.ACTIVE:
            return True
        return False

    if action == "stop":
        app_names = [a.name for a in all_apps if is_running(a)]
    else:
        app_names = [a.name for a in all_apps if not is_running(a)]
    print(f"Found {len(all_apps)} total app(s), {len(app_names)} eligible for {action.upper()}.")
else:
    app_names = [n.strip() for n in raw_names.split(",") if n.strip()]

if not app_names:
    print(f"No apps found to {action} — nothing to do.")
    dbutils.notebook.exit(f"No apps to {action}")
print(f"Action: {action.upper()} | Apps ({len(app_names)}): {app_names}")

# COMMAND ----------

# -- Execute -------------------------------------------------------------------
results: dict[str, str] = {}

for name in app_names:
    try:
        app = w.apps.get(name)
        current_state = app.app_status.state if app.app_status else None
        print(f"\n[{name}] Current status: {current_state}")

        compute_st = app.compute_status.state if app.compute_status else None
        print(f"[{name}] compute_status: {compute_st}")

        if action == "stop":
            if current_state != ApplicationState.RUNNING and compute_st != ComputeState.ACTIVE:
                print(f"[{name}] Not running — skipping.")
                results[name] = "already_stopped"
                continue
            w.apps.stop(name)
            print(f"[{name}] Stop command issued.")

        elif action == "start":
            if current_state == ApplicationState.RUNNING or compute_st == ComputeState.ACTIVE:
                print(f"[{name}] Already running — skipping.")
                results[name] = "already_running"
                continue
            w.apps.start(name)
            print(f"[{name}] Start command issued.")

        results[name] = "ok"

    except Exception as e:
        print(f"[{name}] ERROR: {e}")
        results[name] = f"error: {e}"

# COMMAND ----------

# -- Summary -------------------------------------------------------------------
time.sleep(5)
print("=" * 60)
print("SUMMARY")
print("=" * 60)
for name, status in results.items():
    try:
        app = w.apps.get(name)
        state = app.app_status.state if app.app_status else "unknown"
        print(f"  {name}: {state}  (result: {status})")
    except Exception:
        print(f"  {name}: unable to verify  (result: {status})")

failed = [n for n, s in results.items() if s.startswith("error")]
if failed:
    raise RuntimeError(f"{len(failed)} app(s) failed: {', '.join(failed)}")
print(f"\nDone — {len(results)} app(s) processed successfully.")