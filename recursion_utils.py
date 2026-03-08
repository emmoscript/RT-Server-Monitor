"""
Algoritmo recursivo para RT-Monitor: profundidad de dependencias entre servidores.

En un sistema real, un servidor puede depender de otros (ej.: un API depende de
una base de datos). La profundidad de dependencia indica cuántos "niveles"
hay hasta llegar a un servidor que no depende de nadie.

Se usa recursión real: la profundidad de un servidor es 1 + el máximo de las
profundidades de sus dependencias (caso base: 0 si no tiene dependencias).
"""

from typing import Dict, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from server import Server


def get_dependency_depth(
    server_id: str,
    servers_by_id: Dict[str, "Server"],
    visited: Set[str] | None = None,
) -> int:
    """
    Calcula la profundidad de dependencia de un servidor de forma recursiva.

    La profundidad es el número de niveles en la cadena de dependencias:
    - Si el servidor no depende de nadie (depends_on vacío), profundidad = 0.
    - Si depende de otros, profundidad = 1 + max(profundidad de cada dependencia).

    Se evitan ciclos usando el conjunto `visited`; si se detecta ciclo se retorna 0
    para no entrar en recursión infinita.

    :param server_id: ID del servidor del que calcular la profundidad.
    :param servers_by_id: Diccionario server_id -> instancia de Server (con depends_on).
    :param visited: Conjunto de server_id ya visitados en esta rama (detección de ciclos).
    :return: Profundidad de dependencia (entero >= 0).
    """
    if visited is None:
        visited = set()

    # Evitar ciclos en el grafo de dependencias.
    if server_id in visited:
        return 0
    visited.add(server_id)

    server = servers_by_id.get(server_id)
    if not server or not server.depends_on:
        return 0

    # Caso recursivo: 1 + máximo de las profundidades de las dependencias.
    max_child_depth = 0
    for dep_id in server.depends_on:
        child_depth = get_dependency_depth(dep_id, servers_by_id, visited.copy())
        if child_depth > max_child_depth:
            max_child_depth = child_depth

    return 1 + max_child_depth
