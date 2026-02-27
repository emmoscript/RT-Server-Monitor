"""
Dashboard web para RT-Monitor usando Streamlit.

Arquitectura:
Servidores → Orquestador → system_state.json → Dashboard Streamlit

El dashboard solo observa el estado del sistema; no modifica la simulación.
Ejecuta en otra terminal:

    streamlit run dashboard_streamlit.py
"""

from pathlib import Path
from datetime import datetime
import time

import streamlit as st

from system_state import load_state


LOG_FILE = Path(__file__).with_name("rt_monitor.log")


def _format_ts(ts):
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


def render_sidebar():
    """Barra lateral con controles de refresco y filtros."""
    st.sidebar.title("RT-Monitor")
    st.sidebar.markdown("### Controles")

    auto_refresh = st.sidebar.checkbox("Auto-actualizar", value=True)
    interval = st.sidebar.slider("Intervalo (segundos)", 0.5, 10.0, 1.0, 0.5)

    st.sidebar.markdown("### Filtro de servidores")
    filter_mode = st.sidebar.radio(
        "Mostrar",
        options=["Todos", "Solo con alertas", "Solo OFFLINE"],
        index=0,
    )

    return auto_refresh, interval, filter_mode


def render_summary(servers, alerts):
    total = len(servers)
    online = sum(1 for s in servers.values() if s.get("online"))
    offline = total - online
    alert_count = len(alerts)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Servidores totales", total)
    col2.metric("Online", online)
    col3.metric("Offline", offline)
    col4.metric("Alertas activas", alert_count)


def render_servers(servers, filter_mode):
    st.subheader("Estado de servidores")

    if not servers:
        st.info(
            "Aún no hay datos en el estado global. "
            "Asegúrate de estar ejecutando la simulación (`main.py`)."
        )
        return

    for server_id in sorted(servers.keys()):
        info = servers[server_id]
        cpu = info.get("cpu")
        memory = info.get("memory")
        temperature = info.get("temperature")
        online = bool(info.get("online"))
        server_alerts = info.get("alerts") or []
        last_error = info.get("last_error")
        last_update = info.get("last_update")

        has_alert = bool(server_alerts)

        # Aplicar filtros
        if filter_mode == "Solo con alertas" and not has_alert:
            continue
        if filter_mode == "Solo OFFLINE" and online:
            continue

        status = "ONLINE" if online else "OFFLINE"
        status_icon = "🟢" if online else "❌"

        card = st.container()
        with card:
            top_cols = st.columns([2, 2, 2, 2])
            top_cols[0].markdown(f"**{server_id}**")
            top_cols[1].markdown(f"**Estado:** {status_icon} {status}")
            top_cols[2].markdown(f"**Última actualización:** {_format_ts(last_update)}")
            if last_error:
                top_cols[3].markdown(f"**Último error:** `{last_error}`")

            # Métricas con estilo profesional
            m1, m2, m3 = st.columns(3)

            cpu_val = cpu if isinstance(cpu, (int, float)) else None
            mem_val = memory if isinstance(memory, (int, float)) else None
            temp_val = temperature if isinstance(temperature, (int, float)) else None

            m1.metric("CPU (%)", f"{cpu_val:.1f}" if cpu_val is not None else "-")
            m2.metric("Memoria (%)", f"{mem_val:.1f}" if mem_val is not None else "-")
            m3.metric("Temp (°C)", f"{temp_val:.1f}" if temp_val is not None else "-")

            # Barras de progreso para visualización rápida
            if cpu_val is not None:
                st.progress(min(cpu_val / 100.0, 1.0), text="Uso CPU")
            if mem_val is not None:
                st.progress(min(mem_val / 100.0, 1.0), text="Uso Memoria")

            if server_alerts:
                st.markdown("**Alertas de este servidor:**")
                for a in server_alerts[-5:]:
                    st.markdown(f"- ⚠ {a}")

        st.markdown("---")


def render_alerts_and_logs(alerts):
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Alertas recientes")
        if alerts:
            for a in alerts[-50:]:
                st.markdown(f"- ⚠ {a}")
        else:
            st.write("Sin alertas registradas recientemente.")

    with col_right:
        st.subheader("Logs recientes")
        if LOG_FILE.exists():
            content = LOG_FILE.read_text(encoding="utf-8")
            lines = content.splitlines()
            last_lines = "\n".join(lines[-100:])
            st.text(last_lines)
        else:
            st.write(
                "El archivo de log aún no existe. "
                "Se creará automáticamente al ejecutar `main.py`."
            )


def main() -> None:
    st.set_page_config(page_title="RT-Monitor Dashboard", layout="wide")

    auto_refresh, interval, filter_mode = render_sidebar()

    st.title("RT-Monitor Dashboard")
    st.caption("Monitoreo de infraestructura en tiempo real con orquestador y excepciones.")

    state = load_state()
    servers = state.get("servers", {})
    alerts = state.get("alerts", [])

    render_summary(servers, alerts)
    st.markdown("---")
    render_servers(servers, filter_mode)
    st.markdown("---")
    render_alerts_and_logs(alerts)

    last_update = state.get("last_update")
    st.caption(f"Última actualización global: {_format_ts(last_update)}")

    # Auto-refresh sencillo en “tiempo real”
    if auto_refresh:
        time.sleep(interval)
        # Para versiones recientes de Streamlit
        st.rerun()


if __name__ == "__main__":
    main()

