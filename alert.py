from typing import List
import logging


class AlertManager:
    """
    Encargado de notificar situaciones críticas.

    Por ahora solo escribe en el log. En futuras iteraciones podría enviar correos,
    mensajes a Slack, dashboards, etc.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("rt_monitor.alerts")

    def send_alerts(self, server_id: str, alerts: List[str]) -> None:
        """Registra una o varias alertas asociadas a un servidor."""
        for msg in alerts:
            self._logger.warning("[ALERTA] %s | %s", server_id, msg)

