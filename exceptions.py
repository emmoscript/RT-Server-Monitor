class ServerOfflineException(Exception):
    """Señala que el servidor está desconectado o no responde."""


class InvalidMetricException(Exception):
    """Señala que las métricas recibidas del servidor son inválidas o corruptas."""


class ProcessingException(Exception):
    """Señala un error durante el procesamiento de las métricas."""

