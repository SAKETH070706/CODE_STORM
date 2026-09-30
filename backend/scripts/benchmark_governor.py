"""Offline, isolated benchmark. Never calls live providers or changes demo state."""
import argparse
import json
import math
import os
import platform
import sqlite3
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.governor_store import Store
from core.governor_adapters import Adapters
from core.governor_service import Governor
from core.governor_identity import Principal
from core.governor_policy import evaluate, load_policy
from core.governor_semantic import assess
from core.permission_governor import ActionRequest


def stats(values):
    ordered = sorted(values)
    return {f"p{p}_ms": round(ordered[min(len(ordered)-1, math.ceil(len(ordered)*p/100)-1)], 3) for p in (50, 95, 99)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.samples <= 10000 or not 1 <= args.concurrency <= 32:
        parser.error("Use 1..10000 samples and 1..32 concurrency")
    request = {"task_id": "sales-report", "tool": "database.read", "resource": "sales_summary", "arguments": {"limit": 3}}
    principal = Principal("analyst-1", "data_analyst")
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        store = Store(root / "governor.db")
        store.migrate()
        demo = root / "demo.db"
        with sqlite3.connect(demo) as c:
            c.execute("CREATE TABLE sales_summary(month TEXT,total_sales INTEGER)")
            c.executemany("INSERT INTO sales_summary VALUES(?,?)", [("January", 120000), ("February", 135000), ("March", 142000)])
        c.close()
        governor = Governor(store, Adapters(store, demo, root / "reports"))
        policy = load_policy()
        start = time.perf_counter()
        governor.submit(request, principal)
        cold = (time.perf_counter() - start) * 1000
        for _ in range(10):
            governor.submit(request, principal)
        def sample(_):
            with store.connection() as c:
                start = time.perf_counter()
                evaluate(c, request, principal, policy)
                deterministic = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            governor.submit(request, principal, evaluation_only=True)
            durable = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            result = governor.submit(request, principal)
            total = (time.perf_counter() - start) * 1000
            if result["state"] != "SUCCEEDED":
                raise RuntimeError("Benchmark action failed")
            return deterministic, durable, result["stage_timings"]["execution_ms"], total
        start = time.perf_counter()
        with ThreadPoolExecutor(args.concurrency) as pool:
            results = list(pool.map(sample, range(args.samples)))
        duration = time.perf_counter() - start
        semantic = []
        def mock_provider(**kwargs):
            return type("Result", (), {"success": True, "text": '{"verdict":"ALLOW","reason":"mock only"}'})()
        for _ in range(args.samples):
            start = time.perf_counter()
            assess(ActionRequest.model_validate(request), {}, provider=mock_provider)
            semantic.append((time.perf_counter() - start) * 1000)
        output = {
            "hardware": {"platform": platform.platform(), "cpu": platform.processor(), "logical_cpus": os.cpu_count(), "python": platform.python_version()},
            "workload": "3 synthetic rows; each sample: deterministic evaluation + durable evaluation-only + durable read/artifact execution; WAL/FULL",
            "samples": args.samples, "concurrency": args.concurrency, "warmup_executions": 10,
            "first_execution_ms": round(cold, 3), "conditions": "Fresh temporary databases; OS caches uncontrolled; first execution is not a cold OS boot",
            "workload_samples_per_second": round(args.samples / duration, 2),
            "deterministic": stats([r[0] for r in results]), "durable_evaluation": stats([r[1] for r in results]),
            "adapter_execution": stats([r[2] for r in results]), "end_to_end_execution": stats([r[3] for r in results]),
            "semantic_mock_only": stats(semantic), "live_semantic": "not run",
            "targets": "<5ms deterministic and <10ms fast-path evaluation are targets, not guarantees"
        }
        print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()

