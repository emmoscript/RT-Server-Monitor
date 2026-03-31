import logging

from alert import AlertManager
from orchestrator import Orchestrator
from processor import Processor
from realtime_database import RealtimeDatabaseCluster
from recursion_utils import get_dependency_depth
from server import Server

try:
    import psutil  # noqa: F401
except ImportError:
    psutil = None


def configure_logging() -> None:
    """
    Configura logging para consola y archivo.

    El archivo de log será leído por el dashboard Streamlit para mostrar
    eventos en “tiempo real”.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("rt_monitor.log", encoding="utf-8"),
        ],
    )


def build_system() -> Orchestrator:
    """
    Construye la instancia del sistema RT-Monitor con concurrencia (threads)
    y dependencias entre servidores para el algoritmo recursivo.
    """
    # server-1 = nodo principal: métricas reales de esta PC (psutil) si está instalado.
    # server-2 y server-3 siguen simulados (aleatorio + fallos simulados).
    servers = [
        Server(
            "server-1",
            failure_rate=0.0,
            invalid_data_rate=0.0,
            depends_on=["server-2"],
            use_host_metrics=True,
        ),
        Server(
            "server-2",
            failure_rate=0.10,
            invalid_data_rate=0.05,
            depends_on=["server-3"],
        ),
        Server(
            "server-3",
            failure_rate=0.05,
            invalid_data_rate=0.03,
            depends_on=[],
        ),
    ]
    servers_by_id = {s.server_id: s for s in servers}

    log = logging.getLogger("rt_monitor.main")
    if psutil is None:
        log.warning(
            "psutil no está instalado: el servidor principal usará simulación aleatoria. "
            "Para métricas reales de tu equipo: pip install psutil"
        )
    else:
        log.info("Servidor principal (server-1) usa métricas reales del host (CPU/RAM) vía psutil.")

    # Mostrar profundidad de dependencias (algoritmo recursivo) al arrancar.
    for s in servers:
        depth = get_dependency_depth(s.server_id, servers_by_id)
        log.info(
            "Profundidad de dependencias de %s: %d (depends_on=%s)",
            s.server_id,
            depth,
            s.depends_on,
        )

    processor = Processor(
        cpu_threshold=85.0,
        memory_threshold=90.0,
        temp_threshold=80.0,
    )

    alert_manager = AlertManager()
    database_cluster = RealtimeDatabaseCluster()
    # Simular fallo de una réplica para demostrar alta disponibilidad.
    database_cluster.set_node_availability("node_c", False)

    orchestrator = Orchestrator(
        servers=servers,
        processor=processor,
        alert_manager=alert_manager,
        database_cluster=database_cluster,
        logger=logging.getLogger("rt_monitor.orchestrator"),
    )

    return orchestrator


def main() -> None:
    """
    Punto de entrada. Ejecuta el monitoreo concurrente (Semana 10:
    un thread por servidor). Se detiene con Ctrl+C.
    """
    configure_logging()

    orchestrator = build_system()

    # Monitoreo continuo: se detiene solo manualmente (Ctrl+C).
    orchestrator.run(iterations=None, delay_seconds=1.0)


if __name__ == "__main__":
    main()

