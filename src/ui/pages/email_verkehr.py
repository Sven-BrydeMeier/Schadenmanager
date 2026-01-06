"""
Email-Verkehr Seite
Intelligenter Ordner für alle Emails einer Akte mit Drag & Drop Import
"""

import streamlit as st
from datetime import datetime
from typing import Optional, List

from src.services.email_integration import EmailIntegrationService, Email, EmailStatus, EmailPrioritaet
from src.models import UnfallProjekt, Rollen
from src.utils.session import get_current_user, get_db_session


def render_email_verkehr():
    """Rendert die Email-Verkehr Seite"""
    user = get_current_user()
    if not user:
        st.warning("Bitte melden Sie sich an.")
        return

    st.title("📧 Email-Verkehr")

    db = get_db_session()
    email_service = EmailIntegrationService(db)

    # Projekt-Auswahl
    projekt_id = _render_projekt_auswahl(db, user)

    if not projekt_id:
        # Zeige alle unzugeordneten Emails
        _render_unzugeordnete_emails(email_service, db, user)
        return

    # Tabs für verschiedene Ansichten
    tab1, tab2, tab3 = st.tabs([
        "📥 Email-Verkehr",
        "📤 Email importieren",
        "🔍 Suche"
    ])

    with tab1:
        _render_email_liste(email_service, projekt_id, db)

    with tab2:
        _render_email_import(email_service, projekt_id, user.id, db)

    with tab3:
        _render_email_suche(email_service, projekt_id)


def _render_projekt_auswahl(db, user) -> Optional[int]:
    """Rendert die Projekt-Auswahl"""
    # Aktives Projekt aus Session
    projekt_id = st.session_state.get("aktives_projekt_id")

    # Projekt-Auswahl in Sidebar
    with st.sidebar:
        st.subheader("📁 Akte auswählen")

        # Projekte laden basierend auf Rolle
        if user.rolle in [Rollen.ANWALT, Rollen.ADMIN]:
            projekte = db.query(UnfallProjekt).filter(
                UnfallProjekt.abgeschlossen == False
            ).order_by(UnfallProjekt.aktualisiert_am.desc()).limit(50).all()
        else:
            projekte = db.query(UnfallProjekt).filter(
                UnfallProjekt.unfallopfer_user_id == user.id
            ).all()

        projekt_optionen = {
            f"{p.aktenzeichen or p.projektnummer}": p.id
            for p in projekte
        }

        if projekt_optionen:
            # Finde aktuelles Projekt in Liste
            aktuelle_auswahl = None
            for name, pid in projekt_optionen.items():
                if pid == projekt_id:
                    aktuelle_auswahl = name
                    break

            auswahl = st.selectbox(
                "Akte",
                options=list(projekt_optionen.keys()),
                index=list(projekt_optionen.keys()).index(aktuelle_auswahl) if aktuelle_auswahl else 0,
                key="email_projekt_auswahl"
            )

            if auswahl:
                projekt_id = projekt_optionen[auswahl]
                st.session_state["aktives_projekt_id"] = projekt_id

        # Statistiken
        if projekt_id:
            stats = email_service.email_statistik(projekt_id)
            st.markdown("---")
            st.metric("Gesamt", stats['gesamt'])
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Eingang", stats['eingang'])
            with col2:
                st.metric("Ausgang", stats['ausgang'])
            if stats['ungelesen'] > 0:
                st.warning(f"📬 {stats['ungelesen']} ungelesen")

    return projekt_id


def _render_email_liste(email_service: EmailIntegrationService, projekt_id: int, db):
    """Rendert die Email-Liste für ein Projekt"""

    # Filter-Optionen
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_status = st.selectbox(
            "Status",
            ["Alle", "Ungelesen", "Bearbeitet", "Archiviert"],
            key="email_filter_status"
        )

    with col2:
        filter_richtung = st.selectbox(
            "Richtung",
            ["Alle", "Eingang", "Ausgang"],
            key="email_filter_richtung"
        )

    with col3:
        gruppieren = st.checkbox("Nach Thread gruppieren", value=True, key="email_gruppieren")

    st.markdown("---")

    # Emails laden
    if gruppieren:
        threads = email_service.emails_fuer_projekt_gruppiert(projekt_id)

        if not threads:
            st.info("Keine Emails vorhanden. Importieren Sie Emails über den Tab 'Email importieren'.")
            return

        for thread_id, emails in threads.items():
            # Erste Email als Thread-Header
            erste = emails[0]
            anzahl = len(emails)

            with st.expander(
                f"{'📩' if not erste.gelesen else '📧'} {erste.betreff or '(Kein Betreff)'} "
                f"({anzahl} {'Email' if anzahl == 1 else 'Emails'})",
                expanded=False
            ):
                for email in emails:
                    _render_email_karte(email, email_service, db)
    else:
        emails = email_service.emails_fuer_projekt(projekt_id)

        if not emails:
            st.info("Keine Emails vorhanden.")
            return

        for email in emails:
            _render_email_karte(email, email_service, db)


