"""
Dashboard web para RT-Monitor (Streamlit).

Ejecuta: streamlit run dashboard_streamlit.py
"""

from pathlib import Path
from datetime import datetime
import time

import streamlit as st
import pandas as pd

from realtime_database import RealtimeDatabaseCluster
from system_state import load_state

PRIMARY_SERVER_ID = "server-1"

LOG_FILE = Path(__file__).with_name("rt_monitor.log")
DB_CLUSTER = RealtimeDatabaseCluster()


def _inject_ops_theme() -> None:
    st.markdown(
        """
        <style>
        .main .block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1280px; }
        h1 { font-weight: 700; letter-spacing: -0.02em; color: #0f172a; }
        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.65rem 0.85rem;
        }
        div[data-testid="stMetric"] label {
            color: #64748b !important;
            font-size: 0.75rem !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .section-label {
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #94a3b8;
            margin: 0.5rem 0 0.75rem 0;
        }
        .badge-primary {
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            color: #0369a1;
            background: #e0f2fe;
            padding: 0.25rem 0.55rem;
            border-radius: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_ts(ts):
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "—"


def render_sidebar():
    st.sidebar.markdown("### RT-Monitor")
    st.sidebar.caption("Operations · Live view")

    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    interval = st.sidebar.slider("Intervalo (s)", 0.5, 10.0, 1.0, 0.5)

    st.sidebar.markdown("---")
    filter_mode = st.sidebar.radio(
        "Vista",
        options=["Todos", "Solo con alertas", "Solo OFFLINE"],
        index=0,
    )

    return auto_refresh, interval, filter_mode


def _server_passes_filter(has_alert: bool, online: bool, filter_mode: str) -> bool:
    if filter_mode == "Solo con alertas" and not has_alert:
        return False
    if filter_mode == "Solo OFFLINE" and online:
        return False
    return True


def _render_node_metrics(cpu, memory, temperature, online, last_update, last_error, server_alerts):
    status_label = "Operational" if online else "Down"
    cap = f"Estado: {status_label} · Última lectura: {_format_ts(last_update)}"
    if last_error:
        cap += f" · Incidente: {last_error}"
    st.caption(cap)

    c1, c2, c3 = st.columns(3)
    cpu_val = cpu if isinstance(cpu, (int, float)) else None
    mem_val = memory if isinstance(memory, (int, float)) else None
    temp_val = temperature if isinstance(temperature, (int, float)) else None

    c1.metric("CPU", f"{cpu_val:.1f} %" if cpu_val is not None else "—")
    c2.metric("Memoria", f"{mem_val:.1f} %" if mem_val is not None else "—")
    c3.metric("Temperatura", f"{temp_val:.1f} °C" if temp_val is not None else "—")

    if cpu_val is not None:
        st.progress(min(cpu_val / 100.0, 1.0), text="CPU")
    if mem_val is not None:
        st.progress(min(mem_val / 100.0, 1.0), text="Memoria")

    if server_alerts:
        st.markdown("**Alertas**")
        for a in server_alerts[-8:]:
            st.markdown(f"· {a}")


def render_kpis(servers, alerts):
    total = len(servers)
    online = sum(1 for s in servers.values() if s.get("online"))
    offline = total - online
    alert_count = len(alerts)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nodos", total)
    c2.metric("Operativos", online)
    c3.metric("No disponibles", offline)
    c4.metric("Alertas", alert_count)


def render_infrastructure(servers: dict, filter_mode: str) -> None:
    st.markdown('<p class="section-label">Infraestructura</p>', unsafe_allow_html=True)

    if not servers:
        st.info("Sin telemetría. Ejecuta `python main.py` para iniciar el orquestador.")
        return

    primary_info = servers.get(PRIMARY_SERVER_ID)
    other_ids = [sid for sid in sorted(servers.keys()) if sid != PRIMARY_SERVER_ID]

    if primary_info is not None:
        online = bool(primary_info.get("online"))
        server_alerts = primary_info.get("alerts") or []
        has_alert = bool(server_alerts)
        if _server_passes_filter(has_alert, online, filter_mode):
            with st.container(border=True):
                h1, h2 = st.columns([4, 1])
                with h1:
                    st.markdown(f"#### `{PRIMARY_SERVER_ID}`")
                with h2:
                    st.markdown(
                        '<span class="badge-primary">PRIMARY</span>',
                        unsafe_allow_html=True,
                    )
                _render_node_metrics(
                    primary_info.get("cpu"),
                    primary_info.get("memory"),
                    primary_info.get("temperature"),
                    online,
                    primary_info.get("last_update"),
                    primary_info.get("last_error"),
                    server_alerts,
                )

    if other_ids:
        st.markdown('<p class="section-label">Nodos adicionales</p>', unsafe_allow_html=True)
        cols = st.columns(len(other_ids))
        for col, sid in zip(cols, other_ids):
            info = servers[sid]
            online = bool(info.get("online"))
            server_alerts = info.get("alerts") or []
            has_alert = bool(server_alerts)
            if not _server_passes_filter(has_alert, online, filter_mode):
                continue
            with col:
                with st.container(border=True):
                    st.markdown(f"#### `{sid}`")
                    _render_node_metrics(
                        info.get("cpu"),
                        info.get("memory"),
                        info.get("temperature"),
                        online,
                        info.get("last_update"),
                        info.get("last_error"),
                        server_alerts,
                    )


def render_alerts_and_logs(alerts):
    st.markdown('<p class="section-label">Alertas y registros</p>', unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1])

    with col_left:
        if alerts:
            df_a = pd.DataFrame({"Evento": alerts[-80:]})
            st.dataframe(df_a, use_container_width=True, height=280, hide_index=True)
        else:
            st.caption("Sin alertas en la ventana actual.")

    with col_right:
        if LOG_FILE.exists():
            content = LOG_FILE.read_text(encoding="utf-8")
            lines = content.splitlines()[-120:]
            st.text_area(
                "Registro",
                value="\n".join(lines),
                height=280,
                disabled=True,
                label_visibility="collapsed",
            )
        else:
            st.caption("El archivo de registro se creará al ejecutar `main.py`.")


def render_database_panel() -> None:
    st.markdown('<p class="section-label">Almacén de datos</p>', unsafe_allow_html=True)
    status = DB_CLUSTER.get_cluster_status()
    txs = DB_CLUSTER.get_recent_transactions(limit=20)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if status:
            st.dataframe(pd.DataFrame(status), use_container_width=True, hide_index=True)
        else:
            st.caption("Sin estado de nodos.")
    with col_b:
        if txs:
            rows = [
                {
                    "ID": str(tx.get("tx_id", ""))[:8],
                    "Nodo": tx.get("server_id"),
                    "Tipo": tx.get("type"),
                    "Hora": _format_ts(tx.get("timestamp")),
                    "Estado": tx.get("status"),
                }
                for tx in txs
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("Sin transacciones recientes.")


def main() -> None:
    st.set_page_config(
        page_title="RT-Monitor · Operations",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_ops_theme()

    auto_refresh, interval, filter_mode = render_sidebar()

    st.title("RT-Monitor")
    st.caption("Centro de operaciones · Telemetría en tiempo real")

    state = load_state()
    servers = state.get("servers", {})
    alerts = state.get("alerts", [])

    render_kpis(servers, alerts)
    st.markdown("---")
    render_infrastructure(servers, filter_mode)
    st.markdown("---")
    render_alerts_and_logs(alerts)
    st.markdown("---")
    render_database_panel()

    last_update = state.get("last_update")
    st.caption(f"Sincronizado · {_format_ts(last_update)}")

    if auto_refresh:
        time.sleep(interval)
        st.rerun()


if __name__ == "__main__":
    main()
