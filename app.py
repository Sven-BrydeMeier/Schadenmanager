"""
Schadenmanager - Hauptanwendung
Verkehrsunfall-Abwicklungs-App
"""
import streamlit as st

from src.config.database import init_db, get_session
from src.ui.styles import inject_css
from src.ui.pages.login import require_login, get_current_user_role, get_app_version
from src.ui.pages.dashboard import render_dashboard
from src.ui.pages.projekte import render_projekte, render_projekt_details
from src.ui.pages.dokumente import render_dokumente
from src.ui.pages.kosten import render_kosten
from src.ui.pages.ersatzwagen import render_ersatzwagen_modul, render_ersatzwagen_verwaltung
from src.ui.pages.gebuehren import render_gebuehren
from src.ui.pages.korrespondenz import render_korrespondenz
from src.ui.pages.dokumente import get_ausstehende_freigaben
from src.ui.pages.wiedervorlagen import render_wiedervorlagen
from src.ui.pages.rechner import render_rechner
from src.ui.pages.audit_log import render_audit_log
from src.ui.pages.statistik import render_statistik
from src.ui.pages.werkzeuge import render_werkzeuge
from src.ui.pages.mandanten_portal import render_mandanten_portal
from src.ui.pages.papierkorb import render_papierkorb
from src.ui.pages.signatur import render_signatur
from src.ui.pages.admin_tools import render_admin_tools
from src.ui.pages.dsgvo import render_dsgvo
from src.ui.pages.ermittlungsakte import render_ermittlungsakte
from src.ui.pages.kalender import render_kalender
from src.ui.pages.prozess import render_prozess
from src.ui.pages.nachrichten import render_nachrichten
from src.ui.pages.unfallskizze import render_unfallskizze
from src.ui.pages.versicherungen import render_versicherungen
from src.ui.pages.rechnung import render_rechnungen
from src.ui.pages.schadensbilder import render_schadensbilder
from src.ui.pages.haftungsquote import render_haftungsquote
from src.ui.pages.datev import render_datev
from src.ui.pages.restwert import render_restwert
from src.ui.pages.ki_analyse import render_ki_analyse
from src.ui.pages.dokumenten_chat import render_dokumenten_chat
from src.ui.pages.fristen import render_fristen
from src.ui.pages.vergleich import render_vergleich
from src.ui.pages.email import render_email
from src.ui.pages.fallbericht import render_fallbericht
from src.ui.pages.sprachnotizen import render_sprachnotizen
from src.ui.pages.unfallort_karte import render_unfallort_karte
from src.ui.pages.fahrzeugbewertung import render_fahrzeugbewertung
from src.ui.pages.serienbriefe import render_serienbriefe
from src.ui.pages.api_verwaltung import render_api_verwaltung
from src.ui.pages.backup import render_backup
from src.ui.pages.mandanten import render_mandanten
from src.ui.pages.themes import render_themes
from src.ui.pages.gutachten_plausibilitaet import render_gutachten_plausibilitaet
from src.ui.pages.aktenimport import render_aktenimport
from src.ui.pages.unfallaufnahme import render_unfallaufnahme
from src.ui.pages.datenschutz import render_datenschutz, render_datenschutz_check_banner


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

        # Aktuelle Seite aus Session
        aktuelle_seite = st.session_state.get("page", "Dashboard")

        # Helper-Funktion für Menü-Buttons
        def menu_button(label: str, key: str = None):
            """Erstellt einen Menü-Button"""
            is_active = aktuelle_seite == label
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=key or f"menu_{label}", use_container_width=True, type=btn_type):
                st.session_state["page"] = label
                st.rerun()

        # ===== HAUPTBEREICH =====
        st.markdown("#### 📋 Hauptbereich")
        menu_button("Dashboard")
        menu_button("Projekte")
        menu_button("Dokumente")

        # Menü für Unfallopfer
        if rolle == "UNFALLOPFER":
            menu_button("Unfallaufnahme")
            menu_button("Mein Schadensfall")

        # ===== KOMMUNIKATION =====
        with st.expander("💬 Kommunikation", expanded=aktuelle_seite in ["Korrespondenz", "Nachrichten", "E-Mail", "Serienbriefe"]):
            if rolle in ["ANWALT", "ADMIN"]:
                menu_button("Korrespondenz")
            menu_button("Nachrichten")
            if rolle in ["ADMIN", "ANWALT", "WERKSTATT"]:
                menu_button("E-Mail")
            if rolle in ["ADMIN", "ANWALT"]:
                menu_button("Serienbriefe")

        # ===== TERMINE & FRISTEN =====
        with st.expander("📅 Termine & Fristen", expanded=aktuelle_seite in ["Kalender", "Wiedervorlagen", "Fristen"]):
            if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
                menu_button("Kalender")
                menu_button("Wiedervorlagen")
                menu_button("Fristen")

        # ===== SCHADEN & GUTACHTEN =====
        with st.expander("🔍 Schaden & Gutachten", expanded=aktuelle_seite in ["Schadensbilder", "Unfallskizze", "Unfallort-Karte", "Fahrzeugbewertung", "Restwertbörse", "Gutachten-Prüfung", "Sprachnotizen"]):
            if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
                menu_button("Schadensbilder")
                menu_button("Unfallskizze")
                menu_button("Unfallort-Karte")
                menu_button("Fahrzeugbewertung")
                menu_button("Sprachnotizen")
            if rolle in ["ADMIN", "ANWALT", "WERKSTATT"]:
                menu_button("Restwertbörse")
            if rolle in ["ADMIN", "ANWALT"]:
                menu_button("Gutachten-Prüfung")

        # ===== FINANZEN & ABRECHNUNG =====
        with st.expander("💰 Finanzen", expanded=aktuelle_seite in ["Kosten", "Gebührenberechnung", "Schadensrechner", "Haftungsquote", "Vergleichsrechner", "Rechnungen", "DATEV-Export"]):
            if rolle in ["ANWALT", "WERKSTATT", "VERSICHERUNG_EIGEN", "VERSICHERUNG_GEGNER", "ADMIN"]:
                menu_button("Kosten")
            if rolle in ["ANWALT", "ADMIN"]:
                menu_button("Gebührenberechnung")
                menu_button("Schadensrechner")
                menu_button("Haftungsquote")
                menu_button("Vergleichsrechner")
                menu_button("Rechnungen")
                menu_button("DATEV-Export")

        # ===== RECHTSBEREICH =====
        if rolle in ["ADMIN", "ANWALT"]:
            with st.expander("⚖️ Rechtsbereich", expanded=aktuelle_seite in ["Ermittlungsakte", "Prozessmodul", "Fallberichte", "Aktenimport"]):
                menu_button("Aktenimport")
                menu_button("Ermittlungsakte")
                menu_button("Prozessmodul")
                menu_button("Fallberichte")

        # ===== FAHRZEUG & VERSICHERUNG =====
        with st.expander("🚗 Fahrzeug", expanded=aktuelle_seite in ["Ersatzwagen", "Versicherungen", "Ersatzwagen-Verwaltung"]):
            if rolle in ["WERKSTATT", "UNFALLOPFER", "ADMIN"]:
                menu_button("Ersatzwagen")
            if rolle not in ["UNFALLOPFER"]:
                menu_button("Versicherungen")
            if rolle == "ADMIN":
                menu_button("Ersatzwagen-Verwaltung")

        # ===== WERKZEUGE & KI =====
        with st.expander("🛠️ Werkzeuge & KI", expanded=aktuelle_seite in ["Werkzeuge", "KI-Analyse", "Dokumenten-Chat"]):
            menu_button("Dokumenten-Chat")
            if rolle in ["ANWALT", "WERKSTATT", "ADMIN"]:
                menu_button("Werkzeuge")
            if rolle in ["ADMIN", "ANWALT"]:
                menu_button("KI-Analyse")

        # ===== SYSTEM =====
        with st.expander("⚙️ System", expanded=aktuelle_seite in ["Statistik", "Audit-Log", "Signatur", "DSGVO", "Datenschutz", "Papierkorb", "Admin-Tools", "API-Verwaltung", "Backup", "Mandanten", "Erscheinungsbild"]):
            if rolle in ["ADMIN", "ANWALT"]:
                menu_button("Statistik")
                menu_button("Audit-Log")
            menu_button("Signatur")
            menu_button("Datenschutz")
            if rolle in ["ADMIN", "ANWALT", "WERKSTATT"]:
                menu_button("DSGVO")
            if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
                menu_button("Papierkorb")
            if rolle in ["ADMIN", "ANWALT"]:
                menu_button("Admin-Tools")
            if rolle == "ADMIN":
                menu_button("API-Verwaltung")
                menu_button("Backup")
                menu_button("Mandanten")
            menu_button("Erscheinungsbild")

        seite = st.session_state.get("page", "Dashboard")

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
        st.caption(f"Schadenmanager v{get_app_version()}")

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

    elif page == "Wiedervorlagen":
        render_wiedervorlagen()

    elif page == "Schadensrechner":
        render_rechner()

    elif page == "Audit-Log":
        render_audit_log()

    elif page == "Statistik":
        render_statistik()

    elif page == "Werkzeuge":
        render_werkzeuge()

    elif page == "Mein Schadensfall":
        render_mandanten_portal()

    elif page == "Unfallaufnahme":
        if rolle == "UNFALLOPFER":
            render_unfallaufnahme()
        else:
            st.error("Diese Seite ist nur für Unfallopfer verfügbar.")

    elif page == "Papierkorb":
        render_papierkorb()

    elif page == "Signatur":
        render_signatur()

    elif page == "Admin-Tools":
        render_admin_tools()

    elif page == "DSGVO":
        render_dsgvo()

    elif page == "Ermittlungsakte":
        render_ermittlungsakte()

    elif page == "Kalender":
        render_kalender()

    elif page == "Prozessmodul":
        render_prozess()

    elif page == "Nachrichten":
        render_nachrichten()

    elif page == "Unfallskizze":
        render_unfallskizze()

    elif page == "Versicherungen":
        render_versicherungen()

    elif page == "Rechnungen":
        render_rechnungen()

    elif page == "Schadensbilder":
        render_schadensbilder()

    elif page == "Haftungsquote":
        render_haftungsquote()

    elif page == "Gutachten-Prüfung":
        if rolle in ["ADMIN", "ANWALT"]:
            render_gutachten_plausibilitaet()
        else:
            st.error("Keine Berechtigung für diese Seite.")

    elif page == "DATEV-Export":
        render_datev()

    elif page == "Restwertbörse":
        render_restwert()

    elif page == "KI-Analyse":
        render_ki_analyse()

    elif page == "Dokumenten-Chat":
        render_dokumenten_chat()

    elif page == "Fristen":
        render_fristen()

    elif page == "Vergleichsrechner":
        render_vergleich()

    elif page == "E-Mail":
        render_email()

    elif page == "Fallberichte":
        render_fallbericht()

    elif page == "Aktenimport":
        if rolle in ["ADMIN", "ANWALT"]:
            render_aktenimport()
        else:
            st.error("Keine Berechtigung für diese Seite.")

    elif page == "Sprachnotizen":
        render_sprachnotizen()

    elif page == "Unfallort-Karte":
        render_unfallort_karte()

    elif page == "Fahrzeugbewertung":
        render_fahrzeugbewertung()

    elif page == "Serienbriefe":
        render_serienbriefe()

    elif page == "API-Verwaltung":
        if rolle == "ADMIN":
            render_api_verwaltung()
        else:
            st.error("Keine Berechtigung für diese Seite.")

    elif page == "Backup":
        if rolle == "ADMIN":
            render_backup()
        else:
            st.error("Keine Berechtigung für diese Seite.")

    elif page == "Mandanten":
        if rolle == "ADMIN":
            render_mandanten()
        else:
            st.error("Keine Berechtigung für diese Seite.")

    elif page == "Erscheinungsbild":
        render_themes()

    elif page == "Datenschutz":
        render_datenschutz()

    else:
        st.warning(f"Seite '{page}' nicht gefunden.")


if __name__ == "__main__":
    main()
