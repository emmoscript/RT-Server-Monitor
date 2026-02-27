import logging
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

    Se encarga de:
    - leer métricas de varios servidores,
    - delegar el análisis al Processor,
    - delegar notificaciones al AlertManager,
    - manejar excepciones sin detener el sistema.
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

    def run(self, iterations: int | None = None, delay_seconds: float = 1.0) -> None:
        """
        Ejecuta el ciclo principal de monitoreo.

        :param iterations: Número de ciclos de monitoreo. Si es None, corre indefinidamente.
        :param delay_seconds: Tiempo de espera entre ciclos (simulación de tiempo real).
        """
        cycle = 0
        self.logger.info(
            "Iniciando orquestador con %d servidores. Iteraciones=%s",
            len(self.servers),
            "inf" if iterations is None else iterations,
        )

        try:
            while iterations is None or cycle < iterations:
                cycle += 1
                self.logger.debug("Ciclo de monitoreo #%d", cycle)

                for server in self.servers:
                    self._handle_server_cycle(server)

                time.sleep(delay_seconds)
        except KeyboardInterrupt:
            # Permite detener el sistema manualmente sin stacktrace ruidoso.
            self.logger.info("Ejecución interrumpida manualmente por el usuario.")

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

