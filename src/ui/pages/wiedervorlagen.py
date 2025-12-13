"""
Wiedervorlagen/Fristen-Verwaltung
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, Wiedervorlage, WiedervorlageTyp, WiedervorlagePrioritaet
)
from src.ui.components import badge
from src.config.database import get_session


def render_wiedervorlagen():
    """Rendert die Wiedervorlagen-Verwaltung"""

    st.markdown("## Wiedervorlagen & Fristen")

    user_id = st.session_state.get("user_id")
    rolle = st.session_state.get("user_rolle")

    tabs = st.tabs(["Übersicht", "Neue Wiedervorlage", "Kalender"])

    with tabs[0]:
        _render_uebersicht(user_id, rolle)

    with tabs[1]:
        _render_neue_wiedervorlage()

    with tabs[2]:
        _render_kalender_ansicht(user_id, rolle)


def _render_uebersicht(user_id: int, rolle: str):
    """Rendert die Übersicht der Wiedervorlagen"""

    with get_session() as db:
        # Filter
        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox(
                "Status",
                ["Offen", "Überfällig", "Alle", "Erledigt"],
                index=0
            )

        with col2:
            typ_filter = st.selectbox(
                "Typ",
                ["Alle"] + [t.value for t in WiedervorlageTyp],
                index=0
            )

        with col3:
            prioritaet_filter = st.selectbox(
                "Priorität",
                ["Alle"] + [p.value for p in WiedervorlagePrioritaet],
                index=0
            )

        # Query erstellen
        query = db.query(Wiedervorlage).join(UnfallProjekt)

        # Rollenbasierte Filterung
        if rolle == "ANWALT":
            query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
        elif rolle == "WERKSTATT":
            query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)
        elif rolle == "GUTACHTER":
            query = query.filter(UnfallProjekt.gutachter_user_id == user_id)
        # ADMIN sieht alle

        # Status-Filter
        if status_filter == "Offen":
            query = query.filter(Wiedervorlage.erledigt == False)
        elif status_filter == "Überfällig":
            query = query.filter(
                Wiedervorlage.erledigt == False,
                Wiedervorlage.faellig_am < datetime.now()
            )
        elif status_filter == "Erledigt":
            query = query.filter(Wiedervorlage.erledigt == True)

        # Typ-Filter
        if typ_filter != "Alle":
            query = query.filter(Wiedervorlage.typ == WiedervorlageTyp(typ_filter))

        # Prioritäts-Filter
        if prioritaet_filter != "Alle":
            query = query.filter(Wiedervorlage.prioritaet == WiedervorlagePrioritaet(prioritaet_filter))

        # Sortierung: Überfällige zuerst, dann nach Fälligkeit
        query = query.order_by(Wiedervorlage.erledigt, Wiedervorlage.faellig_am)

        wiedervorlagen = query.all()

        st.markdown("---")

        # Statistik
        col1, col2, col3, col4 = st.columns(4)

        offen = len([w for w in wiedervorlagen if not w.erledigt])
        ueberfaellig = len([w for w in wiedervorlagen if w.ist_ueberfaellig])
        heute = len([w for w in wiedervorlagen if not w.erledigt and w.tage_bis_faellig == 0])
        diese_woche = len([w for w in wiedervorlagen if not w.erledigt and 0 < w.tage_bis_faellig <= 7])

        with col1:
            st.metric("Offen", offen)
        with col2:
            st.metric("Überfällig", ueberfaellig, delta=f"-{ueberfaellig}" if ueberfaellig > 0 else None, delta_color="inverse")
        with col3:
            st.metric("Heute fällig", heute)
        with col4:
            st.metric("Diese Woche", diese_woche)

        st.markdown("---")

        if not wiedervorlagen:
            st.info("Keine Wiedervorlagen gefunden.")
            return

        # Liste anzeigen
        for wv in wiedervorlagen:
            _render_wiedervorlage_karte(db, wv)


def _render_wiedervorlage_karte(db: Session, wv: Wiedervorlage):
    """Rendert eine Wiedervorlage-Karte"""

    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

        with col1:
            # Titel mit Prioritäts-Indikator
            prio_icons = {
                WiedervorlagePrioritaet.KRITISCH: "🔴",
                WiedervorlagePrioritaet.HOCH: "🟠",
                WiedervorlagePrioritaet.NORMAL: "🟡",
                WiedervorlagePrioritaet.NIEDRIG: "🟢"
            }
            icon = prio_icons.get(wv.prioritaet, "")

            if wv.erledigt:
                st.markdown(f"~~{icon} **{wv.titel}**~~")
            else:
                st.markdown(f"{icon} **{wv.titel}**")

            st.caption(f"Akte: {wv.projekt.aktenzeichen or wv.projekt.projektnummer}")

            if wv.beschreibung:
                st.caption(wv.beschreibung[:100] + "..." if len(wv.beschreibung) > 100 else wv.beschreibung)

        with col2:
            # Fälligkeit
            if wv.ist_ueberfaellig:
                st.markdown(badge(f"Überfällig ({abs(wv.tage_bis_faellig)} Tage)", "danger"), unsafe_allow_html=True)
            elif wv.tage_bis_faellig == 0:
                st.markdown(badge("Heute fällig", "warning"), unsafe_allow_html=True)
            elif wv.tage_bis_faellig <= 3:
                st.markdown(badge(f"In {wv.tage_bis_faellig} Tag(en)", "warning"), unsafe_allow_html=True)
            elif wv.erledigt:
                st.markdown(badge("Erledigt", "success"), unsafe_allow_html=True)
            else:
                st.markdown(badge(f"In {wv.tage_bis_faellig} Tagen", "info"), unsafe_allow_html=True)

            st.caption(f"Fällig: {wv.faellig_am.strftime('%d.%m.%Y')}")
            st.caption(f"Typ: {wv.typ_anzeige}")

        with col3:
            if not wv.erledigt:
                if st.button("Erledigt", key=f"erledigt_{wv.id}", type="primary"):
                    wv.erledigt = True
                    wv.erledigt_am = datetime.now()
                    wv.erledigt_von_user_id = st.session_state.get("user_id")
                    db.flush()
                    st.rerun()

        with col4:
            if st.button("Löschen", key=f"loeschen_{wv.id}"):
                db.delete(wv)
                db.flush()
                st.rerun()

        st.markdown("---")


def _render_neue_wiedervorlage():
    """Rendert das Formular für neue Wiedervorlagen"""

    st.markdown("### Neue Wiedervorlage anlegen")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    with get_session() as db:
        # Projekt auswählen oder aktives verwenden
        if aktives_projekt_id:
            projekt = db.query(UnfallProjekt).filter(
                UnfallProjekt.id == aktives_projekt_id
            ).first()
            if projekt:
                st.info(f"Für Projekt: {projekt.aktenzeichen or projekt.projektnummer}")
                projekt_id = projekt.id
            else:
                st.warning("Aktives Projekt nicht gefunden.")
                return
        else:
            # Projektauswahl anzeigen
            rolle = st.session_state.get("user_rolle")
            user_id = st.session_state.get("user_id")

            query = db.query(UnfallProjekt)
            if rolle == "ANWALT":
                query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
            elif rolle == "WERKSTATT":
                query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)

            projekte = query.all()

            if not projekte:
                st.warning("Keine Projekte verfügbar.")
                return

            projekt_optionen = {
                f"{p.aktenzeichen or p.projektnummer}": p.id
                for p in projekte
            }

            ausgewaehltes = st.selectbox("Projekt auswählen", list(projekt_optionen.keys()))
            projekt_id = projekt_optionen.get(ausgewaehltes)

        # Formular
        with st.form("neue_wiedervorlage"):
            col1, col2 = st.columns(2)

            with col1:
                titel = st.text_input("Titel*", placeholder="z.B. Nachfassen bei Versicherung")

                typ = st.selectbox(
                    "Typ",
                    options=[t.value for t in WiedervorlageTyp],
                    format_func=lambda x: {
                        "FRIST": "Frist",
                        "ERINNERUNG": "Erinnerung",
                        "TERMIN": "Termin",
                        "NACHFASSEN": "Nachfassen",
                        "ZAHLUNG": "Zahlungsfrist"
                    }.get(x, x)
                )

            with col2:
                faellig_am = st.date_input(
                    "Fällig am*",
                    value=datetime.now() + timedelta(days=7)
                )

                prioritaet = st.selectbox(
                    "Priorität",
                    options=[p.value for p in WiedervorlagePrioritaet],
                    index=1,  # Normal als Standard
                    format_func=lambda x: {
                        "NIEDRIG": "Niedrig",
                        "NORMAL": "Normal",
                        "HOCH": "Hoch",
                        "KRITISCH": "Kritisch"
                    }.get(x, x)
                )

            beschreibung = st.text_area("Beschreibung (optional)")

            col1, col2 = st.columns(2)

            with col1:
                erinnerung_tage = st.number_input(
                    "Erinnerung Tage vorher",
                    min_value=0,
                    max_value=30,
                    value=3
                )

            with col2:
                email_benachrichtigung = st.checkbox("E-Mail-Benachrichtigung", value=True)

            submitted = st.form_submit_button("Wiedervorlage anlegen", use_container_width=True)

            if submitted:
                if not titel:
                    st.error("Bitte einen Titel eingeben.")
                elif not faellig_am:
                    st.error("Bitte ein Fälligkeitsdatum angeben.")
                else:
                    wv = Wiedervorlage(
                        unfallprojekt_id=projekt_id,
                        erstellt_von_user_id=st.session_state.get("user_id"),
                        zugewiesen_an_user_id=st.session_state.get("user_id"),
                        typ=WiedervorlageTyp(typ),
                        prioritaet=WiedervorlagePrioritaet(prioritaet),
                        titel=titel,
                        beschreibung=beschreibung,
                        faellig_am=datetime.combine(faellig_am, datetime.min.time()),
                        erinnerung_tage_vorher=erinnerung_tage,
                        email_benachrichtigung=email_benachrichtigung
                    )

                    # Erinnerungsdatum berechnen
                    if erinnerung_tage > 0:
                        wv.erinnerung_am = wv.faellig_am - timedelta(days=erinnerung_tage)

                    db.add(wv)
                    db.flush()

                    st.success("Wiedervorlage wurde angelegt!")
                    st.rerun()


def _render_kalender_ansicht(user_id: int, rolle: str):
    """Rendert eine einfache Kalenderansicht"""

    st.markdown("### Kalenderübersicht")

    with get_session() as db:
        # Query für die nächsten 30 Tage
        heute = datetime.now()
        in_30_tagen = heute + timedelta(days=30)

        query = db.query(Wiedervorlage).join(UnfallProjekt).filter(
            Wiedervorlage.erledigt == False,
            Wiedervorlage.faellig_am >= heute,
            Wiedervorlage.faellig_am <= in_30_tagen
        )

        # Rollenbasierte Filterung
        if rolle == "ANWALT":
            query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
        elif rolle == "WERKSTATT":
            query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)
        elif rolle == "GUTACHTER":
            query = query.filter(UnfallProjekt.gutachter_user_id == user_id)

        wiedervorlagen = query.order_by(Wiedervorlage.faellig_am).all()

        if not wiedervorlagen:
            st.info("Keine anstehenden Wiedervorlagen in den nächsten 30 Tagen.")
            return

        # Nach Wochen gruppieren
        woche_aktuell = heute.isocalendar()[1]

        st.markdown("#### Diese Woche")
        diese_woche = [w for w in wiedervorlagen if w.faellig_am.isocalendar()[1] == woche_aktuell]

        if diese_woche:
            for wv in diese_woche:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**{wv.faellig_am.strftime('%d.%m.')}**")
                with col2:
                    st.write(f"{wv.titel} ({wv.projekt.aktenzeichen or wv.projekt.projektnummer})")
        else:
            st.caption("Keine Termine diese Woche")

        st.markdown("---")
        st.markdown("#### Nächste Woche")
        naechste_woche = [w for w in wiedervorlagen if w.faellig_am.isocalendar()[1] == woche_aktuell + 1]

        if naechste_woche:
            for wv in naechste_woche:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**{wv.faellig_am.strftime('%d.%m.')}**")
                with col2:
                    st.write(f"{wv.titel} ({wv.projekt.aktenzeichen or wv.projekt.projektnummer})")
        else:
            st.caption("Keine Termine nächste Woche")

        st.markdown("---")
        st.markdown("#### Später")
        spaeter = [w for w in wiedervorlagen if w.faellig_am.isocalendar()[1] > woche_aktuell + 1]

        if spaeter:
            for wv in spaeter:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**{wv.faellig_am.strftime('%d.%m.')}**")
                with col2:
                    st.write(f"{wv.titel} ({wv.projekt.aktenzeichen or wv.projekt.projektnummer})")
        else:
            st.caption("Keine weiteren Termine")
