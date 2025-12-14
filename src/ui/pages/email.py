"""
E-Mail-Integration UI-Seite
E-Mail-Verwaltung und automatische Zuordnung
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.email_integration import (
    EmailIntegrationService, EmailStatus, EmailPrioritaet,
    Email, EmailKonto, EmailVorlage
)


def render_email():
    """Rendert die E-Mail-Seite"""
    st.title("📧 E-Mail-Integration")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Posteingang", "Unzugeordnet", "Vorlagen", "Einstellungen"
    ])

    with tab1:
        _render_posteingang()

    with tab2:
        _render_unzugeordnet()

    with tab3:
        _render_vorlagen()

    with tab4:
        _render_einstellungen()


def _render_posteingang():
    """E-Mail Posteingang"""
    st.subheader("Posteingang")

    with get_session() as db:
        service = EmailIntegrationService(db)
        statistik = service.email_statistik()

        # Metriken
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Gesamt", statistik['gesamt'])
        with col2:
            st.metric("Ungelesen", statistik['ungelesen'])
        with col3:
            st.metric("Unzugeordnet", statistik['unzugeordnet'])
        with col4:
            st.metric("Dringend", statistik['dringend'])

        st.markdown("---")

        # E-Mails laden
        emails = db.query(Email).filter(
            Email.richtung.in_(['EINGANG'])
        ).order_by(Email.empfangen_am.desc()).limit(50).all()

        if not emails:
            st.info("Keine E-Mails vorhanden")

            # Demo-Import
            st.markdown("### Demo-E-Mail importieren")
            if st.button("📥 Demo-E-Mail erstellen"):
                demo_email = service.email_importieren(
                    konto_id=1,
                    von="versicherung@demo.de",
                    an="kanzlei@demo.de",
                    betreff="Schadenmeldung - Az. 2024-001",
                    text_inhalt="Sehr geehrte Damen und Herren,\n\nanbei übersenden wir die Regulierungszusage..."
                )
                db.commit()
                st.success("Demo-E-Mail erstellt")
                st.rerun()
            return

        for email in emails:
            prioritaet_icon = {
                EmailPrioritaet.DRINGEND: "🔴",
                EmailPrioritaet.HOCH: "🟠",
                EmailPrioritaet.NORMAL: "🔵",
                EmailPrioritaet.NIEDRIG: "⚪"
            }.get(email.prioritaet, "⚪")

            gelesen_icon = "📭" if email.gelesen else "📬"

            with st.expander(
                f"{gelesen_icon} {prioritaet_icon} {email.betreff or '(Kein Betreff)'} - "
                f"{email.von[:30]}..."
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Von:** {email.von}")
                    st.write(f"**An:** {email.an}")
                    st.write(f"**Datum:** {email.empfangen_am.strftime('%d.%m.%Y %H:%M') if email.empfangen_am else '-'}")

                with col2:
                    st.write(f"**Status:** {email.status.value if email.status else '-'}")
                    st.write(f"**Priorität:** {email.prioritaet.value if email.prioritaet else '-'}")
                    if email.projekt_id:
                        st.write(f"**Projekt:** {email.projekt_id}")
                        if email.auto_zugeordnet:
                            st.caption(f"Auto-zugeordnet: {email.zuordnung_grund}")

                st.markdown("**Inhalt:**")
                st.text_area(
                    "E-Mail-Text",
                    value=email.text_inhalt or "",
                    height=150,
                    disabled=True,
                    key=f"text_{email.id}"
                )

                # Aktionen
                col_a1, col_a2, col_a3 = st.columns(3)

                with col_a1:
                    if not email.gelesen:
                        if st.button("✅ Als gelesen", key=f"read_{email.id}"):
                            service.email_als_gelesen_markieren(email.id)
                            db.commit()
                            st.rerun()

                with col_a2:
                    if not email.projekt_id:
                        if st.button("🔗 Zuordnen", key=f"assign_{email.id}"):
                            st.session_state[f"assign_email_{email.id}"] = True

                with col_a3:
                    if st.button("🗑️ Archivieren", key=f"arch_{email.id}"):
                        email.status = EmailStatus.ARCHIVIERT
                        db.commit()
                        st.rerun()


def _render_unzugeordnet():
    """Unzugeordnete E-Mails"""
    st.subheader("Unzugeordnete E-Mails")

    with get_session() as db:
        service = EmailIntegrationService(db)
        unzugeordnet = service.unzugeordnete_emails()

        if not unzugeordnet:
            st.success("Alle E-Mails sind zugeordnet!")
            return

        st.warning(f"{len(unzugeordnet)} E-Mail(s) ohne Projektzuordnung")

        from src.models import UnfallProjekt
        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        projekt_options = {0: "--- Projekt wählen ---"}
        projekt_options.update({
            p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
            for p in projekte
        })

        for email in unzugeordnet:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.write(f"**{email.betreff or '(Kein Betreff)'}**")
                    st.caption(f"Von: {email.von}")

                with col2:
                    projekt_id = st.selectbox(
                        "Projekt",
                        list(projekt_options.keys()),
                        format_func=lambda x: projekt_options.get(x, ""),
                        key=f"proj_{email.id}"
                    )

                with col3:
                    if st.button("🔗 Zuordnen", key=f"zu_{email.id}"):
                        if projekt_id > 0:
                            service.email_manuell_zuordnen(email.id, projekt_id)
                            db.commit()
                            st.success("Zugeordnet!")
                            st.rerun()

                st.markdown("---")


def _render_vorlagen():
    """E-Mail-Vorlagen"""
    st.subheader("E-Mail-Vorlagen")

    with get_session() as db:
        service = EmailIntegrationService(db)
        vorlagen = service.alle_vorlagen()

        # Neue Vorlage
        with st.expander("➕ Neue Vorlage erstellen"):
            bezeichnung = st.text_input("Bezeichnung")
            kategorie = st.selectbox(
                "Kategorie",
                ["Versicherung", "Mahnung", "Gutachter", "Allgemein"]
            )
            betreff = st.text_input("Betreff-Vorlage", placeholder="Schadenmeldung - Az. {{aktenzeichen}}")
            text = st.text_area(
                "Text-Vorlage",
                height=200,
                placeholder="Verwenden Sie {{platzhalter}} für dynamische Inhalte"
            )

            st.caption("Verfügbare Platzhalter: {{aktenzeichen}}, {{mandant_name}}, {{unfalldatum}}, {{kennzeichen}}, ...")

            if st.button("💾 Vorlage speichern"):
                if bezeichnung and text:
                    vorlage = service.vorlage_erstellen(
                        bezeichnung=bezeichnung,
                        betreff_vorlage=betreff,
                        text_vorlage=text,
                        kategorie=kategorie
                    )
                    db.commit()
                    st.success("Vorlage erstellt!")
                    st.rerun()

        st.markdown("---")

        # Vorhandene Vorlagen
        if not vorlagen:
            st.info("Noch keine Vorlagen vorhanden")

            if st.button("📥 Standard-Vorlagen importieren"):
                from src.services.email_integration import STANDARD_VORLAGEN
                for v in STANDARD_VORLAGEN:
                    service.vorlage_erstellen(
                        bezeichnung=v['bezeichnung'],
                        betreff_vorlage=v['betreff'],
                        text_vorlage=v['text'],
                        kategorie=v['kategorie']
                    )
                db.commit()
                st.success("Standard-Vorlagen importiert!")
                st.rerun()
            return

        for vorlage in vorlagen:
            with st.expander(f"📝 {vorlage.bezeichnung}"):
                st.write(f"**Kategorie:** {vorlage.kategorie or '-'}")
                st.write(f"**Betreff:** {vorlage.betreff_vorlage or '-'}")
                st.text_area(
                    "Text",
                    value=vorlage.text_vorlage or "",
                    height=150,
                    disabled=True,
                    key=f"vorl_{vorlage.id}"
                )

                if vorlage.platzhalter:
                    st.caption(f"Platzhalter: {', '.join(vorlage.platzhalter)}")


def _render_einstellungen():
    """E-Mail-Konten Einstellungen"""
    st.subheader("E-Mail-Konten")

    st.info("""
    Konfigurieren Sie hier Ihre E-Mail-Konten für den automatischen Abruf.
    In der Demo-Version ist diese Funktion simuliert.
    """)

    with get_session() as db:
        konten = db.query(EmailKonto).all()

        if not konten:
            st.warning("Noch keine E-Mail-Konten konfiguriert")

        # Neues Konto
        with st.expander("➕ Neues E-Mail-Konto hinzufügen"):
            col1, col2 = st.columns(2)

            with col1:
                bezeichnung = st.text_input("Bezeichnung", placeholder="Hauptkonto")
                email = st.text_input("E-Mail-Adresse", placeholder="kanzlei@beispiel.de")
                imap_server = st.text_input("IMAP-Server", placeholder="imap.beispiel.de")

            with col2:
                smtp_server = st.text_input("SMTP-Server", placeholder="smtp.beispiel.de")
                benutzername = st.text_input("Benutzername")
                passwort = st.text_input("Passwort", type="password")

            if st.button("💾 Konto speichern"):
                if bezeichnung and email:
                    service = EmailIntegrationService(db)
                    konto = service.konto_erstellen(
                        bezeichnung=bezeichnung,
                        email_adresse=email,
                        imap_server=imap_server or "",
                        smtp_server=smtp_server or "",
                        benutzername=benutzername or "",
                        passwort=passwort or ""
                    )
                    db.commit()
                    st.success("Konto erstellt!")
                    st.rerun()

        # Vorhandene Konten
        for konto in konten:
            with st.expander(f"📧 {konto.bezeichnung} ({konto.email_adresse})"):
                st.write(f"**IMAP:** {konto.imap_server}")
                st.write(f"**SMTP:** {konto.smtp_server}")
                st.write(f"**Status:** {'Aktiv' if konto.aktiv else 'Inaktiv'}")
                st.write(f"**Letzter Abruf:** {konto.letzter_abruf.strftime('%d.%m.%Y %H:%M') if konto.letzter_abruf else 'Noch nie'}")
