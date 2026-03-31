import statistics
import threading
import time
from typing import List

from realtime_database import RealtimeDatabaseCluster


def _worker(cluster: RealtimeDatabaseCluster, worker_id: int, events: int, latencies: List[float]) -> None:
    for i in range(events):
        start = time.perf_counter()
        cluster.persist_server_event(
            server_id=f"server-{(worker_id % 3) + 1}",
            metrics={"cpu": (i * 7) % 100, "memory": (i * 3) % 100, "temperature": 45.0},
            alerts=[],
            online=True,
            error=None,
        )
        latencies.append(time.perf_counter() - start)


def run_load_test(workers: int = 10, events_per_worker: int = 100) -> dict:
    cluster = RealtimeDatabaseCluster(base_dir="db_data_test")
    threads = []
    latencies: List[float] = []

    start_total = time.perf_counter()
    for w in range(workers):
        t = threading.Thread(target=_worker, args=(cluster, w, events_per_worker, latencies))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - start_total

    total_events = workers * events_per_worker
    tx_count_primary = len(cluster.get_recent_transactions(limit=total_events + 10))
    throughput = total_events / elapsed if elapsed > 0 else 0.0

    return {
        "workers": workers,
        "events_per_worker": events_per_worker,
        "total_events": total_events,
        "elapsed_seconds": round(elapsed, 4),
        "throughput_events_sec": round(throughput, 2),
        "avg_latency_ms": round(statistics.mean(latencies) * 1000, 3) if latencies else 0.0,
        "p95_latency_ms": round(statistics.quantiles(latencies, n=100)[94] * 1000, 3) if len(latencies) >= 100 else 0.0,
        "tx_seen_primary": tx_count_primary,
    }


def run_failover_test() -> dict:
    cluster = RealtimeDatabaseCluster(base_dir="db_data_test")
    cluster.set_node_availability("node_c", False)
    cluster.persist_server_event("server-1", {"cpu": 65.0, "memory": 40.0, "temperature": 50.0}, [], True, None)
    cluster.persist_server_event("server-2", {"cpu": 88.0, "memory": 70.0, "temperature": 82.0}, ["CPU high"], True, None)

    status = cluster.get_cluster_status()
    active_nodes = [n for n in status if n["available"]]
    return {
        "active_nodes": len(active_nodes),
        "down_nodes": len(status) - len(active_nodes),
        "recent_transactions": len(cluster.get_recent_transactions(10)),
        "status": status,
    }


if __name__ == "__main__":
    print("=== LOAD TEST ===")
    print(run_load_test(workers=8, events_per_worker=80))
    print("=== FAILOVER TEST ===")
    print(run_failover_test())

