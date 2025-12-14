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
            menu.extend(["Korrespondenz", "Gebührenberechnung", "Schadensrechner"])

        if rolle in ["WERKSTATT", "UNFALLOPFER", "ADMIN"]:
            menu.append("Ersatzwagen")

        # Mandanten-Portal für Unfallopfer
        if rolle == "UNFALLOPFER":
            menu.append("Mein Schadensfall")

        if rolle in ["ANWALT", "WERKSTATT", "VERSICHERUNG_EIGEN", "VERSICHERUNG_GEGNER", "ADMIN"]:
            menu.append("Kosten")

        # Wiedervorlagen für alle Rollen mit Projektzugriff
        if rolle in ["ANWALT", "WERKSTATT", "GUTACHTER", "ADMIN"]:
            menu.append("Wiedervorlagen")

        # Werkzeuge für Anwälte, Werkstätten und Admins
        if rolle in ["ANWALT", "WERKSTATT", "ADMIN"]:
            menu.append("Werkzeuge")

        # Audit-Log nur für Admins und Anwälte
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Audit-Log")

        # Statistik für Admins und Anwälte
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Statistik")

        # Papierkorb für alle mit Dokumentenzugriff
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
            menu.append("Papierkorb")

        # Digitale Signatur für alle
        menu.append("Signatur")

        # Admin-Tools für Admins und Anwälte
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Admin-Tools")

        # DSGVO für Anwälte, Werkstätten und Admins
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT"]:
            menu.append("DSGVO")

        # Ermittlungsakte nur für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Ermittlungsakte")

        # Neue Features
        # Terminkalender für alle mit Projektzugriff
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
            menu.append("Kalender")

        # Prozessmodul nur für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Prozessmodul")

        # Nachrichten für alle
        menu.append("Nachrichten")

        # Unfallskizze für alle mit Projektzugriff
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
            menu.append("Unfallskizze")

        # Versicherungsdatenbank für alle außer Unfallopfer
        if rolle not in ["UNFALLOPFER"]:
            menu.append("Versicherungen")

        # Rechnungsstellung nur für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Rechnungen")

        # Schadensbilder für alle mit Projektzugriff
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
            menu.append("Schadensbilder")

        # Haftungsquoten-Rechner für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Haftungsquote")

        # Gutachten-Plausibilitätsprüfung für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Gutachten-Prüfung")

        # DATEV-Export nur für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("DATEV-Export")

        # Restwertbörse für Anwälte, Werkstätten und Admins
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT"]:
            menu.append("Restwertbörse")

        # Neue erweiterte Features
        # KI-Analyse für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("KI-Analyse")

        # Fristenwarnsystem für alle mit Projektzugriff
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
            menu.append("Fristen")

        # Vergleichsrechner für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Vergleichsrechner")

        # E-Mail-Integration für Anwälte, Werkstätten und Admins
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT"]:
            menu.append("E-Mail")

        # Fallberichte für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Fallberichte")

        # Sprachnotizen für alle mit Projektzugriff
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
            menu.append("Sprachnotizen")

        # Unfallort-Karte für alle mit Projektzugriff
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
            menu.append("Unfallort-Karte")

        # Fahrzeugbewertung für Anwälte, Werkstätten und Gutachter
        if rolle in ["ADMIN", "ANWALT", "WERKSTATT", "GUTACHTER"]:
            menu.append("Fahrzeugbewertung")

        # Serienbriefe für Anwälte und Admins
        if rolle in ["ADMIN", "ANWALT"]:
            menu.append("Serienbriefe")

        # API-Verwaltung nur für Admins
        if rolle == "ADMIN":
            menu.append("API-Verwaltung")

        # Backup nur für Admins
        if rolle == "ADMIN":
            menu.append("Backup")

        # Multi-Mandanten nur für Admins
        if rolle == "ADMIN":
            menu.append("Mandanten")

        # Theme-Einstellungen für alle
        menu.append("Erscheinungsbild")

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

    elif page == "Fristen":
        render_fristen()

    elif page == "Vergleichsrechner":
        render_vergleich()

    elif page == "E-Mail":
        render_email()

    elif page == "Fallberichte":
        render_fallbericht()

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

    else:
        st.warning(f"Seite '{page}' nicht gefunden.")


if __name__ == "__main__":
    main()
