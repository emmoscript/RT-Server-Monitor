import random
from typing import Dict, Any

from exceptions import ServerOfflineException, InvalidMetricException


class Server:
    """
    Simulador de servidor que genera métricas periódicamente.

    Esta clase está pensada para ser usada por el orquestador en un bucle
    (o en hilos en semanas posteriores).
    """

    def __init__(self, server_id: str, failure_rate: float = 0.1, invalid_data_rate: float = 0.05) -> None:
        """
        :param server_id: Identificador lógico del servidor.
        :param failure_rate: Probabilidad de que el servidor esté "offline" en un ciclo.
        :param invalid_data_rate: Probabilidad de enviar datos corruptos/invalidos.
        """
        self.server_id = server_id
        self.failure_rate = failure_rate
        self.invalid_data_rate = invalid_data_rate

    def generate_metrics(self) -> Dict[str, Any]:
        """
        Genera métricas simuladas.

        Puede lanzar:
        - ServerOfflineException: si el servidor se considera desconectado.
        - InvalidMetricException: si se generan datos corruptos/adulterados.
        """
        # Simular servidor offline
        if random.random() < self.failure_rate:
            raise ServerOfflineException(f"Servidor {self.server_id} no responde (simulado).")

        # Métricas base "válidas"
        metrics = {
            "cpu": random.uniform(0, 100),       # porcentaje
            "memory": random.uniform(0, 100),    # porcentaje
            "temperature": random.uniform(20, 90),  # grados Celsius
            "online": True,
        }

        # Simular datos inválidos
        if random.random() < self.invalid_data_rate:
            # Por ejemplo, valor fuera de rango o tipo incorrecto
            choice = random.choice(["cpu_out_of_range", "temp_negative", "wrong_type"])
            if choice == "cpu_out_of_range":
                metrics["cpu"] = 150.0
            elif choice == "temp_negative":
                metrics["temperature"] = -10.0
            elif choice == "wrong_type":
                metrics["memory"] = "N/A"

        # Validación mínima local; si falla, generamos excepción
        if not self._validate_metrics(metrics):
            raise InvalidMetricException(f"Métricas inválidas recibidas de {self.server_id}: {metrics}")

        return metrics

    @staticmethod
    def _validate_metrics(metrics: Dict[str, Any]) -> bool:
        """Valida rango y tipos básicos de las métricas."""
        try:
            cpu = float(metrics["cpu"])
            memory = float(metrics["memory"])
            temperature = float(metrics["temperature"])
        except (KeyError, TypeError, ValueError):
            return False

        if not (0.0 <= cpu <= 100.0):
            return False
        if not (0.0 <= memory <= 100.0):
            return False
        if not (-5.0 <= temperature <= 120.0):
            return False

        return True

