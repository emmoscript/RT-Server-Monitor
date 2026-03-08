import logging

from alert import AlertManager
from orchestrator import Orchestrator
from processor import Processor
from recursion_utils import get_dependency_depth
from server import Server


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
    # server-1 depende de server-2, server-2 de server-3; server-3 no depende de nadie.
    servers = [
        Server(
            "server-1",
            failure_rate=0.15,
            invalid_data_rate=0.08,
            depends_on=["server-2"],
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

    # Mostrar profundidad de dependencias (algoritmo recursivo) al arrancar.
    log = logging.getLogger("rt_monitor.main")
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

    orchestrator = Orchestrator(
        servers=servers,
        processor=processor,
        alert_manager=alert_manager,
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

