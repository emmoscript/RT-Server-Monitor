import random
from collections import deque
from typing import Dict, Any, List, Optional

from exceptions import ServerOfflineException, InvalidMetricException

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None  # type: ignore


class Server:
    """
    Simulador de servidor que genera métricas periódicamente.

    Pensado para ejecutarse en un thread propio; el orquestador coordina
    varios servidores de forma concurrente.
    """

    def __init__(
        self,
        server_id: str,
        failure_rate: float = 0.1,
        invalid_data_rate: float = 0.05,
        depends_on: Optional[List[str]] = None,
        use_host_metrics: bool = False,
    ) -> None:
        """
        :param server_id: Identificador lógico del servidor.
        :param failure_rate: Probabilidad de que el servidor esté "offline" en un ciclo.
        :param invalid_data_rate: Probabilidad de enviar datos corruptos/invalidos.
        :param depends_on: Lista de server_id de los que este servidor "depende"
            (para el algoritmo recursivo de profundidad de dependencias).
        :param use_host_metrics: Si True, CPU y memoria salen de esta máquina (psutil).
            Temperatura: sensores del SO si existen; si no, estimación a partir de la carga de CPU.
            Requiere ``pip install psutil``. Si no está instalado, se cae a simulación aleatoria.
        """
        self.server_id = server_id
        self.failure_rate = failure_rate
        self.invalid_data_rate = invalid_data_rate
        self.depends_on = depends_on or []
        self.use_host_metrics = bool(use_host_metrics and psutil is not None)
        # Suavizado de CPU (varias muestras) para acercarse al comportamiento del Administrador de tareas.
        self._cpu_smooth_window: deque[float] | None = (
            deque(maxlen=5) if self.use_host_metrics else None
        )

    def generate_metrics(self) -> Dict[str, Any]:
        """
        Genera métricas (simuladas o, si use_host_metrics, del equipo local vía psutil).

        Puede lanzar:
        - ServerOfflineException: si el servidor se considera desconectado.
        - InvalidMetricException: si se generan datos corruptos/adulterados.
        """
        # Simular servidor offline
        if random.random() < self.failure_rate:
            raise ServerOfflineException(f"Servidor {self.server_id} no responde (simulado).")

        if self.use_host_metrics:
            metrics = self._metrics_from_host()
        else:
            metrics = {
                "cpu": random.uniform(0, 100),       # porcentaje
                "memory": random.uniform(0, 100),    # porcentaje
                "temperature": random.uniform(20, 90),  # grados Celsius
                "online": True,
                "source": "simulated",
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

    def _metrics_from_host(self) -> Dict[str, Any]:
        """CPU y RAM reales de esta máquina; temperatura de sensores o estimación por carga."""
        assert psutil is not None
        assert self._cpu_smooth_window is not None
        # Ventana ~0.5 s por muestra (similar a muchos monitores del SO). El Administrador de tareas
        # usa su propio suavizado y frecuencia de actualización; no coincidirá al decimal.
        sample = float(psutil.cpu_percent(interval=0.5))
        self._cpu_smooth_window.append(sample)
        cpu = sum(self._cpu_smooth_window) / len(self._cpu_smooth_window)
        mem = float(psutil.virtual_memory().percent)
        temp = self._host_temperature_estimate(cpu)

        return {
            "cpu": round(cpu, 1),
            "memory": round(mem, 1),
            "temperature": temp,
            "online": True,
            "source": "host",
        }

    @staticmethod
    def _host_temperature_estimate(cpu_percent: float) -> float:
        """
        Intenta leer sensores del SO; si no hay, estima una temperatura plausible
        a partir del uso de CPU (no es un sensor físico).
        """
        if psutil is None:
            return 40.0
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for e in entries:
                        if e.current is not None:
                            return float(e.current)
        except (AttributeError, NotImplementedError, RuntimeError):
            pass
        # Windows suele no exponer sensores vía psutil: curva aproximada 35–85 °C según carga
        return round(35.0 + (cpu_percent / 100.0) * 50.0, 1)

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