def _render_email_karte(email: Email, email_service: EmailIntegrationService, db):
    """Rendert eine einzelne Email-Karte"""

    # Status-Icon
    if not email.gelesen:
        icon = "📩"
        style = "border-left: 3px solid #1976d2;"
    else:
        icon = "📧"
        style = "border-left: 3px solid #9e9e9e;"

    # Prioritäts-Badge
    prio_badge = ""
    if email.prioritaet == EmailPrioritaet.DRINGEND:
        prio_badge = "🔴 DRINGEND"
    elif email.prioritaet == EmailPrioritaet.HOCH:
        prio_badge = "🟠 Wichtig"

    st.markdown(f"""
    <div style="background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px; {style}">
        <div style="display: flex; justify-content: space-between;">
            <strong>{icon} {email.betreff or '(Kein Betreff)'}</strong>
            <span style="color: #666; font-size: 0.9em;">
                {email.gesendet_am.strftime('%d.%m.%Y %H:%M') if email.gesendet_am else 'Unbekannt'}
            </span>
        </div>
        <div style="color: #666; font-size: 0.9em; margin-top: 5px;">
            Von: {email.von} {prio_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Details anzeigen
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        if st.button("📖 Lesen", key=f"read_{email.id}"):
            st.session_state[f"show_email_{email.id}"] = True
            if not email.gelesen:
                email_service.email_als_gelesen_markieren(email.id)
                st.rerun()

    with col2:
        if email.anhaenge:
            st.write(f"📎 {len(email.anhaenge)} Anhänge")

    with col3:
        if email.auto_zugeordnet:
            st.write(f"🤖 {email.zuordnung_konfidenz}%")

    # Email-Inhalt anzeigen wenn ausgewählt
    if st.session_state.get(f"show_email_{email.id}"):
        with st.container():
            st.markdown("---")
            st.markdown(f"**Von:** {email.von}")
            st.markdown(f"**An:** {email.an}")
            if email.cc:
                st.markdown(f"**CC:** {email.cc}")
            st.markdown(f"**Datum:** {email.gesendet_am}")
            st.markdown("---")

            # Inhalt
            if email.html_inhalt:
                st.components.v1.html(email.html_inhalt, height=400, scrolling=True)
            else:
                st.text(email.text_inhalt or "(Kein Inhalt)")

            # Anhänge
            if email.anhaenge:
                st.markdown("**Anhänge:**")
                for anh in email.anhaenge:
                    st.write(f"📎 {anh.get('dateiname', 'Anhang')} ({anh.get('groesse', 0) / 1024:.1f} KB)")

            if st.button("Schließen", key=f"close_{email.id}"):
                st.session_state[f"show_email_{email.id}"] = False
                st.rerun()


def _render_email_import(email_service: EmailIntegrationService, projekt_id: int, user_id: int, db):
    """Rendert den Email-Import Bereich mit Drag & Drop"""

    st.subheader("📤 Emails importieren")

    st.info("""
    **Drag & Drop Import**

    Ziehen Sie Email-Dateien (.eml oder .msg) hierher, um sie zur Akte hinzuzufügen.

    - Emails werden automatisch geparst (Absender, Empfänger, Betreff, Datum)
    - Anhänge werden extrahiert und separat gespeichert
    - Aktenzeichen werden automatisch erkannt
    """)

    # File Uploader mit Drag & Drop
    uploaded_files = st.file_uploader(
        "Email-Dateien hochladen",
        type=["eml", "msg"],
        accept_multiple_files=True,
        key="email_upload",
        help="Unterstützte Formate: .eml (Standard), .msg (Outlook)"
    )

    if uploaded_files:
        st.markdown("---")
        st.subheader(f"📋 {len(uploaded_files)} Datei(en) ausgewählt")

        erfolge = 0
        fehler = []

        progress = st.progress(0)

        for i, file in enumerate(uploaded_files):
            progress.progress((i + 1) / len(uploaded_files))

            with st.spinner(f"Importiere {file.name}..."):
                bytes_data = file.read()

                email_obj, error = email_service.importiere_email_datei(
                    datei_bytes=bytes_data,
                    dateiname=file.name,
                    user_id=user_id,
                    projekt_id=projekt_id
                )

                if error and "bereits importiert" not in error.lower():
                    fehler.append(f"{file.name}: {error}")
                else:
                    erfolge += 1

        progress.empty()

        # Ergebnis anzeigen
        if erfolge > 0:
            st.success(f"✅ {erfolge} Email(s) erfolgreich importiert!")
            db.commit()

        if fehler:
            st.error("Fehler bei einigen Dateien:")
            for f in fehler:
                st.write(f"- {f}")

        # Seite neu laden um neue Emails anzuzeigen
        if erfolge > 0:
            if st.button("🔄 Emails anzeigen"):
                st.rerun()


def _render_email_suche(email_service: EmailIntegrationService, projekt_id: int):
    """Rendert die Email-Suche"""

    st.subheader("🔍 Email-Suche")

    col1, col2 = st.columns(2)

    with col1:
        suchbegriff = st.text_input(
            "Suchbegriff",
            placeholder="Betreff oder Inhalt durchsuchen...",
            key="email_suche_text"
        )

    with col2:
        von_filter = st.text_input(
            "Von (Absender)",
            placeholder="Email-Adresse oder Name",
            key="email_suche_von"
        )

    col3, col4 = st.columns(2)

    with col3:
        nur_ungelesen = st.checkbox("Nur ungelesene", key="email_suche_ungelesen")

    with col4:
        nur_anhaenge = st.checkbox("Nur mit Anhängen", key="email_suche_anhaenge")

    if st.button("🔍 Suchen", key="email_suche_btn"):
        ergebnisse = email_service.suche_emails(
            projekt_id=projekt_id,
            suchbegriff=suchbegriff if suchbegriff else None,
            von=von_filter if von_filter else None,
            nur_ungelesen=nur_ungelesen,
            nur_mit_anhaengen=nur_anhaenge
        )

        st.markdown("---")

        if ergebnisse:
            st.success(f"✅ {len(ergebnisse)} Ergebnis(se) gefunden")

            for email in ergebnisse:
                with st.expander(f"📧 {email.betreff or '(Kein Betreff)'} - {email.von}"):
                    st.write(f"**Datum:** {email.gesendet_am}")
                    st.write(f"**Von:** {email.von}")
                    st.write(f"**An:** {email.an}")
                    st.markdown("---")
                    st.text(email.text_inhalt[:500] + "..." if email.text_inhalt and len(email.text_inhalt) > 500 else email.text_inhalt or "")
        else:
            st.info("Keine Emails gefunden.")


def _render_unzugeordnete_emails(email_service: EmailIntegrationService, db, user):
    """Rendert unzugeordnete Emails zur manuellen Zuordnung"""

    st.subheader("📭 Unzugeordnete Emails")

    emails = email_service.unzugeordnete_emails()

    if not emails:
        st.info("Keine unzugeordneten Emails vorhanden.")
        return

    st.warning(f"⚠️ {len(emails)} Email(s) ohne Akten-Zuordnung")

    # Projekte für Zuordnung laden
    projekte = db.query(UnfallProjekt).filter(
        UnfallProjekt.abgeschlossen == False
    ).order_by(UnfallProjekt.aktualisiert_am.desc()).limit(100).all()

    projekt_optionen = {
        f"{p.aktenzeichen or p.projektnummer}": p.id
        for p in projekte
    }

    for email in emails:
        with st.expander(f"📩 {email.betreff or '(Kein Betreff)'} - {email.von}"):
            st.write(f"**Datum:** {email.gesendet_am}")
            st.write(f"**Von:** {email.von}")

            if email.zuordnung_grund:
                st.info(f"🤖 Vorschlag: {email.zuordnung_grund} ({email.zuordnung_konfidenz}%)")

            # Projekt-Zuordnung
            col1, col2 = st.columns([3, 1])

            with col1:
                auswahl = st.selectbox(
                    "Akte zuordnen",
                    options=["-- Auswählen --"] + list(projekt_optionen.keys()),
                    key=f"zuordnung_{email.id}"
                )

            with col2:
                if st.button("✅ Zuordnen", key=f"btn_zuordnung_{email.id}"):
                    if auswahl and auswahl != "-- Auswählen --":
                        projekt_id = projekt_optionen[auswahl]
                        email_service.email_manuell_zuordnen(email.id, projekt_id)
                        db.commit()
                        st.success("Email zugeordnet!")
                        st.rerun()
