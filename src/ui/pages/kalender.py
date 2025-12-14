"""
Terminkalender UI-Seite
Kalenderansicht für Termine und Gerichtstermine
"""
import streamlit as st
from datetime import datetime, date, timedelta
import calendar

from src.config.database import get_session
from src.services.kalender import KalenderService, Termin, TerminTyp, TerminStatus


def render_kalender():
    """Rendert die Kalender-Seite"""
    st.title("📅 Terminkalender")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Kalenderansicht", "Terminliste", "Neuer Termin", "iCal-Export"
    ])

    with tab1:
        _render_kalenderansicht()

    with tab2:
        _render_terminliste()

    with tab3:
        _render_neuer_termin()

    with tab4:
        _render_ical_export()


def _render_kalenderansicht():
    """Rendert die Kalenderansicht"""
    st.subheader("Monatsübersicht")

    # Monat/Jahr Auswahl
    col1, col2, col3 = st.columns([1, 1, 2])

    heute = date.today()

    with col1:
        monat = st.selectbox(
            "Monat",
            range(1, 13),
            index=heute.month - 1,
            format_func=lambda x: calendar.month_name[x]
        )

    with col2:
        jahr = st.selectbox(
            "Jahr",
            range(heute.year - 1, heute.year + 3),
            index=1
        )

    with get_session() as db:
        service = KalenderService(db)
        monats_uebersicht = service.kalender_monats_uebersicht(jahr, monat)

        # Kalendergitter erstellen
        cal = calendar.Calendar(firstweekday=0)  # Montag als erster Tag
        monatstage = cal.monthdayscalendar(jahr, monat)

        # Wochentags-Header
        wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        header_cols = st.columns(7)
        for i, tag in enumerate(wochentage):
            with header_cols[i]:
                st.markdown(f"**{tag}**")

        st.markdown("---")

        # Kalenderwochen
        for woche in monatstage:
            cols = st.columns(7)
            for i, tag_num in enumerate(woche):
                with cols[i]:
                    if tag_num == 0:
                        st.write("")
                    else:
                        tag_datum = date(jahr, monat, tag_num)
                        tag_key = tag_datum.strftime("%Y-%m-%d")
                        termine = monats_uebersicht.get(tag_key, [])

                        # Tag-Styling
                        ist_heute = tag_datum == heute
                        ist_wochenende = i >= 5

                        if ist_heute:
                            st.markdown(f"**🔵 {tag_num}**")
                        elif ist_wochenende:
                            st.markdown(f"*{tag_num}*")
                        else:
                            st.write(f"{tag_num}")

                        # Termine anzeigen
                        for termin in termine[:3]:  # Max 3 pro Tag
                            farbe = _get_termin_farbe(termin.termin_typ)
                            if st.button(
                                f"{farbe} {termin.titel[:15]}...",
                                key=f"t_{termin.id}",
                                use_container_width=True
                            ):
                                st.session_state["selected_termin_id"] = termin.id

                        if len(termine) > 3:
                            st.caption(f"+{len(termine) - 3} weitere")


