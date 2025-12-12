"""
Schadenmanager - Hauptanwendung
Verkehrsunfall-Abwicklungs-App
"""
import streamlit as st

from src.config.database import init_db, get_session
from src.ui.styles import inject_css
from src.ui.pages.login import require_login, get_current_user_role
from src.ui.pages.dashboard import render_dashboard
from src.ui.pages.projekte import render_projekte, render_projekt_details
from src.ui.pages.dokumente import render_dokumente
from src.ui.pages.kosten import render_kosten
from src.ui.pages.ersatzwagen import render_ersatzwagen_modul, render_ersatzwagen_verwaltung
from src.ui.pages.gebuehren import render_gebuehren
from src.ui.pages.korrespondenz import render_korrespondenz
from src.ui.pages.dokumente import get_ausstehende_freigaben


# Streamlit-Konfiguration
st.set_page_config(
    page_title="Schadenmanager",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """Hauptfunktion der Anwendung"""

    # CSS injizieren
    inject_css()

    # Datenbank initialisieren (nur beim ersten Start)
    if "db_initialized" not in st.session_state:
        init_db()

        # Demo-Daten erstellen
        try:
            from src.services.demo_data import create_demo_data
            with get_session() as db:
                create_demo_data(db)
        except Exception as e:
            print(f"Demo-Daten konnten nicht erstellt werden: {e}")

        st.session_state["db_initialized"] = True

    # Login prüfen
    if not require_login():
        return

    # Navigation
    rolle = get_current_user_role()
    page = render_sidebar(rolle)

    # Seite rendern
    render_page(page, rolle)


def render_sidebar(rolle: str) -> str:
    """Rendert die Sidebar und gibt die ausgewählte Seite zurück"""

    with st.sidebar:
        # Logo/Header
        st.markdown("# 🚗 Schadenmanager")
        st.markdown("---")

        # Benutzerinfo
        user_name = st.session_state.get("user_name", "Benutzer")
        st.markdown(f"**{user_name}**")

        rolle_anzeige = {
            "WERKSTATT": "Werkstatt",
            "GUTACHTER": "Gutachter",
            "VERSICHERUNG_EIGEN": "Eigene Versicherung",
            "VERSICHERUNG_GEGNER": "Gegnerische Versicherung",
            "ANWALT": "Rechtsanwalt",
            "UNFALLOPFER": "Unfallopfer",
            "ADMIN": "Administrator"
        }.get(rolle, rolle)

        st.caption(rolle_anzeige)
        st.markdown("---")

        # Navigation
        st.markdown("### Navigation")

        # Gemeinsame Menüpunkte
        menu = ["Dashboard", "Projekte", "Dokumente"]

        # Rollenspezifische Menüpunkte
        if rolle in ["ANWALT", "ADMIN"]:
            menu.extend(["Korrespondenz", "Gebührenberechnung"])

        if rolle in ["WERKSTATT", "UNFALLOPFER", "ADMIN"]:
            menu.append("Ersatzwagen")

        if rolle in ["ANWALT", "WERKSTATT", "VERSICHERUNG_EIGEN", "VERSICHERUNG_GEGNER", "ADMIN"]:
            menu.append("Kosten")

        if rolle == "ADMIN":
            menu.append("Ersatzwagen-Verwaltung")

        # Aktuelle Seite aus Session oder Standard
        aktuelle_seite = st.session_state.get("page", "Dashboard")
        if aktuelle_seite not in menu:
            aktuelle_seite = "Dashboard"

        seite = st.radio(
            "Menü",
            menu,
            index=menu.index(aktuelle_seite) if aktuelle_seite in menu else 0,
            label_visibility="collapsed"
        )

        st.session_state["page"] = seite

        # Aktives Projekt anzeigen
        aktives_projekt_id = st.session_state.get("aktives_projekt_id")
        if aktives_projekt_id:
            st.markdown("---")
            st.markdown("**Aktives Projekt:**")
            # Projektnummer würde hier aus der DB geladen

        # Abmelden
        st.markdown("---")

        # Prüfe auf ausstehende Freigaben beim Ausloggen
        if st.session_state.get("show_logout_warning"):
            _render_logout_warning()
        elif st.button("Abmelden", use_container_width=True):
            _handle_logout_request()

        # Footer
        st.markdown("---")
        st.caption("Schadenmanager v1.0")

    return seite


def _handle_logout_request():
    """Behandelt eine Logout-Anfrage und prüft auf ausstehende Freigaben"""
    user_id = st.session_state.get("user_id")

    if user_id:
        with get_session() as db:
            ausstehende = get_ausstehende_freigaben(db, user_id)

            if ausstehende:
                # Es gibt ausstehende Freigaben - Warnung anzeigen
                st.session_state["show_logout_warning"] = True
                st.session_state["ausstehende_freigaben_ids"] = [d.id for d in ausstehende]
                st.rerun()
            else:
                # Keine ausstehenden Freigaben - direkt ausloggen
                _perform_logout()
    else:
        _perform_logout()


def _render_logout_warning():
    """Rendert die Logout-Warnung für ausstehende Freigaben"""
    from src.models import Dokument
    from datetime import datetime

    st.warning("Ausstehende Freigaben!")

    user_id = st.session_state.get("user_id")
    ausstehende_ids = st.session_state.get("ausstehende_freigaben_ids", [])

    with get_session() as db:
        ausstehende = db.query(Dokument).filter(Dokument.id.in_(ausstehende_ids)).all()

        if ausstehende:
            st.markdown("Sie haben noch **nicht freigegebene Dokumente**:")

            for dok in ausstehende:
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.caption(f"{dok.dokument_typ_anzeige}: {dok.original_dateiname}")

                with col2:
                    if st.button("Freigeben", key=f"logout_freigabe_{dok.id}", type="primary"):
                        dok.freigabe_erteilt = True
                        dok.freigabe_erteilt_von_user_id = user_id
                        dok.freigabe_erteilt_am = datetime.now()
                        db.flush()
                        # Aktualisiere die Liste
                        st.session_state["ausstehende_freigaben_ids"] = [
                            d_id for d_id in ausstehende_ids if d_id != dok.id
                        ]
                        if not st.session_state["ausstehende_freigaben_ids"]:
                            st.session_state["show_logout_warning"] = False
                        st.rerun()

                with col3:
                    if st.button("Überspringen", key=f"logout_skip_{dok.id}"):
                        # Markiere, dass der Benutzer dieses Dokument übersprungen hat
                        dok.freigabe_ueberspringen(user_id)
                        db.flush()
                        # Aktualisiere die Liste
                        st.session_state["ausstehende_freigaben_ids"] = [
                            d_id for d_id in ausstehende_ids if d_id != dok.id
                        ]
                        if not st.session_state["ausstehende_freigaben_ids"]:
                            st.session_state["show_logout_warning"] = False
                        st.rerun()

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Alle freigeben & Abmelden", type="primary", use_container_width=True):
            with get_session() as db:
                from src.models import Dokument
                from datetime import datetime

                ausstehende = db.query(Dokument).filter(
                    Dokument.id.in_(ausstehende_ids)
                ).all()

                for dok in ausstehende:
                    dok.freigabe_erteilt = True
                    dok.freigabe_erteilt_von_user_id = user_id
                    dok.freigabe_erteilt_am = datetime.now()

                db.flush()

            _perform_logout()

    with col2:
        if st.button("Trotzdem abmelden", use_container_width=True):
            # Markiere alle als übersprungen
            with get_session() as db:
                from src.models import Dokument

                ausstehende = db.query(Dokument).filter(
                    Dokument.id.in_(ausstehende_ids)
                ).all()

                for dok in ausstehende:
                    dok.freigabe_ueberspringen(user_id)

                db.flush()

            _perform_logout()

    # Abbrechen-Button
    if st.button("Abbrechen", use_container_width=True):
        st.session_state["show_logout_warning"] = False
        if "ausstehende_freigaben_ids" in st.session_state:
            del st.session_state["ausstehende_freigaben_ids"]
        st.rerun()


def _perform_logout():
    """Führt das Logout durch"""
    # Session löschen
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def render_page(page: str, rolle: str):
    """Rendert die ausgewählte Seite"""

    if page == "Dashboard":
        render_dashboard()

    elif page == "Projekte":
        render_projekte()

    elif page == "Dokumente":
        render_dokumente()

    elif page == "Kosten":
        render_kosten()

    elif page == "Ersatzwagen":
        render_ersatzwagen_modul()

    elif page == "Korrespondenz":
        render_korrespondenz()

    elif page == "Gebührenberechnung":
        render_gebuehren()

    elif page == "Ersatzwagen-Verwaltung":
        if rolle == "ADMIN":
            render_ersatzwagen_verwaltung()
        else:
            st.error("Keine Berechtigung für diese Seite.")

    else:
        st.warning(f"Seite '{page}' nicht gefunden.")


if __name__ == "__main__":
    main()
