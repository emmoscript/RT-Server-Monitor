import logging
import threading
import time
from typing import Iterable

from exceptions import ServerOfflineException, InvalidMetricException, ProcessingException
from server import Server
from processor import Processor
from alert import AlertManager
from system_state import update_server_state


class Orchestrator:
    """
    Orquestador / Event Manager.

    Coordina la ejecución concurrente: cada servidor se ejecuta en su propio
    thread. El orquestador lanza los threads y maneja la señal de parada (Ctrl+C).
    """

    def __init__(
        self,
        servers: Iterable[Server],
        processor: Processor,
        alert_manager: AlertManager,
        logger: logging.Logger | None = None,
    ) -> None:
        self.servers = list(servers)
        self.processor = processor
        self.alert_manager = alert_manager
        self.logger = logger or logging.getLogger("rt_monitor.orchestrator")
        self._stop_event = threading.Event()

    def run(self, iterations: int | None = None, delay_seconds: float = 1.0) -> None:
        """
        Ejecuta el monitoreo de forma concurrente: un thread por servidor.

        Cada thread ejecuta ciclos de lectura → procesamiento → alertas → estado
        para su servidor, con delay_seconds entre ciclos. El orquestador espera
        hasta recibir Ctrl+C y entonces detiene todos los threads.

        :param iterations: Si es un entero, cada thread hace como máximo ese número
            de ciclos; si es None, corre hasta que se detenga con Ctrl+C.
        :param delay_seconds: Pausa entre ciclos dentro de cada thread.
        """
        self.logger.info(
            "Iniciando orquestador concurrente con %d servidores (1 thread por servidor).",
            len(self.servers),
        )
        self._stop_event.clear()

        threads = []
        for server in self.servers:
            t = threading.Thread(
                target=self._server_worker,
                args=(server, iterations, delay_seconds),
                name=f"monitor-{server.server_id}",
                daemon=False,
            )
            threads.append(t)
            t.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Señal de parada recibida; deteniendo threads...")
            self._stop_event.set()

        for t in threads:
            t.join(timeout=2.0)
        self.logger.info("Orquestador detenido.")

    def _server_worker(
        self,
        server: Server,
        iterations: int | None,
        delay_seconds: float,
    ) -> None:
        """
        Bucle que ejecuta un thread: ciclos de monitoreo para un solo servidor.
        """
        cycle = 0
        while not self._stop_event.is_set():
            if iterations is not None and cycle >= iterations:
                break
            cycle += 1
            self._handle_server_cycle(server)
            self._stop_event.wait(timeout=delay_seconds)

    def _handle_server_cycle(self, server: Server) -> None:
        """Gestiona un ciclo completo (lectura + proceso + alerta) para un servidor."""
        try:
            metrics = server.generate_metrics()
            self.logger.info("Métricas recibidas de %s: %s", server.server_id, metrics)

            alerts = self.processor.process(server.server_id, metrics)
            if alerts:
                self.alert_manager.send_alerts(server.server_id, alerts)
            else:
                self.logger.debug("Sin alertas para %s en este ciclo.", server.server_id)

            # Actualizar estado global observable por el dashboard.
            update_server_state(
                server_id=server.server_id,
                metrics=metrics,
                alerts=alerts,
                online=True,
                error=None,
            )

        except ServerOfflineException as exc:
            # Error controlado: el servidor está "caído", pero el sistema sigue.
            self.logger.error("Servidor offline: %s", exc)
            update_server_state(
                server_id=server.server_id,
                online=False,
                error=str(exc),
            )

        except InvalidMetricException as exc:
            # Datos corruptos: se registran y se continúa.
            self.logger.error("Datos inválidos: %s", exc)
            update_server_state(
                server_id=server.server_id,
                online=False,
                error=str(exc),
            )

        except ProcessingException as exc:
            # Falla en el procesamiento, se registra pero no se interrumpe el sistema.
            self.logger.error("Error de procesamiento: %s", exc)
            update_server_state(
                server_id=server.server_id,
                online=True,
                error=str(exc),
            )

        except Exception as exc:  # noqa: BLE001 - captura global intencional
            # Cualquier otro error inesperado también se maneja para preservar la ejecución.
            self.logger.exception("Error inesperado manejado por el orquestador: %s", exc)
            update_server_state(
                server_id=server.server_id,
                online=False,
                error=str(exc),
            )