def _render_terminliste():
    """Rendert die Terminliste"""
    st.subheader("Anstehende Termine")

    col1, col2 = st.columns([1, 2])

    with col1:
        zeitraum = st.selectbox(
            "Zeitraum",
            ["Heute", "Diese Woche", "Dieser Monat", "Alle"],
            index=1
        )

    with col2:
        nur_gerichtstermine = st.checkbox("Nur Gerichtstermine")

    with get_session() as db:
        service = KalenderService(db)

        # Termine laden
        if zeitraum == "Heute":
            termine = service.heute_termine()
        elif zeitraum == "Diese Woche":
            termine = service.anstehende_termine(tage=7)
        elif zeitraum == "Dieser Monat":
            termine = service.anstehende_termine(tage=31)
        else:
            termine = service.termine_fuer_zeitraum(
                date.today() - timedelta(days=30),
                date.today() + timedelta(days=365)
            )

        if nur_gerichtstermine:
            termine = [t for t in termine if t.termin_typ == TerminTyp.GERICHTSTERMIN]

        if not termine:
            st.info("Keine Termine in diesem Zeitraum")
            return

        for termin in termine:
            with st.expander(
                f"{_get_termin_farbe(termin.termin_typ)} {termin.datum.strftime('%d.%m.%Y')} - {termin.titel}",
                expanded=termin.ist_heute
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Typ:** {termin.termin_typ_anzeige}")
                    st.write(f"**Status:** {termin.status_anzeige}")

                    if termin.uhrzeit_von:
                        zeit_text = termin.uhrzeit_von.strftime("%H:%M")
                        if termin.uhrzeit_bis:
                            zeit_text += f" - {termin.uhrzeit_bis.strftime('%H:%M')}"
                        st.write(f"**Zeit:** {zeit_text}")

                    if termin.ort:
                        st.write(f"**Ort:** {termin.ort}")

                with col2:
                    if termin.gericht_name:
                        st.write(f"**Gericht:** {termin.gericht_name}")
                        if termin.gericht_aktenzeichen:
                            st.write(f"**Az:** {termin.gericht_aktenzeichen}")
                        if termin.gericht_saal:
                            st.write(f"**Saal:** {termin.gericht_saal}")

                    if termin.tage_bis_termin >= 0:
                        if termin.tage_bis_termin == 0:
                            st.warning("Heute!")
                        elif termin.tage_bis_termin == 1:
                            st.warning("Morgen!")
                        else:
                            st.info(f"In {termin.tage_bis_termin} Tagen")

                if termin.beschreibung:
                    st.write("**Beschreibung:**")
                    st.write(termin.beschreibung)

                # Aktionen
                col1, col2, col3 = st.columns(3)

                with col1:
                    if termin.status != TerminStatus.WAHRGENOMMEN:
                        if st.button("✅ Erledigt", key=f"done_{termin.id}"):
                            service.termin_aktualisieren(
                                termin.id,
                                status=TerminStatus.WAHRGENOMMEN
                            )
                            st.rerun()

                with col2:
                    if st.button("✏️ Bearbeiten", key=f"edit_{termin.id}"):
                        st.session_state["edit_termin_id"] = termin.id

                with col3:
                    if st.button("🗑️ Löschen", key=f"del_{termin.id}"):
                        service.termin_loeschen(termin.id)
                        st.success("Termin gelöscht")
                        st.rerun()


def _render_neuer_termin():
    """Formular für neuen Termin"""
    st.subheader("Neuen Termin erstellen")

    with st.form("neuer_termin"):
        col1, col2 = st.columns(2)

        with col1:
            titel = st.text_input("Titel *", max_chars=200)

            termin_typ = st.selectbox(
                "Termintyp",
                [t for t in TerminTyp],
                format_func=lambda t: {
                    TerminTyp.GERICHTSTERMIN: "⚖️ Gerichtstermin",
                    TerminTyp.GUTACHTERTERMIN: "📋 Gutachtertermin",
                    TerminTyp.MANDANTENBESPRECHUNG: "👥 Mandantenbesprechung",
                    TerminTyp.WERKSTATTTERMIN: "🔧 Werkstatttermin",
                    TerminTyp.VERSICHERUNGSTERMIN: "🏢 Versicherungstermin",
                    TerminTyp.ORTSBESICHTIGUNG: "📍 Ortsbesichtigung",
                    TerminTyp.TELEFONTERMIN: "📞 Telefontermin",
                    TerminTyp.FRIST: "⏰ Frist",
                    TerminTyp.SONSTIGER: "📌 Sonstiger Termin"
                }.get(t, str(t))
            )

            datum = st.date_input("Datum *", value=date.today())

            ganztaegig = st.checkbox("Ganztägig")

        with col2:
            if not ganztaegig:
                uhrzeit_von = st.time_input("Von", value=None)
                uhrzeit_bis = st.time_input("Bis", value=None)
            else:
                uhrzeit_von = None
                uhrzeit_bis = None

            ort = st.text_input("Ort")

        # Gerichtsdaten (wenn Gerichtstermin)
        if termin_typ == TerminTyp.GERICHTSTERMIN:
            st.markdown("**Gerichtsdaten**")
            col1, col2, col3 = st.columns(3)

            with col1:
                gericht_name = st.text_input("Gericht")
            with col2:
                gericht_aktenzeichen = st.text_input("Aktenzeichen")
            with col3:
                gericht_saal = st.text_input("Saal")
        else:
            gericht_name = None
            gericht_aktenzeichen = None
            gericht_saal = None

        beschreibung = st.text_area("Beschreibung", height=100)

        # Projekt auswählen
        with get_session() as db:
            from src.models import UnfallProjekt
            projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).limit(50).all()

            projekt_options = {p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}" for p in projekte}
            projekt_id = st.selectbox(
                "Projekt zuordnen",
                [None] + list(projekt_options.keys()),
                format_func=lambda x: "-- Kein Projekt --" if x is None else projekt_options.get(x, "")
            )

        erinnerung = st.selectbox(
            "Erinnerung",
            [0, 15, 30, 60, 120, 1440],
            format_func=lambda x: {
                0: "Keine Erinnerung",
                15: "15 Minuten vorher",
                30: "30 Minuten vorher",
                60: "1 Stunde vorher",
                120: "2 Stunden vorher",
                1440: "1 Tag vorher"
            }.get(x, f"{x} Minuten vorher")
        )

        submitted = st.form_submit_button("Termin erstellen", type="primary")

        if submitted:
            if not titel or not projekt_id:
                st.error("Bitte Titel und Projekt ausfüllen")
            else:
                with get_session() as db:
                    service = KalenderService(db)
                    user_id = st.session_state.get("user_id")

                    termin = service.termin_erstellen(
                        projekt_id=projekt_id,
                        titel=titel,
                        datum=datum,
                        termin_typ=termin_typ,
                        uhrzeit_von=uhrzeit_von,
                        uhrzeit_bis=uhrzeit_bis,
                        ganztaegig=ganztaegig,
                        ort=ort,
                        beschreibung=beschreibung,
                        gericht_name=gericht_name,
                        gericht_aktenzeichen=gericht_aktenzeichen,
                        gericht_saal=gericht_saal,
                        erinnerung_minuten=erinnerung,
                        erstellt_von_user_id=user_id
                    )

                    st.success(f"Termin '{termin.titel}' erstellt!")


