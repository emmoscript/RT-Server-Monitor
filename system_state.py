import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


STATE_FILE = Path(__file__).with_name("system_state.json")
# Bloqueo para escrituras concurrentes (varios threads actualizando estado).
_state_lock = threading.Lock()


def _default_state() -> Dict[str, Any]:
    """Estructura mínima de estado global."""
    return {
        "servers": {},        # server_id -> {...}
        "last_update": 0.0,
        "alerts": [],         # lista de strings legibles
    }


def load_state() -> Dict[str, Any]:
    """Carga el estado actual desde disco para el dashboard."""
    if not STATE_FILE.exists():
        return _default_state()

    try:
        raw = STATE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return _default_state()
        return data
    except (OSError, json.JSONDecodeError):
        # Si algo va mal leyendo el archivo, devolvemos un estado limpio.
        return _default_state()


def update_server_state(
    server_id: str,
    metrics: Optional[Dict[str, Any]] = None,
    alerts: Optional[List[str]] = None,
    online: Optional[bool] = None,
    error: Optional[str] = None,
) -> None:
    """
    Actualiza el estado global de un servidor concreto y lo persiste en disco.

    Thread-safe: usa un lock para que varios threads puedan actualizar
    distintos servidores sin corromper el JSON.
    """
    with _state_lock:
        _update_server_state_unsafe(server_id, metrics, alerts, online, error)


def _update_server_state_unsafe(
    server_id: str,
    metrics: Optional[Dict[str, Any]] = None,
    alerts: Optional[List[str]] = None,
    online: Optional[bool] = None,
    error: Optional[str] = None,
) -> None:
    """Actualiza estado y persiste en disco. Debe llamarse con _state_lock adquirido."""
    state = load_state()
    servers: Dict[str, Any] = state.setdefault("servers", {})

    server_state: Dict[str, Any] = servers.get(
        server_id,
        {
            "server_id": server_id,
            "cpu": None,
            "memory": None,
            "temperature": None,
            "online": False,
            "last_update": 0.0,
            "alerts": [],
            "last_error": None,
        },
    )

    # Actualizar métricas si se proporcionan
    if metrics is not None:
        server_state["cpu"] = metrics.get("cpu")
        server_state["memory"] = metrics.get("memory")
        server_state["temperature"] = metrics.get("temperature")

    # Actualizar estado online/offline
    if online is not None:
        server_state["online"] = online

    # Actualizar alertas por servidor
    if alerts is not None:
        server_state["alerts"] = alerts

        # Añadir también a la lista global de alertas para el panel
        global_alerts: List[str] = state.setdefault("alerts", [])
        for msg in alerts:
            readable = f"{server_id}: {msg}"
            global_alerts.append(readable)

    # Registrar último error conocido
    if error is not None:
        server_state["last_error"] = error

    now = time.time()
    server_state["last_update"] = now
    state["last_update"] = now
    servers[server_id] = server_state

    # Persistir en disco para que el dashboard lo lea.
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

