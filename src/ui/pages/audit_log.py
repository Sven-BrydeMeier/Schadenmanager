"""
Audit-Log Ansicht für Administratoren
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from src.models import AuditLog, AktionKategorie, UnfallProjekt, User
from src.services.audit_service import get_audit_service
from src.ui.components import badge
from src.config.database import get_session


def render_audit_log():
    """Rendert die Audit-Log-Ansicht"""

    st.markdown("## Audit-Log")

    rolle = st.session_state.get("user_rolle")

    # Nur Admins und Anwälte sehen das volle Audit-Log
    if rolle not in ["ADMIN", "ANWALT"]:
        st.warning("Sie haben keine Berechtigung, das Audit-Log einzusehen.")
        return

    tabs = st.tabs(["Aktivitäten", "Projekt-Historie", "Statistiken"])

    with tabs[0]:
        _render_aktivitaeten()

    with tabs[1]:
        _render_projekt_historie()

    with tabs[2]:
        _render_statistiken()


def _render_aktivitaeten():
    """Rendert die allgemeine Aktivitätenübersicht"""

    with get_session() as db:
        audit_service = get_audit_service(db)

        # Filter
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            kategorie_optionen = ["Alle"] + [
                AktionKategorie.AUTH,
                AktionKategorie.PROJEKT,
                AktionKategorie.DOKUMENT,
                AktionKategorie.KOSTEN,
                AktionKategorie.WIEDERVORLAGE
            ]
            kategorie = st.selectbox("Kategorie", kategorie_optionen)

        with col2:
            zeitraum = st.selectbox(
                "Zeitraum",
                ["Heute", "Letzte 7 Tage", "Letzte 30 Tage", "Alles"]
            )

        with col3:
            # Benutzer-Filter (nur für Admins)
            if st.session_state.get("user_rolle") == "ADMIN":
                users = db.query(User).all()
                user_optionen = {"Alle": None}
                user_optionen.update({u.voller_name or u.email: u.id for u in users})
                user_auswahl = st.selectbox("Benutzer", list(user_optionen.keys()))
                user_id_filter = user_optionen[user_auswahl]
            else:
                user_id_filter = None

        with col4:
            limit = st.selectbox("Einträge", [50, 100, 200, 500], index=0)

        # Zeitraum berechnen
        von_datum = None
        if zeitraum == "Heute":
            von_datum = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif zeitraum == "Letzte 7 Tage":
            von_datum = datetime.now() - timedelta(days=7)
        elif zeitraum == "Letzte 30 Tage":
            von_datum = datetime.now() - timedelta(days=30)

        # Logs abrufen
        logs = audit_service.get_logs(
            limit=limit,
            user_id=user_id_filter,
            kategorie=kategorie if kategorie != "Alle" else None,
            von_datum=von_datum
        )

        st.markdown("---")
        st.caption(f"{len(logs)} Einträge gefunden")

        if not logs:
            st.info("Keine Aktivitäten gefunden.")
            return

        # Logs anzeigen
        for log in logs:
            _render_log_eintrag(log)


def _render_log_eintrag(log: AuditLog):
    """Rendert einen einzelnen Log-Eintrag"""

    with st.container():
        col1, col2, col3 = st.columns([1, 3, 1])

        with col1:
            # Zeitstempel
            if log.zeitstempel:
                st.caption(log.zeitstempel.strftime("%d.%m.%Y"))
                st.caption(log.zeitstempel.strftime("%H:%M:%S"))

        with col2:
            # Aktion mit Icon
            aktion_icons = {
                "LOGIN": "🔑",
                "LOGOUT": "🚪",
                "DOKUMENT_HOCHGELADEN": "📄",
                "DOKUMENT_FREIGEGEBEN": "✅",
                "PROJEKT_ERSTELLT": "📁",
                "PROJEKT_STATUS_GEAENDERT": "🔄",
                "KOSTENPOSITION_ERSTELLT": "💰",
                "WIEDERVORLAGE_ERSTELLT": "📅",
                "WIEDERVORLAGE_ERLEDIGT": "☑️",
            }
            icon = aktion_icons.get(log.aktion, "📝")

            st.markdown(f"**{icon} {log.aktion}**")

            # Details
            details_text = []
            if log.user_name:
                details_text.append(f"Benutzer: {log.user_name}")
            elif log.user_email:
                details_text.append(f"Benutzer: {log.user_email}")

            if log.aktenzeichen:
                details_text.append(f"Akte: {log.aktenzeichen}")

            if log.objekt_bezeichnung:
                details_text.append(f"Objekt: {log.objekt_bezeichnung}")

            if log.beschreibung:
                details_text.append(log.beschreibung)

            if details_text:
                st.caption(" | ".join(details_text))

        with col3:
            # Kategorie-Badge
            kategorie_farben = {
                AktionKategorie.AUTH: "info",
                AktionKategorie.PROJEKT: "primary",
                AktionKategorie.DOKUMENT: "success",
                AktionKategorie.KOSTEN: "warning",
                AktionKategorie.WIEDERVORLAGE: "secondary",
            }
            farbe = kategorie_farben.get(log.aktion_kategorie, "secondary")
            st.markdown(badge(log.aktion_kategorie or "SYSTEM", farbe), unsafe_allow_html=True)

        st.markdown("---")


def _render_projekt_historie():
    """Rendert die Historie eines bestimmten Projekts"""

    st.markdown("### Projekt-Historie")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    with get_session() as db:
        # Projektauswahl
        if aktives_projekt_id:
            projekt = db.query(UnfallProjekt).filter(
                UnfallProjekt.id == aktives_projekt_id
            ).first()
            if projekt:
                st.info(f"Aktives Projekt: {projekt.aktenzeichen or projekt.projektnummer}")
                projekt_id = projekt.id
            else:
                projekt_id = None
        else:
            projekte = db.query(UnfallProjekt).all()
            if not projekte:
                st.warning("Keine Projekte vorhanden.")
                return

            projekt_optionen = {
                f"{p.aktenzeichen or p.projektnummer}": p.id
                for p in projekte
            }

            ausgewaehltes = st.selectbox("Projekt auswählen", list(projekt_optionen.keys()))
            projekt_id = projekt_optionen.get(ausgewaehltes)

        if not projekt_id:
            return

        audit_service = get_audit_service(db)

        # Historie abrufen
        logs = audit_service.get_projekt_historie(projekt_id, limit=100)

        st.markdown("---")

        if not logs:
            st.info("Keine Aktivitäten für dieses Projekt gefunden.")
            return

        st.caption(f"{len(logs)} Aktivitäten gefunden")

        # Timeline-Ansicht
        for log in logs:
            _render_log_eintrag(log)


def _render_statistiken():
    """Rendert Statistiken über die Aktivitäten"""

    st.markdown("### Aktivitäts-Statistiken")

    with get_session() as db:
        audit_service = get_audit_service(db)

        # Zeitraum
        zeitraum = st.selectbox(
            "Zeitraum",
            ["Letzte 7 Tage", "Letzte 30 Tage", "Letzte 90 Tage"],
            index=1
        )

        tage = {"Letzte 7 Tage": 7, "Letzte 30 Tage": 30, "Letzte 90 Tage": 90}[zeitraum]
        von_datum = datetime.now() - timedelta(days=tage)

        st.markdown("---")

        # Gesamtzahlen
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            gesamt = audit_service.count_logs()
            st.metric("Aktivitäten gesamt", gesamt)

        with col2:
            auth = audit_service.count_logs(kategorie=AktionKategorie.AUTH)
            st.metric("Anmeldungen", auth)

        with col3:
            dokumente = audit_service.count_logs(kategorie=AktionKategorie.DOKUMENT)
            st.metric("Dokument-Aktionen", dokumente)

        with col4:
            projekte = audit_service.count_logs(kategorie=AktionKategorie.PROJEKT)
            st.metric("Projekt-Aktionen", projekte)

        st.markdown("---")

        # Aktivitäten pro Kategorie
        st.markdown("#### Aktivitäten nach Kategorie")

        kategorien = [
            (AktionKategorie.AUTH, "Authentifizierung"),
            (AktionKategorie.PROJEKT, "Projekte"),
            (AktionKategorie.DOKUMENT, "Dokumente"),
            (AktionKategorie.KOSTEN, "Kosten"),
            (AktionKategorie.KORRESPONDENZ, "Korrespondenz"),
            (AktionKategorie.WIEDERVORLAGE, "Wiedervorlagen"),
            (AktionKategorie.BENUTZER, "Benutzerverwaltung"),
        ]

        for kategorie, name in kategorien:
            anzahl = audit_service.count_logs(kategorie=kategorie)
            if anzahl > 0:
                st.progress(min(anzahl / 100, 1.0), text=f"{name}: {anzahl}")

        # Hinweis für Datenschutz
        st.markdown("---")
        st.caption("""
        **Hinweis zum Datenschutz:**
        Das Audit-Log dient der Nachvollziehbarkeit und Rechtssicherheit.
        Die Daten werden gemäß DSGVO verarbeitet und nach den gesetzlichen
        Aufbewahrungsfristen gelöscht.
        """)
