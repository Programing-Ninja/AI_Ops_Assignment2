"""
validate.py
===========
Runs inside ONE pod of the Indexed Job. Kubernetes injects JOB_COMPLETION_INDEX (0..7), which
selects the shard this pod owns. NODE_NAME / POD_NAME come from the Downward API.

Output goes to stdout only (read back later through the Kubernetes API, no shared volume).
The last line is machine-readable:
    RESULT {"shard": 3, "invalid": 17, ...}
"""
import csv
import json
import os
import re
import time

DATA_DIR = os.getenv("DATA_DIR", "/data")
WORK_SECONDS = float(os.getenv("WORK_SECONDS", "0"))
REQUIRED = ("user_id", "name", "email", "signup_date")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


def validate(path):
    total, missing, bad_email = 0, 0, 0
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            total += 1
            if any(not (row.get(f) or "").strip() for f in REQUIRED):
                missing += 1
            elif not EMAIL_RE.match(row["email"]):
                bad_email += 1
    return total, missing, bad_email


def main():
    index = int(os.environ["JOB_COMPLETION_INDEX"])
    node = os.getenv("NODE_NAME", "unknown")
    pod = os.getenv("POD_NAME", "unknown")
    print(f"START shard={index} pod={pod} node={node}", flush=True)

    total, missing, bad_email = validate(os.path.join(DATA_DIR, f"shard_{index}.csv"))

    # Validating 250 rows takes milliseconds; hold the pod so that concurrent pods are
    # actually observable with `kubectl get pods -o wide`. Set WORK_SECONDS=0 to disable.
    time.sleep(WORK_SECONDS)

    result = {
        "shard": index, "rows": total, "invalid": missing + bad_email,
        "missing_field": missing, "bad_email": bad_email,
        "pod": pod, "node": node,
    }
    print("RESULT " + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
