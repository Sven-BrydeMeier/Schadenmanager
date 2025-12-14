"""
Fristenwarnsystem UI-Seite
Überwachung von Verjährungs- und Klagefristen
"""
import streamlit as st
from datetime import datetime, date, timedelta

from src.config.database import get_session
from src.services.fristen import FristenService, FristTyp, FristPrioritaet, FristStatus, Frist


def render_fristen():
    """Rendert die Fristen-Seite"""
    st.title("⏰ Fristenwarnsystem")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Dashboard", "Alle Fristen", "Neue Frist", "Überfällig"
    ])

    with tab1:
        _render_fristen_dashboard()

    with tab2:
        _render_alle_fristen()

    with tab3:
        _render_neue_frist()

    with tab4:
        _render_ueberfaellige_fristen()


def _render_fristen_dashboard():
    """Dashboard mit Fristenübersicht"""
    with get_session() as db:
        service = FristenService(db)
        uebersicht = service.fristen_uebersicht()

        # Metriken
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Offene Fristen", uebersicht['offen'])
        with col2:
            st.metric(
                "Überfällig",
                uebersicht['ueberfaellig'],
                delta=None if uebersicht['ueberfaellig'] == 0 else f"-{uebersicht['ueberfaellig']}",
                delta_color="inverse"
            )
        with col3:
            st.metric("Kritisch (7 Tage)", uebersicht['kritisch_7_tage'])
        with col4:
            st.metric("Warnung (30 Tage)", uebersicht['warnung_30_tage'])

        st.markdown("---")

        # Kritische Fristen
        st.subheader("🔴 Kritische Fristen (nächste 7 Tage)")

        kritische = service.kritische_fristen(tage=7)

        if kritische:
            for frist in kritische:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.write(f"**{frist.bezeichnung}**")
                        st.caption(f"Projekt: {frist.projekt_id}")

                    with col2:
                        st.write(f"📅 {frist.frist_datum.strftime('%d.%m.%Y')}")
                        st.caption(f"{frist.tage_bis_frist} Tage")

                    with col3:
                        if st.button("✅ Erledigt", key=f"erl_{frist.id}"):
                            service.frist_erledigen(frist.id, 1, "Über Dashboard erledigt")
                            st.rerun()

                    st.markdown("---")
        else:
            st.success("Keine kritischen Fristen in den nächsten 7 Tagen")

        # Warnungen
        st.subheader("🟡 Warnungen (nächste 30 Tage)")

        warnungen = service.kritische_fristen(tage=30)
        warnungen = [f for f in warnungen if f.tage_bis_frist > 7]

        if warnungen:
            for frist in warnungen[:5]:  # Nur erste 5
                st.write(f"- **{frist.bezeichnung}** - {frist.frist_datum.strftime('%d.%m.%Y')} ({frist.tage_bis_frist} Tage)")
        else:
            st.info("Keine Warnungen")


def _render_alle_fristen():
    """Alle Fristen anzeigen"""
    st.subheader("Alle Fristen")

    with get_session() as db:
        from src.models import UnfallProjekt

        # Filter
        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox(
                "Status",
                ["Alle", "Offen", "Erledigt", "Überfällig"]
            )

        with col2:
            typ_filter = st.selectbox(
                "Typ",
                ["Alle"] + [t.value for t in FristTyp]
            )

        with col3:
            projekt_filter = st.selectbox(
                "Projekt",
                ["Alle"],
                # Hier könnten Projekte geladen werden
            )

        # Fristen laden
        query = db.query(Frist)

        if status_filter == "Offen":
            query = query.filter(Frist.erledigt == False)
        elif status_filter == "Erledigt":
            query = query.filter(Frist.erledigt == True)
        elif status_filter == "Überfällig":
            query = query.filter(
                Frist.frist_datum < date.today(),
                Frist.erledigt == False
            )

        if typ_filter != "Alle":
            query = query.filter(Frist.frist_typ == typ_filter)

        fristen = query.order_by(Frist.frist_datum).all()

        if not fristen:
            st.info("Keine Fristen gefunden")
            return

        # Tabelle
        for frist in fristen:
            with st.expander(
                f"{frist.status_anzeige} {frist.bezeichnung} - {frist.frist_datum.strftime('%d.%m.%Y')}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Typ:** {frist.typ_anzeige}")
                    st.write(f"**Priorität:** {frist.prioritaet.value if frist.prioritaet else '-'}")
                    st.write(f"**Projekt:** {frist.projekt_id}")

                with col2:
                    st.write(f"**Frist:** {frist.frist_datum.strftime('%d.%m.%Y')}")
                    st.write(f"**Tage bis Frist:** {frist.tage_bis_frist}")
                    if frist.erledigt:
                        st.write(f"**Erledigt am:** {frist.erledigt_am.strftime('%d.%m.%Y') if frist.erledigt_am else '-'}")

                if frist.beschreibung:
                    st.write(f"**Beschreibung:** {frist.beschreibung}")

                # Aktionen
                col_a1, col_a2 = st.columns(2)

                with col_a1:
                    if not frist.erledigt:
                        if st.button("✅ Als erledigt markieren", key=f"done_{frist.id}"):
                            service = FristenService(db)
                            service.frist_erledigen(frist.id, 1)
                            st.success("Frist als erledigt markiert")
                            st.rerun()

                with col_a2:
                    if not frist.erledigt:
                        neues_datum = st.date_input(
                            "Verlängern bis",
                            value=frist.frist_datum + timedelta(days=14),
                            key=f"verl_{frist.id}"
                        )
                        if st.button("📅 Verlängern", key=f"ext_{frist.id}"):
                            service = FristenService(db)
                            service.frist_verlaengern(frist.id, neues_datum)
                            st.success("Frist verlängert")
                            st.rerun()


