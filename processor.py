from typing import Dict, Any, List

from exceptions import ProcessingException


class Processor:
    """
    Analiza las métricas recibidas y detecta anomalías.

    Devuelve una lista de mensajes de alerta (strings) en caso de anomalía.
    También puede lanzar ProcessingException ante errores lógicos internos.
    """

    def __init__(
        self,
        cpu_threshold: float = 85.0,
        memory_threshold: float = 90.0,
        temp_threshold: float = 80.0,
    ) -> None:
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.temp_threshold = temp_threshold

    def process(self, server_id: str, metrics: Dict[str, Any]) -> List[str]:
        """
        Procesa las métricas de un servidor y devuelve alertas detectadas.

        :raises ProcessingException: Si ocurre un error inesperado durante el análisis.
        """
        try:
            alerts: List[str] = []

            cpu = float(metrics["cpu"])
            memory = float(metrics["memory"])
            temperature = float(metrics["temperature"])

            if cpu > self.cpu_threshold:
                alerts.append(
                    f"CPU alta en {server_id}: {cpu:.1f}% (umbral {self.cpu_threshold}%)"
                )

            if memory > self.memory_threshold:
                alerts.append(
                    f"Memoria alta en {server_id}: {memory:.1f}% (umbral {self.memory_threshold}%)"
                )

            if temperature > self.temp_threshold:
                alerts.append(
                    f"Temperatura alta en {server_id}: {temperature:.1f}°C (umbral {self.temp_threshold}°C)"
                )

            return alerts
        except Exception as exc:  # noqa: BLE001 - intencional para encapsular errores de procesamiento
            raise ProcessingException(
                f"Error procesando métricas de {server_id}: {exc}"
            ) from exc

