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
        if st.button("Abmelden", use_container_width=True):
            # Session löschen
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # Footer
        st.markdown("---")
        st.caption("Schadenmanager v1.0")

    return seite


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
