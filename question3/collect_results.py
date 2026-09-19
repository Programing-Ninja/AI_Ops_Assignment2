"""
collect_results.py
==================
Collects every shard's invalid-row count by reading pod logs through the Kubernetes API
(CoreV1Api.read_namespaced_pod_log, the same endpoint `kubectl logs` uses), NOT through a shared
volume. It then compares the counts against the generator's ground truth.

Usage:
    pip install kubernetes
    python collect_results.py [--job signup-validator] [--namespace default]
"""
import argparse
import json
from pathlib import Path

from kubernetes import client, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", default="signup-validator")
    parser.add_argument("--namespace", default="default")
    args = parser.parse_args()

    config.load_kube_config()          # same ~/.kube/config that kubectl uses (minikube context)
    v1 = client.CoreV1Api()

    pods = v1.list_namespaced_pod(args.namespace, label_selector=f"job-name={args.job}").items
    results = {}
    for pod in pods:
        if pod.status.phase != "Succeeded":   # skip failed/retried attempts
            continue
        # _preload_content=False: newer clients return str(bytes) ("b'...\\n...'") otherwise
        log = v1.read_namespaced_pod_log(pod.metadata.name, args.namespace,
                                         _preload_content=False).data.decode()
        line = next(l for l in reversed(log.splitlines()) if l.startswith("RESULT "))
        r = json.loads(line[len("RESULT "):])
        results[r["shard"]] = r

    expected_path = Path(__file__).parent / "shards" / "expected_counts.json"
    expected = json.loads(expected_path.read_text()) if expected_path.exists() else {}

    print(f"{'shard':>5} {'invalid':>7} {'expected':>8} {'missing':>7} {'bad_email':>9}  "
          f"{'node':<14} pod")
    for shard in sorted(results):
        r = results[shard]
        exp = expected.get(str(shard), {}).get("invalid", "?")
        ok = "" if exp == "?" or exp == r["invalid"] else "  <-- MISMATCH"
        print(f"{shard:>5} {r['invalid']:>7} {exp:>8} {r['missing_field']:>7} {r['bad_email']:>9}  "
              f"{r['node']:<14} {r['pod']}{ok}")

    total = sum(r["invalid"] for r in results.values())
    print(f"\nshards collected: {len(results)}/8   total invalid rows: {total}")
    Path("results.json").write_text(json.dumps([results[s] for s in sorted(results)], indent=2))


if __name__ == "__main__":
    main()
