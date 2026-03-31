import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List


class DatabaseNode:
    """Representa un nodo de base de datos (simulado con JSON en disco)."""

    def __init__(self, node_id: str, base_dir: Path) -> None:
        self.node_id = node_id
        self.file_path = base_dir / f"db_{node_id}.json"
        self.is_available = True
        self._lock = threading.Lock()
        self._initialize_if_needed()

    def _initialize_if_needed(self) -> None:
        if not self.file_path.exists():
            self.write_data(
                {
                    "node_id": self.node_id,
                    "last_updated": 0.0,
                    "servers": {},
                    "metrics_events": [],
                    "alerts_events": [],
                    "tx_log": [],
                }
            )

    def read_data(self) -> Dict[str, Any]:
        with self._lock:
            try:
                raw = self.file_path.read_text(encoding="utf-8")
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
            return {
                "node_id": self.node_id,
                "last_updated": 0.0,
                "servers": {},
                "metrics_events": [],
                "alerts_events": [],
                "tx_log": [],
            }

    def write_data(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self.file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


class RealtimeDatabaseCluster:
    """
    Cluster de base de datos distribuida (simulada):
    - 1 nodo primario
    - 2 réplicas
    - replicación síncrona en nodos disponibles
    """

    def __init__(self, base_dir: str = "db_data") -> None:
        self.base_path = Path(__file__).with_name(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.nodes: Dict[str, DatabaseNode] = {
            "node_a": DatabaseNode("node_a", self.base_path),
            "node_b": DatabaseNode("node_b", self.base_path),
            "node_c": DatabaseNode("node_c", self.base_path),
        }
        self.primary_node_id = "node_a"
        self._cluster_lock = threading.Lock()

    def set_node_availability(self, node_id: str, is_available: bool) -> None:
        node = self.nodes.get(node_id)
        if node:
            node.is_available = is_available

    def get_cluster_status(self) -> List[Dict[str, Any]]:
        status = []
        for node_id, node in self.nodes.items():
            data = node.read_data()
            status.append(
                {
                    "node_id": node_id,
                    "role": "primary" if node_id == self.primary_node_id else "replica",
                    "available": node.is_available,
                    "last_updated": data.get("last_updated", 0.0),
                    "tx_count": len(data.get("tx_log", [])),
                }
            )
        return status

    def get_recent_transactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        primary = self.nodes[self.primary_node_id]
        tx_log = primary.read_data().get("tx_log", [])
        return tx_log[-limit:]

    def persist_server_event(
        self,
        server_id: str,
        metrics: Dict[str, Any] | None,
        alerts: List[str],
        online: bool,
        error: str | None,
    ) -> None:
        """Persiste evento de monitoreo y replica en nodos disponibles."""
        tx = {
            "tx_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "type": "upsert_server_state",
            "server_id": server_id,
            "payload": {
                "metrics": metrics,
                "alerts": alerts,
                "online": online,
                "error": error,
            },
            "status": "committed",
        }
        self._replicate_transaction(tx)

    def _choose_write_node(self) -> DatabaseNode | None:
        primary = self.nodes.get(self.primary_node_id)
        if primary and primary.is_available:
            return primary
        for node in self.nodes.values():
            if node.is_available:
                return node
        return None

    def _replicate_transaction(self, tx: Dict[str, Any]) -> None:
        with self._cluster_lock:
            writer = self._choose_write_node()
            if writer is None:
                return

            for node in self.nodes.values():
                if not node.is_available:
                    continue
                self._apply_tx_on_node(node, tx)

    def _apply_tx_on_node(self, node: DatabaseNode, tx: Dict[str, Any]) -> None:
        data = node.read_data()
        payload = tx.get("payload", {})
        server_id = tx.get("server_id", "unknown")
        metrics = payload.get("metrics")
        alerts = payload.get("alerts", [])
        online = bool(payload.get("online", False))
        error = payload.get("error")

        servers: Dict[str, Any] = data.setdefault("servers", {})
        server_state = servers.get(
            server_id,
            {
                "server_id": server_id,
                "cpu": None,
                "memory": None,
                "temperature": None,
                "online": False,
                "last_error": None,
                "last_update": 0.0,
                "alerts": [],
            },
        )

        if metrics:
            server_state["cpu"] = metrics.get("cpu")
            server_state["memory"] = metrics.get("memory")
            server_state["temperature"] = metrics.get("temperature")
            server_state["metrics_source"] = metrics.get("source", "simulated")

            metrics_events = data.setdefault("metrics_events", [])
            metrics_events.append(
                {
                    "server_id": server_id,
                    "timestamp": tx["timestamp"],
                    "metrics": metrics,
                }
            )

        server_state["online"] = online
        server_state["last_error"] = error
        server_state["last_update"] = tx["timestamp"]
        server_state["alerts"] = alerts
        servers[server_id] = server_state

        if alerts:
            alerts_events = data.setdefault("alerts_events", [])
            for alert in alerts:
                alerts_events.append(
                    {
                        "server_id": server_id,
                        "timestamp": tx["timestamp"],
                        "message": alert,
                    }
                )

        tx_log = data.setdefault("tx_log", [])
        tx_log.append(tx)
        data["last_updated"] = tx["timestamp"]
        node.write_data(data)

