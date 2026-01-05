"""
Dokumenten-Chat UI-Seite
KI-gestützter Chat mit Dokumenten, Akten und der Datenbank
"""
import streamlit as st
from datetime import datetime
import json

from src.config.database import get_session
from src.models import UnfallProjekt, Rollen, SchreibenTyp, EmpfaengerTyp
from src.services.dokumenten_chat import DokumentenChatService


def render_dokumenten_chat():
    """Rendert die Dokumenten-Chat-Seite"""
    st.title("💬 Dokumenten-Chat")

    # Benutzer-Rolle aus Session
    user_rolle = st.session_state.get('user_rolle', Rollen.UNFALLOPFER)
    user_id = st.session_state.get('user_id', 1)

    ist_anwalt = user_rolle == Rollen.ANWALT

    # Info-Box basierend auf Rolle
    if ist_anwalt:
        st.info("""
        **Anwalts-Modus**: Chatten Sie mit Ihren Akten und Dokumenten.
        Erhalten Sie Vorschläge für das weitere Vorgehen und generieren Sie
        Schreiben an Versicherungen, Mandanten und andere Beteiligte.
        """)
    else:
        st.info("""
        Stellen Sie Fragen zu Ihrem Fall und Ihren Dokumenten.
        Der KI-Assistent hilft Ihnen, den Stand Ihres Verfahrens zu verstehen.
        """)

    # Projekt-Auswahl
    projekt = _render_projekt_auswahl(user_rolle, user_id)

    if not projekt:
        return

    # Session State für Chat initialisieren
    chat_key = f"chat_{projekt.id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = {
            "messages": [],
            "generiertes_schreiben": None
        }

    # Layout: Chat und Sidebar
    if ist_anwalt:
        col_chat, col_sidebar = st.columns([2, 1])
    else:
        col_chat = st.container()
        col_sidebar = None

    with col_chat:
        _render_chat_bereich(projekt, user_id, user_rolle, chat_key)

    if col_sidebar and ist_anwalt:
        with col_sidebar:
            _render_anwalt_sidebar(projekt, user_id, chat_key)