def _render_neue_frist():
    """Neue Frist erstellen"""
    st.subheader("Neue Frist erstellen")

    with get_session() as db:
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        col1, col2 = st.columns(2)

        with col1:
            projekt_options = {
                p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
                for p in projekte
            }
            projekt_id = st.selectbox(
                "Projekt",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, "")
            )

            bezeichnung = st.text_input("Bezeichnung", placeholder="z.B. Verjährungsfrist")

            frist_typ = st.selectbox(
                "Fristtyp",
                [t.value for t in FristTyp],
                format_func=lambda x: {
                    'VERJAEHRUNG': '⏰ Verjährung',
                    'KLAGEFRIST': '⚖️ Klagefrist',
                    'BERUFUNGSFRIST': '📜 Berufungsfrist',
                    'WIDERSPRUCHSFRIST': '✋ Widerspruchsfrist',
                    'STELLUNGNAHME': '📝 Stellungnahme',
                    'ZAHLUNG': '💶 Zahlungsfrist',
                    'GUTACHTEN': '📋 Gutachtenfrist',
                    'REGULIERUNG': '🏢 Regulierungsfrist',
                    'RECHTSMITTEL': '⚖️ Rechtsmittelfrist',
                    'SONSTIGE': '📌 Sonstige'
                }.get(x, x)
            )

        with col2:
            frist_datum = st.date_input(
                "Fristdatum",
                value=date.today() + timedelta(days=30)
            )

            prioritaet = st.selectbox(
                "Priorität",
                [p.value for p in FristPrioritaet],
                index=1
            )

            warnung_tage = st.number_input(
                "Warnung Tage vorher",
                min_value=1,
                max_value=365,
                value=30
            )

        beschreibung = st.text_area("Beschreibung (optional)")

        if st.button("💾 Frist erstellen", type="primary"):
            if not bezeichnung:
                st.error("Bitte Bezeichnung eingeben")
                return

            service = FristenService(db)
            frist = service.frist_erstellen(
                projekt_id=projekt_id,
                bezeichnung=bezeichnung,
                frist_datum=frist_datum,
                frist_typ=FristTyp(frist_typ),
                prioritaet=FristPrioritaet(prioritaet),
                beschreibung=beschreibung if beschreibung else None,
                warnung_tage_vorher=warnung_tage
            )

            db.commit()
            st.success(f"Frist erstellt! Fällig am {frist_datum.strftime('%d.%m.%Y')}")


def _render_ueberfaellige_fristen():
    """Überfällige Fristen"""
    st.subheader("⛔ Überfällige Fristen")

    with get_session() as db:
        service = FristenService(db)
        ueberfaellige = service.ueberfaellige_fristen()

        if not ueberfaellige:
            st.success("Keine überfälligen Fristen!")
            return

        st.error(f"{len(ueberfaellige)} überfällige Frist(en)!")

        for frist in ueberfaellige:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"**{frist.bezeichnung}**")
                    st.caption(f"Fällig: {frist.frist_datum.strftime('%d.%m.%Y')}")

                with col2:
                    st.write(f"**{abs(frist.tage_bis_frist)} Tage überfällig**")

                with col3:
                    if st.button("✅ Erledigen", key=f"ueberf_{frist.id}"):
                        service.frist_erledigen(frist.id, 1, "Nachträglich erledigt")
                        st.rerun()

                st.markdown("---")
