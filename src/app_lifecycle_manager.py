# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # App Lifecycle Manager — Start / Stop Databricks Apps
# MAGIC
# MAGIC Worker notebook called by the scheduled **App Auto-Terminate** jobs.
# MAGIC
# MAGIC | Parameter | Description | Example |
# MAGIC |-----------|-------------|---------|
# MAGIC | `app_names` | Comma-separated app names | `my-app-1,my-app-2` |
# MAGIC | `action` | `start` or `stop` | `stop` |

# COMMAND ----------

import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import AppState

# -- Parameters ----------------------------------------------------------------
dbutils.widgets.text("app_names", "", "App Names (comma-separated)")
dbutils.widgets.dropdown("action", "stop", ["stop", "start"], "Action")

raw_names = dbutils.widgets.get("app_names")
action = dbutils.widgets.get("action")

assert raw_names.strip(), "app_names parameter is required"
assert action in ("start", "stop"), f"Invalid action: {action}"

app_names = [n.strip() for n in raw_names.split(",") if n.strip()]
print(f"Action: {action.upper()} | Apps ({len(app_names)}): {app_names}")

# COMMAND ----------

# -- Execute -------------------------------------------------------------------
w = WorkspaceClient()
results: dict[str, str] = {}

for name in app_names:
    try:
        app = w.apps.get(name)
        print(f"\n[{name}] Current status: {app.status}")

        if action == "stop":
            if app.status == AppState.STOPPED:
                print(f"[{name}] Already stopped — skipping.")
                results[name] = "already_stopped"
                continue
            w.apps.stop(name)
            print(f"[{name}] Stop command issued.")

        elif action == "start":
            if app.status == AppState.RUNNING:
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
        print(f"  {name}: {app.status}  (result: {status})")
    except Exception:
        print(f"  {name}: unable to verify  (result: {status})")

failed = [n for n, s in results.items() if s.startswith("error")]
if failed:
    raise RuntimeError(f"{len(failed)} app(s) failed: {', '.join(failed)}")
print(f"\nDone — {len(results)} app(s) processed successfully.")