def _render_projekt_auswahl(user_rolle: Rollen, user_id: int):
    """Rendert die Projekt-Auswahl"""
    with get_session() as db:
        # Projekte laden (gefiltert nach Rolle)
        query = db.query(UnfallProjekt)

        if user_rolle == Rollen.UNFALLOPFER:
            # Nur eigene Projekte
            query = query.filter(UnfallProjekt.unfallopfer_id == user_id)
        elif user_rolle == Rollen.ANWALT:
            # Projekte des Anwalts
            query = query.filter(UnfallProjekt.anwalt_id == user_id)

        projekte = query.order_by(UnfallProjekt.erstellt_am.desc()).limit(100).all()

        if not projekte:
            st.warning("Keine Projekte gefunden.")
            return None

        # Projekt-Auswahl
        projekt_options = {}
        for p in projekte:
            label = f"{p.projektnummer}"
            if p.aktenzeichen:
                label += f" ({p.aktenzeichen})"
            if p.datum_unfall:
                label += f" - Unfall: {p.datum_unfall.strftime('%d.%m.%Y')}"
            projekt_options[p.id] = label

        selected_id = st.selectbox(
            "📁 Akte auswählen",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, ""),
            help="Wählen Sie die Akte, zu der Sie chatten möchten"
        )

        # Projekt neu laden für aktuelle Session
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == selected_id
        ).first()

        # Projekt-Info anzeigen
        if projekt:
            with st.expander("📋 Akten-Details", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Status", projekt.status.value if projekt.status else "Offen")
                with col2:
                    docs_count = len(projekt.dokumente) if projekt.dokumente else 0
                    st.metric("Dokumente", docs_count)
                with col3:
                    kosten_summe = sum(
                        kp.betrag_brutto or 0
                        for kp in projekt.kostenpositionen
                    ) if projekt.kostenpositionen else 0
                    st.metric("Schadenshöhe", f"{kosten_summe:,.2f} €")

        return projekt


def _render_chat_bereich(projekt, user_id: int, user_rolle: Rollen, chat_key: str):
    """Rendert den Chat-Bereich"""
    st.markdown("---")
    st.subheader("💬 Chat")

    chat_state = st.session_state[chat_key]

    # Chat-Verlauf aus DB laden (initial)
    if not chat_state["messages"]:
        with get_session() as db:
            service = DokumentenChatService(db)
            verlauf = service.get_chat_verlauf(projekt.id)
            for msg in verlauf:
                chat_state["messages"].append({
                    "role": msg["rolle"],
                    "content": msg["inhalt"],
                    "vorschlaege": msg.get("vorschlaege", []),
                    "quellen": msg.get("quellen", []),
                    "schreiben": msg.get("hat_schreiben", False)
                })

    # Willkommensnachricht wenn leer
    if not chat_state["messages"]:
        with st.chat_message("assistant"):
            if user_rolle == Rollen.ANWALT:
                st.markdown("""
                Guten Tag! Ich bin Ihr KI-Assistent für diese Akte.

                **Ich kann Ihnen helfen mit:**
                - Fragen zu Dokumenten und Sachstand
                - Zusammenfassungen der Akte
                - Generierung von Schreiben
                - Vorschläge für das weitere Vorgehen

                *Stellen Sie mir eine Frage oder nutzen Sie die Schreiben-Generierung rechts.*
                """)
            else:
                st.markdown("""
                Guten Tag! Ich bin Ihr KI-Assistent.

                **Ich kann Ihnen helfen:**
                - Den Stand Ihres Verfahrens zu erklären
                - Fragen zu Ihren Dokumenten zu beantworten
                - Rechtliche Begriffe verständlich zu erklären

                *Stellen Sie mir gerne eine Frage zu Ihrem Fall.*
                """)

    # Chat-Verlauf anzeigen
    for i, message in enumerate(chat_state["messages"]):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Vorschläge anzeigen (nur für Anwalt)
            if message.get("vorschlaege") and user_rolle == Rollen.ANWALT:
                st.markdown("---")
                st.markdown("**💡 Vorschläge:**")
                for vorschlag in message["vorschlaege"]:
                    st.markdown(f"• {vorschlag}")

            # Quellen anzeigen
            if message.get("quellen"):
                with st.expander("📎 Quellen"):
                    for quelle in message["quellen"]:
                        st.markdown(f"• Dokument {quelle}")

    # Eingabefeld
    if prompt := st.chat_input("Stellen Sie eine Frage zu dieser Akte..."):
        # User-Nachricht anzeigen
        with st.chat_message("user"):
            st.markdown(prompt)

        chat_state["messages"].append({
            "role": "user",
            "content": prompt
        })

        # Antwort generieren
        with st.chat_message("assistant"):
            with st.spinner("Denke nach..."):
                with get_session() as db:
                    service = DokumentenChatService(db)

                    # Chat-Verlauf für Kontext
                    verlauf_fuer_ki = [
                        {"role": m["role"], "content": m["content"]}
                        for m in chat_state["messages"][-10:]
                    ]

                    antwort = service.chat(
                        frage=prompt,
                        projekt_id=projekt.id,
                        user_id=user_id,
                        user_rolle=user_rolle,
                        chat_verlauf=verlauf_fuer_ki[:-1]  # Ohne aktuelle Frage
                    )

                st.markdown(antwort.antwort)

                # Vorschläge anzeigen
                if antwort.vorschlaege and user_rolle == Rollen.ANWALT:
                    st.markdown("---")
                    st.markdown("**💡 Vorschläge:**")
                    for vorschlag in antwort.vorschlaege:
                        st.markdown(f"• {vorschlag}")

                # Quellen anzeigen
                if antwort.quellen:
                    with st.expander("📎 Verwendete Quellen"):
                        for quelle in antwort.quellen:
                            st.markdown(f"• {quelle.get('dateiname', 'Dokument')} ({quelle.get('typ', '')})")

        # Antwort speichern
        chat_state["messages"].append({
            "role": "assistant",
            "content": antwort.antwort,
            "vorschlaege": antwort.vorschlaege,
            "quellen": [q.get("id") for q in antwort.quellen] if antwort.quellen else []
        })

        st.rerun()


def _render_anwalt_sidebar(projekt, user_id: int, chat_key: str):
    """Rendert die Anwalt-Sidebar mit Schreiben-Generierung"""
    st.markdown("---")
    st.subheader("📝 Schreiben generieren")

    chat_state = st.session_state[chat_key]

    # Schreiben-Typ auswählen
    schreiben_typ_options = {
        SchreibenTyp.ANSPRUCHSSCHREIBEN: "📋 Anspruchsschreiben",
        SchreibenTyp.KUERZUNGSERWIDERUNG: "↩️ Kürzungserwiderung",
        SchreibenTyp.MAHNUNG: "⚠️ Mahnung",
        SchreibenTyp.MANDANTENINFORMATION: "📧 Mandanteninformation",
        SchreibenTyp.ANFRAGE: "❓ Anfrage",
        SchreibenTyp.STELLUNGNAHME: "📄 Stellungnahme",
        SchreibenTyp.AUFFORDERUNG: "📢 Aufforderung",
        SchreibenTyp.FREIES_SCHREIBEN: "✏️ Freies Schreiben"
    }

    schreiben_typ = st.selectbox(
        "Art des Schreibens",
        list(schreiben_typ_options.keys()),
        format_func=lambda x: schreiben_typ_options.get(x, x.value)
    )

    # Empfänger auswählen
    empfaenger_options = {
        EmpfaengerTyp.VERSICHERUNG_GEGNER: "🏢 Gegnerische Versicherung",
        EmpfaengerTyp.VERSICHERUNG_EIGEN: "🏠 Eigene Versicherung",
        EmpfaengerTyp.MANDANT: "👤 Mandant",
        EmpfaengerTyp.POLIZEI: "👮 Polizei",
        EmpfaengerTyp.STAATSANWALTSCHAFT: "⚖️ Staatsanwaltschaft",
        EmpfaengerTyp.GEGNER: "🚗 Unfallgegner",
        EmpfaengerTyp.WERKSTATT: "🔧 Werkstatt",
        EmpfaengerTyp.GUTACHTER: "📋 Gutachter",
        EmpfaengerTyp.GERICHT: "🏛️ Gericht",
        EmpfaengerTyp.SONSTIG: "📝 Sonstiger Empfänger"
    }

    empfaenger_typ = st.selectbox(
        "Empfänger",
        list(empfaenger_options.keys()),
        format_func=lambda x: empfaenger_options.get(x, x.value)
    )

    # Zusätzliche Anweisungen
    zusatz = st.text_area(
        "Zusätzliche Anweisungen",
        placeholder="z.B. 'Betone die Dringlichkeit' oder 'Erwähne das Gutachten vom 15.01.'",
        height=100
    )

    # Generieren-Button
    if st.button("🚀 Schreiben generieren", type="primary", use_container_width=True):
        with st.spinner("Generiere Schreiben..."):
            with get_session() as db:
                service = DokumentenChatService(db)
                dokument, fehler = service.generiere_schreiben(
                    schreiben_typ=schreiben_typ,
                    empfaenger_typ=empfaenger_typ,
                    projekt_id=projekt.id,
                    user_id=user_id,
                    zusatz_anweisungen=zusatz if zusatz else None
                )

                if fehler:
                    st.error(f"Fehler: {fehler}")
                else:
                    chat_state["generiertes_schreiben"] = dokument
                    st.success("Schreiben generiert!")
                    st.rerun()

    # Generiertes Schreiben anzeigen
    if chat_state.get("generiertes_schreiben"):
        st.markdown("---")
        st.subheader("📄 Generiertes Schreiben")

        dokument = chat_state["generiertes_schreiben"]

        # Schreiben anzeigen
        with st.expander("📝 Inhalt anzeigen/bearbeiten", expanded=True):
            bearbeiteter_inhalt = st.text_area(
                "Inhalt",
                value=dokument.inhalt,
                height=400,
                label_visibility="collapsed"
            )

        # Aktionen
        st.markdown("**Aktionen:**")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📧 Per E-Mail senden", use_container_width=True):
                _render_email_dialog(projekt, dokument, user_id)

            if st.button("💾 Zur Akte speichern", use_container_width=True):
                with get_session() as db:
                    service = DokumentenChatService(db)
                    # Inhalt aktualisieren falls bearbeitet
                    dokument.inhalt = bearbeiteter_inhalt
                    saved_doc = service.speichere_zur_akte(
                        generiertes_dokument=dokument,
                        projekt_id=projekt.id,
                        user_id=user_id,
                        aktion="gespeichert"
                    )
                    if saved_doc:
                        st.success(f"Zur Akte gespeichert! (ID: {saved_doc.id})")
                        chat_state["generiertes_schreiben"] = None
                        st.rerun()

        with col2:
            if st.button("🖨️ Als PDF drucken", use_container_width=True):
                _render_pdf_export(projekt, dokument, bearbeiteter_inhalt, user_id)

            if st.button("🗑️ Verwerfen", use_container_width=True):
                chat_state["generiertes_schreiben"] = None
                st.rerun()


def _render_email_dialog(projekt, dokument, user_id: int):
    """Zeigt den E-Mail-Dialog"""
    st.markdown("---")
    st.subheader("📧 E-Mail senden")

    empfaenger_email = st.text_input(
        "Empfänger E-Mail",
        value=dokument.empfaenger_email or "",
        placeholder="empfaenger@example.de"
    )

    betreff = st.text_input(
        "Betreff",
        value=dokument.betreff or f"Az. {projekt.aktenzeichen or projekt.projektnummer}"
    )

    if st.button("📤 Jetzt senden", type="primary"):
        if not empfaenger_email:
            st.error("Bitte E-Mail-Adresse eingeben")
            return

        # E-Mail senden
        try:
            from src.services.email_service import EmailService

            email_service = EmailService()
            success = email_service.sende_email(
                empfaenger=empfaenger_email,
                betreff=betreff,
                inhalt=dokument.inhalt
            )

            if success:
                # Zur Akte speichern
                with get_session() as db:
                    service = DokumentenChatService(db)
                    service.speichere_zur_akte(
                        generiertes_dokument=dokument,
                        projekt_id=projekt.id,
                        user_id=user_id,
                        aktion="per_email_gesendet"
                    )
                st.success(f"E-Mail an {empfaenger_email} gesendet und zur Akte gespeichert!")
            else:
                st.error("Fehler beim E-Mail-Versand")
        except Exception as e:
            st.error(f"Fehler: {str(e)}")


def _render_pdf_export(projekt, dokument, inhalt: str, user_id: int):
    """Erstellt PDF-Export"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import cm
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2.5*cm,
            rightMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )

        styles = getSampleStyleSheet()
        story = []

        # Titel
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=20
        )
        story.append(Paragraph(
            f"{dokument.schreiben_typ.value} - Az. {projekt.aktenzeichen or projekt.projektnummer}",
            title_style
        ))

        # Inhalt
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=11,
            leading=14
        )

        # Text in Absätze aufteilen
        for paragraph in inhalt.split('\n\n'):
            if paragraph.strip():
                # Zeilenumbrüche durch <br/> ersetzen
                paragraph = paragraph.replace('\n', '<br/>')
                story.append(Paragraph(paragraph, body_style))
                story.append(Spacer(1, 0.5*cm))

        doc.build(story)

        # Download-Button
        pdf_bytes = buffer.getvalue()
        dateiname = f"{dokument.schreiben_typ.value.lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

        st.download_button(
            label="📥 PDF herunterladen",
            data=pdf_bytes,
            file_name=dateiname,
            mime="application/pdf",
            use_container_width=True
        )

        # Zur Akte speichern
        with get_session() as db:
            service = DokumentenChatService(db)
            service.speichere_zur_akte(
                generiertes_dokument=dokument,
                projekt_id=projekt.id,
                user_id=user_id,
                aktion="als_pdf_exportiert"
            )

        st.success("PDF erstellt und zur Akte gespeichert!")

    except Exception as e:
        st.error(f"PDF-Fehler: {str(e)}")
