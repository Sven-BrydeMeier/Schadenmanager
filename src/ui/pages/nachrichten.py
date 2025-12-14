"""
Mandanten-Kommunikation (Chat/Nachrichten) UI-Seite
Interne Nachrichtenverwaltung
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.nachrichten import NachrichtenService, Nachricht, NachrichtPrioritaet


def render_nachrichten():
    """Rendert die Nachrichten-Seite"""
    st.title("💬 Nachrichten")

    user_id = st.session_state.get("user_id")

    if not user_id:
        st.error("Bitte anmelden")
        return

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Posteingang", "Neue Nachricht", "Suche"
    ])

    with tab1:
        _render_posteingang(user_id)

    with tab2:
        _render_neue_nachricht(user_id)

    with tab3:
        _render_suche(user_id)


def _render_posteingang(user_id: int):
    """Zeigt den Posteingang mit Konversationen"""
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Konversationen")

        with get_session() as db:
            service = NachrichtenService(db)

            # Ungelesene Nachrichten
            ungelesen = service.ungelesene_nachrichten_zaehlen(user_id)
            if ungelesen > 0:
                st.info(f"📬 {ungelesen} ungelesene Nachricht(en)")

            konversationen = service.konversationen_fuer_user(user_id)

            if not konversationen:
                st.info("Keine Nachrichten")
                return

            # Konversationsliste
            selected_konv = st.session_state.get("selected_konversation")

            for konv in konversationen:
                partner = konv.get("partner")
                partner_name = partner.email if partner else "System"
                ungelesen_count = konv.get("ungelesen", 0)

                label = f"{'🔵 ' if ungelesen_count > 0 else ''}{partner_name}"
                if ungelesen_count > 0:
                    label += f" ({ungelesen_count})"

                if st.button(label, key=f"konv_{konv['konversation_id']}", use_container_width=True):
                    st.session_state["selected_konversation"] = konv['konversation_id']
                    st.rerun()

    with col2:
        selected_konv = st.session_state.get("selected_konversation")

        if selected_konv:
            _render_konversation(user_id, selected_konv)
        else:
            st.info("Wählen Sie eine Konversation aus der Liste")


def _render_konversation(user_id: int, konversation_id: str):
    """Zeigt eine einzelne Konversation"""
    st.subheader("Chatverlauf")

    with get_session() as db:
        service = NachrichtenService(db)

        # Nachrichten als gelesen markieren
        service.nachrichten_als_gelesen_markieren(konversation_id, user_id)

        # Nachrichten laden
        nachrichten = service.nachrichten_fuer_konversation(konversation_id)
        nachrichten.reverse()  # Älteste zuerst

        # Chat-Container
        chat_container = st.container()

        with chat_container:
            for nachricht in nachrichten:
                ist_eigene = nachricht.absender_user_id == user_id

                # Chat-Bubble
                if ist_eigene:
                    col1, col2 = st.columns([1, 4])
                    with col2:
                        with st.chat_message("user"):
                            if nachricht.prioritaet_anzeige:
                                st.write(nachricht.prioritaet_anzeige)
                            st.write(nachricht.inhalt)
                            st.caption(nachricht.erstellt_am.strftime("%d.%m.%Y %H:%M"))
                else:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        with st.chat_message("assistant"):
                            if nachricht.absender:
                                st.caption(f"Von: {nachricht.absender.email}")
                            if nachricht.prioritaet_anzeige:
                                st.write(nachricht.prioritaet_anzeige)
                            st.write(nachricht.inhalt)
                            st.caption(nachricht.erstellt_am.strftime("%d.%m.%Y %H:%M"))

        # Antwort-Formular
        st.markdown("---")

        with st.form("antwort_form", clear_on_submit=True):
            antwort = st.text_area("Ihre Antwort", height=100, key="reply_text")

            prioritaet = st.selectbox(
                "Priorität",
                [NachrichtPrioritaet.NORMAL, NachrichtPrioritaet.WICHTIG, NachrichtPrioritaet.DRINGEND],
                format_func=lambda p: {
                    NachrichtPrioritaet.NORMAL: "Normal",
                    NachrichtPrioritaet.WICHTIG: "⚠️ Wichtig",
                    NachrichtPrioritaet.DRINGEND: "🔴 Dringend"
                }.get(p, str(p))
            )

            if st.form_submit_button("Senden", type="primary"):
                if antwort:
                    # Partner finden
                    letzte = nachrichten[-1] if nachrichten else None
                    if letzte:
                        if letzte.absender_user_id == user_id:
                            empfaenger_id = letzte.empfaenger_user_id
                        else:
                            empfaenger_id = letzte.absender_user_id

                        service.nachricht_senden(
                            absender_user_id=user_id,
                            empfaenger_user_id=empfaenger_id,
                            inhalt=antwort,
                            prioritaet=prioritaet,
                            projekt_id=letzte.projekt_id
                        )
                        st.success("Nachricht gesendet!")
                        st.rerun()
                else:
                    st.warning("Bitte Nachricht eingeben")


def _render_neue_nachricht(user_id: int):
    """Formular für neue Nachricht"""
    st.subheader("Neue Nachricht verfassen")

    with get_session() as db:
        from src.models import User

        # Alle Benutzer laden (außer sich selbst)
        users = db.query(User).filter(User.id != user_id, User.ist_aktiv == True).all()

        if not users:
            st.warning("Keine anderen Benutzer verfügbar")
            return

        with st.form("neue_nachricht"):
            empfaenger_options = {u.id: f"{u.name or u.email} ({u.rolle})" for u in users}
            empfaenger_id = st.selectbox(
                "Empfänger *",
                list(empfaenger_options.keys()),
                format_func=lambda x: empfaenger_options.get(x, "")
            )

            # Projekt-Zuordnung (optional)
            from src.models import UnfallProjekt
            projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).limit(50).all()

            projekt_options = {p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}" for p in projekte}
            projekt_id = st.selectbox(
                "Projekt zuordnen (optional)",
                [None] + list(projekt_options.keys()),
                format_func=lambda x: "-- Kein Projekt --" if x is None else projekt_options.get(x, "")
            )

            betreff = st.text_input("Betreff")

            prioritaet = st.selectbox(
                "Priorität",
                [NachrichtPrioritaet.NORMAL, NachrichtPrioritaet.WICHTIG, NachrichtPrioritaet.DRINGEND],
                format_func=lambda p: {
                    NachrichtPrioritaet.NORMAL: "Normal",
                    NachrichtPrioritaet.WICHTIG: "⚠️ Wichtig",
                    NachrichtPrioritaet.DRINGEND: "🔴 Dringend"
                }.get(p, str(p))
            )

            inhalt = st.text_area("Nachricht *", height=200)

            submitted = st.form_submit_button("Nachricht senden", type="primary")

            if submitted:
                if not inhalt:
                    st.error("Bitte Nachricht eingeben")
                else:
                    service = NachrichtenService(db)

                    nachricht = service.nachricht_senden(
                        absender_user_id=user_id,
                        empfaenger_user_id=empfaenger_id,
                        inhalt=inhalt,
                        betreff=betreff,
                        prioritaet=prioritaet,
                        projekt_id=projekt_id
                    )

                    st.success("Nachricht wurde gesendet!")


def _render_suche(user_id: int):
    """Nachrichten-Suche"""
    st.subheader("Nachrichten durchsuchen")

    suchbegriff = st.text_input("Suchbegriff", placeholder="Suchen in Nachrichten...")

    if suchbegriff and len(suchbegriff) >= 2:
        with get_session() as db:
            service = NachrichtenService(db)
            ergebnisse = service.suche_nachrichten(user_id, suchbegriff)

            if ergebnisse:
                st.write(f"**{len(ergebnisse)} Ergebnis(se) gefunden:**")

                for nachricht in ergebnisse:
                    with st.expander(f"{nachricht.erstellt_am.strftime('%d.%m.%Y %H:%M')} - {nachricht.betreff or 'Kein Betreff'}"):
                        if nachricht.absender:
                            st.caption(f"Von: {nachricht.absender.email}")
                        st.write(nachricht.inhalt)

                        if st.button("Zur Konversation", key=f"goto_{nachricht.id}"):
                            st.session_state["selected_konversation"] = nachricht.konversation_id
                            st.session_state["page"] = "Nachrichten"
                            st.rerun()
            else:
                st.info("Keine Nachrichten gefunden")
    elif suchbegriff:
        st.caption("Bitte mindestens 2 Zeichen eingeben")