def _render_ical_export():
    """iCal-Export"""
    st.subheader("Kalender exportieren")

    st.info("Exportieren Sie Ihre Termine im iCal-Format für externe Kalender-Apps.")

    col1, col2 = st.columns(2)

    with col1:
        export_zeitraum = st.selectbox(
            "Zeitraum",
            ["Nächste 30 Tage", "Nächste 90 Tage", "Dieses Jahr", "Alle"]
        )

    with col2:
        nur_gericht = st.checkbox("Nur Gerichtstermine exportieren")

    if st.button("iCal generieren", type="primary"):
        with get_session() as db:
            service = KalenderService(db)

            heute = date.today()
            if export_zeitraum == "Nächste 30 Tage":
                termine = service.anstehende_termine(tage=30)
            elif export_zeitraum == "Nächste 90 Tage":
                termine = service.anstehende_termine(tage=90)
            elif export_zeitraum == "Dieses Jahr":
                termine = service.termine_fuer_zeitraum(
                    date(heute.year, 1, 1),
                    date(heute.year, 12, 31)
                )
            else:
                termine = service.termine_fuer_zeitraum(
                    heute - timedelta(days=365),
                    heute + timedelta(days=365)
                )

            if nur_gericht:
                termine = [t for t in termine if t.termin_typ == TerminTyp.GERICHTSTERMIN]

            if termine:
                ical_content = service.generiere_ical(termine)

                st.download_button(
                    "📥 iCal herunterladen",
                    data=ical_content,
                    file_name="schadenmanager_termine.ics",
                    mime="text/calendar"
                )

                st.success(f"{len(termine)} Termine exportiert")
            else:
                st.warning("Keine Termine zum Exportieren gefunden")


def _get_termin_farbe(termin_typ: TerminTyp) -> str:
    """Gibt Emoji/Farbe für Termintyp zurück"""
    return {
        TerminTyp.GERICHTSTERMIN: "⚖️",
        TerminTyp.GUTACHTERTERMIN: "📋",
        TerminTyp.MANDANTENBESPRECHUNG: "👥",
        TerminTyp.WERKSTATTTERMIN: "🔧",
        TerminTyp.VERSICHERUNGSTERMIN: "🏢",
        TerminTyp.ORTSBESICHTIGUNG: "📍",
        TerminTyp.TELEFONTERMIN: "📞",
        TerminTyp.FRIST: "⏰",
        TerminTyp.SONSTIGER: "📌"
    }.get(termin_typ, "📌")
