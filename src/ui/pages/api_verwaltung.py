"""
REST-API Verwaltung UI-Seite
API-Keys und Zugriffsprotokolle
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.api import (
    APIService, APIBerechtigung, APIKeyStatus,
    APIKey, APILog, generiere_api_dokumentation
)


def render_api_verwaltung():
    """Rendert die API-Verwaltung-Seite"""
    st.title("🔌 REST-API Verwaltung")

    st.info("""
    Verwalten Sie API-Zugänge für externe Systeme und Integrationen.
    """)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "API-Keys", "Zugriffsprotokolle", "Statistik", "Dokumentation"
    ])

    with tab1:
        _render_api_keys()

    with tab2:
        _render_zugriffsprotokolle()

    with tab3:
        _render_statistik()

    with tab4:
        _render_dokumentation()


def _render_api_keys():
    """API-Keys verwalten"""
    st.subheader("API-Keys")

    with get_session() as db:
        service = APIService(db)

        # Neuen Key erstellen
        with st.expander("➕ Neuen API-Key erstellen"):
            bezeichnung = st.text_input("Bezeichnung", placeholder="z.B. Buchhaltungssoftware")

            berechtigungen = st.multiselect(
                "Berechtigungen",
                [b.value for b in APIBerechtigung],
                default=["LESEN"],
                format_func=lambda x: {
                    'LESEN': '👁️ Lesen',
                    'SCHREIBEN': '✏️ Schreiben',
                    'LOESCHEN': '🗑️ Löschen',
                    'ADMIN': '👑 Admin'
                }.get(x, x)
            )

            rate_limit = st.number_input(
                "Rate Limit (pro Minute)",
                min_value=1,
                max_value=1000,
                value=60
            )

            if st.button("🔑 API-Key erstellen"):
                if bezeichnung:
                    result = service.api_key_erstellen(
                        bezeichnung=bezeichnung,
                        berechtigungen=[APIBerechtigung(b) for b in berechtigungen],
                        rate_limit_pro_minute=rate_limit
                    )
                    db.commit()

                    st.success("API-Key erstellt!")

                    st.warning("""
                    **Wichtig:** Notieren Sie sich das API-Secret jetzt!
                    Es wird nur einmal angezeigt.
                    """)

                    st.code(f"API-Key: {result['api_key']}")
                    st.code(f"API-Secret: {result['api_secret']}")

                else:
                    st.error("Bitte Bezeichnung eingeben")

        st.markdown("---")

        # Vorhandene Keys
        keys = service.alle_api_keys()

        if not keys:
            st.info("Noch keine API-Keys vorhanden")
            return

        for key in keys:
            status_icon = {
                APIKeyStatus.AKTIV.value: "🟢",
                APIKeyStatus.INAKTIV.value: "⚪",
                APIKeyStatus.GESPERRT.value: "🔴",
                APIKeyStatus.ABGELAUFEN.value: "⏰"
            }.get(key.status, "⚪")

            with st.expander(f"{status_icon} {key.bezeichnung} ({key.api_key[:20]}...)"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Status:** {key.status}")
                    st.write(f"**Berechtigungen:** {', '.join(key.berechtigungen)}")
                    st.write(f"**Rate Limit:** {key.rate_limit_pro_minute}/Min")

                with col2:
                    st.write(f"**Erstellt:** {key.erstellt_am.strftime('%d.%m.%Y') if key.erstellt_am else '-'}")
                    st.write(f"**Letzter Zugriff:** {key.letzter_zugriff.strftime('%d.%m.%Y %H:%M') if key.letzter_zugriff else 'Nie'}")
                    st.write(f"**Zugriffe gesamt:** {key.zugriffe_gesamt}")

                st.code(f"API-Key: {key.api_key}")

                # Aktionen
                col_a1, col_a2 = st.columns(2)

                with col_a1:
                    if key.status == APIKeyStatus.AKTIV.value:
                        if st.button("🔴 Deaktivieren", key=f"deact_{key.id}"):
                            service.api_key_deaktivieren(key.id)
                            db.commit()
                            st.rerun()

                with col_a2:
                    if st.button("📊 Logs anzeigen", key=f"logs_{key.id}"):
                        st.session_state['show_logs_for_key'] = key.id


def _render_zugriffsprotokolle():
    """Zugriffsprotokolle"""
    st.subheader("Zugriffsprotokolle")

    with get_session() as db:
        service = APIService(db)

        # Filter
        col1, col2 = st.columns(2)

        with col1:
            keys = service.alle_api_keys()
            key_options = {0: "Alle Keys"}
            key_options.update({k.id: k.bezeichnung for k in keys})

            selected_key = st.selectbox(
                "API-Key filtern",
                list(key_options.keys()),
                format_func=lambda x: key_options.get(x, "")
            )

        with col2:
            limit = st.number_input("Anzahl Einträge", min_value=10, max_value=500, value=50)

        # Logs laden
        logs = service.api_logs(
            api_key_id=selected_key if selected_key > 0 else None,
            limit=limit
        )

        if not logs:
            st.info("Keine Protokolleinträge vorhanden")
            return

        for log in logs:
            status_color = "🟢" if 200 <= (log.status_code or 0) < 300 else "🔴"

            with st.expander(
                f"{status_color} {log.methode} {log.endpoint} - "
                f"{log.zeitstempel.strftime('%d.%m.%Y %H:%M') if log.zeitstempel else '-'}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Methode:** {log.methode}")
                    st.write(f"**Endpoint:** {log.endpoint}")
                    st.write(f"**Status:** {log.status_code}")

                with col2:
                    st.write(f"**Dauer:** {log.dauer_ms} ms" if log.dauer_ms else "**Dauer:** -")
                    st.write(f"**IP:** {log.ip_adresse or '-'}")

                if log.fehler_nachricht:
                    st.error(f"Fehler: {log.fehler_nachricht}")


def _render_statistik():
    """API-Statistik"""
    st.subheader("API-Statistik")

    with get_session() as db:
        service = APIService(db)
        statistik = service.api_statistik()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Gesamt Aufrufe", statistik['gesamt_aufrufe'])

        with col2:
            st.metric("Erfolgreich", statistik['erfolgreiche_aufrufe'])

        with col3:
            st.metric("Fehler", statistik['fehlerhafte_aufrufe'])

        with col4:
            st.metric("Ø Dauer", f"{statistik['durchschnittliche_dauer_ms']:.0f} ms")

        st.markdown("---")

        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("### Top Endpoints")
            for endpoint, count in statistik.get('nach_endpoint', {}).items():
                st.write(f"- `{endpoint}`: {count}")

        with col_s2:
            st.markdown("### Nach Methode")
            for methode, count in statistik.get('nach_methode', {}).items():
                st.write(f"- **{methode}**: {count}")


def _render_dokumentation():
    """API-Dokumentation"""
    st.subheader("API-Dokumentation")

    dokumentation = generiere_api_dokumentation()

    st.markdown(dokumentation)

    # Download
    st.download_button(
        "📥 Dokumentation herunterladen",
        data=dokumentation,
        file_name="api_dokumentation.md",
        mime="text/markdown"
    )
