"""
Haftungsquoten-Rechner UI-Seite
Automatische Einschätzung basierend auf Unfalltyp
"""
import streamlit as st

from src.config.database import get_session
from src.services.haftungsquote import HaftungsquoteService, HaftungsBerechnung, UnfallTyp


def render_haftungsquote():
    """Rendert die Haftungsquoten-Rechner-Seite"""
    st.title("📊 Haftungsquoten-Rechner")

    st.info("""
    Dieser Rechner gibt eine erste Einschätzung der Haftungsquoten basierend auf dem Unfalltyp
    und bekannten Modifikatoren. Die tatsächliche Haftung hängt immer vom Einzelfall ab.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Neue Berechnung", "Berechnungen", "Rechtsprechung"
    ])

    with tab1:
        _render_neue_berechnung()

    with tab2:
        _render_berechnungen()

    with tab3:
        _render_rechtsprechung()


def _render_neue_berechnung():
    """Neue Haftungsquoten-Berechnung"""
    st.subheader("Haftungsquote berechnen")

    # Projekt auswählen
    with get_session() as db:
        from src.models import UnfallProjekt
        projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).limit(50).all()

        if not projekte:
            st.warning("Bitte erst ein Projekt anlegen")
            return

        projekt_options = {p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}" for p in projekte}
        projekt_id = st.selectbox(
            "Projekt",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, "")
        )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Unfalltyp auswählen")

        unfall_typ = st.selectbox(
            "Unfalltyp",
            [t for t in UnfallTyp],
            format_func=lambda t: _unfall_typ_anzeige(t)
        )

        ist_hauptverursacher = st.radio(
            "Rolle Ihres Mandanten",
            [False, True],
            format_func=lambda x: "Geschädigter" if not x else "Verursacher"
        )

        beschreibung = st.text_area(
            "Unfallbeschreibung",
            height=100,
            placeholder="Kurze Beschreibung des Unfallhergangs..."
        )

    with col2:
        st.markdown("### Zusätzliche Faktoren")

        with get_session() as db:
            service = HaftungsquoteService(db)
            modifikatoren = service.get_alle_modifikatoren()

            st.write("Wählen Sie zutreffende Faktoren:")

            selected_faktoren = []
            for mod in modifikatoren:
                aenderung = mod['aenderung']
                label = f"{mod['beschreibung']} ({'+' if aenderung > 0 else ''}{aenderung}%)"

                if st.checkbox(label, key=f"mod_{mod['code']}"):
                    selected_faktoren.append(mod['code'])

    # Berechnung durchführen
    if st.button("Haftungsquote berechnen", type="primary"):
        with get_session() as db:
            service = HaftungsquoteService(db)
            user_id = st.session_state.get("user_id")

            berechnung = service.berechne_haftungsquote(
                projekt_id=projekt_id,
                unfall_typ=unfall_typ,
                ist_hauptverursacher=ist_hauptverursacher,
                zusatz_faktoren=selected_faktoren if selected_faktoren else None,
                beschreibung=beschreibung,
                erstellt_von_user_id=user_id
            )

            # Ergebnis anzeigen
            st.markdown("---")
            st.markdown("## Ergebnis")

            col_r1, col_r2 = st.columns(2)

            with col_r1:
                st.metric(
                    "Haftungsquote eigenes Fahrzeug",
                    f"{berechnung.haftungsquote_eigenes_fahrzeug}%"
                )

                # Fortschrittsbalken
                st.progress(float(berechnung.haftungsquote_eigenes_fahrzeug) / 100)

            with col_r2:
                st.metric(
                    "Haftungsquote Unfallgegner",
                    f"{berechnung.haftungsquote_gegner}%"
                )

                st.progress(float(berechnung.haftungsquote_gegner) / 100)

            # Ampel-Bewertung
            if berechnung.haftungsquote_eigenes_fahrzeug <= 25:
                st.success("🟢 Sehr gute Ausgangslage für Ihren Mandanten")
            elif berechnung.haftungsquote_eigenes_fahrzeug <= 50:
                st.warning("🟡 Teilhaftung - Quotelung wahrscheinlich")
            else:
                st.error("🔴 Überwiegende Haftung des Mandanten")

            # Begründung
            st.markdown("### Begründung")
            st.text(berechnung.begruendung)

            # Relevante Urteile
            if berechnung.relevante_urteile:
                import json
                urteile = json.loads(berechnung.relevante_urteile)

                if urteile:
                    st.markdown("### Relevante Rechtsprechung")

                    for urteil in urteile:
                        st.write(f"**{urteil.get('gericht')} - {urteil.get('aktenzeichen')}** ({urteil.get('datum')})")
                        st.write(f"*{urteil.get('leitsatz')}*")
                        st.markdown("---")


def _render_berechnungen():
    """Zeigt gespeicherte Berechnungen"""
    st.subheader("Gespeicherte Berechnungen")

    # Projekt auswählen
    with get_session() as db:
        from src.models import UnfallProjekt
        projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).limit(50).all()

        if not projekte:
            st.info("Keine Projekte vorhanden")
            return

        projekt_options = {p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}" for p in projekte}
        projekt_id = st.selectbox(
            "Projekt",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, ""),
            key="berechnung_projekt"
        )

        service = HaftungsquoteService(db)
        berechnungen = service.berechnungen_fuer_projekt(projekt_id)

        if not berechnungen:
            st.info("Noch keine Berechnungen für dieses Projekt")
            return

        for berechnung in berechnungen:
            with st.expander(
                f"{berechnung.erstellt_am.strftime('%d.%m.%Y %H:%M')} - "
                f"{_unfall_typ_anzeige(UnfallTyp(berechnung.unfall_typ))} - "
                f"{berechnung.haftungsquote_eigenes_fahrzeug}%/{berechnung.haftungsquote_gegner}%"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Unfalltyp:** {_unfall_typ_anzeige(UnfallTyp(berechnung.unfall_typ))}")
                    st.write(f"**Beschreibung:** {berechnung.unfall_beschreibung or '-'}")

                with col2:
                    st.metric("Eigenes Fahrzeug", f"{berechnung.haftungsquote_eigenes_fahrzeug}%")
                    st.metric("Unfallgegner", f"{berechnung.haftungsquote_gegner}%")

                if berechnung.begruendung:
                    st.text_area(
                        "Begründung",
                        value=berechnung.begruendung,
                        height=200,
                        disabled=True,
                        key=f"begr_{berechnung.id}"
                    )


def _render_rechtsprechung():
    """Rechtsprechungsdatenbank durchsuchen"""
    st.subheader("Rechtsprechungsdatenbank")

    suchbegriff = st.text_input("Suche nach Leitsatz oder Aktenzeichen")

    if suchbegriff:
        with get_session() as db:
            service = HaftungsquoteService(db)
            ergebnisse = service.suche_rechtsprechung(suchbegriff)

            if ergebnisse:
                st.write(f"**{len(ergebnisse)} Ergebnis(se):**")

                for urteil in ergebnisse:
                    with st.expander(f"{urteil.get('gericht')} - {urteil.get('aktenzeichen')}"):
                        st.write(f"**Datum:** {urteil.get('datum')}")
                        st.write(f"**Unfalltyp:** {urteil.get('unfalltyp')}")
                        st.markdown("**Leitsatz:**")
                        st.write(urteil.get('leitsatz'))
            else:
                st.info("Keine Urteile gefunden")
    else:
        st.markdown("### Typische Unfallkonstellationen")

        for typ in [
            UnfallTyp.AUFFAHRUNFALL,
            UnfallTyp.SPURWECHSEL,
            UnfallTyp.VORFAHRT,
            UnfallTyp.PARKPLATZ,
            UnfallTyp.RUECKWAERTS
        ]:
            with st.expander(_unfall_typ_anzeige(typ)):
                with get_session() as db:
                    service = HaftungsquoteService(db)
                    basis = service.BASIS_HAFTUNG.get(typ, {})

                    st.write(basis.get('beschreibung', 'Keine Beschreibung verfügbar'))

                    rechtsprechung = service.RECHTSPRECHUNG.get(typ, [])
                    if rechtsprechung:
                        st.markdown("**Relevante Urteile:**")
                        for urteil in rechtsprechung:
                            st.write(f"- {urteil.get('gericht')} {urteil.get('aktenzeichen')} ({urteil.get('datum')})")


def _unfall_typ_anzeige(typ: UnfallTyp) -> str:
    """Anzeigetext für Unfalltyp"""
    return {
        UnfallTyp.AUFFAHRUNFALL: "🚗💥🚗 Auffahrunfall",
        UnfallTyp.SPURWECHSEL: "↔️ Spurwechselunfall",
        UnfallTyp.VORFAHRT: "⚠️ Vorfahrtsverletzung",
        UnfallTyp.ABBIEGEN: "↩️ Abbiegeunfall",
        UnfallTyp.RUECKWAERTS: "⬅️ Rückwärtsfahren",
        UnfallTyp.PARKPLATZ: "🅿️ Parkplatzunfall",
        UnfallTyp.KREUZUNG: "✚ Kreuzungsunfall",
        UnfallTyp.UEBERHOLEN: "➡️ Überholunfall",
        UnfallTyp.TUER_OEFFNEN: "🚪 Türöffnungsunfall",
        UnfallTyp.FUSSGAENGER: "🚶 Fußgängerunfall",
        UnfallTyp.WILDUNFALL: "🦌 Wildunfall",
        UnfallTyp.ALKOHOL: "🍺 Alkoholunfall",
        UnfallTyp.GESCHWINDIGKEIT: "💨 Geschwindigkeitsunfall",
        UnfallTyp.ROTLICHT: "🚦 Rotlichtverstoß",
        UnfallTyp.KETTENREAKTION: "🔗 Kettenreaktion",
        UnfallTyp.SONSTIGES: "❓ Sonstiger Unfall"
    }.get(typ, str(typ))
