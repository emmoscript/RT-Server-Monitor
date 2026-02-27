import logging

from alert import AlertManager
from orchestrator import Orchestrator
from processor import Processor
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
    Construye la instancia del sistema RT-Monitor.

    Esta función centraliza la creación de componentes y sirve como punto
    de entrada claro para futuras extensiones (threads, mutex, etc.).
    """
    servers = [
        Server("server-1", failure_rate=0.15, invalid_data_rate=0.08),
        Server("server-2", failure_rate=0.10, invalid_data_rate=0.05),
        Server("server-3", failure_rate=0.05, invalid_data_rate=0.03),
    ]

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
    Punto de entrada para la demostración de la Semana 9.

    Se ejecutan un número finito de iteraciones para que el programa sea fácil de probar.
    Para simular un sistema "permanente" se puede cambiar iterations=None en el run().
    """
    configure_logging()

    orchestrator = build_system()

    # Monitoreo continuo: se detiene solo manualmente (Ctrl+C).
    orchestrator.run(iterations=None, delay_seconds=1.0)


if __name__ == "__main__":
    main()

