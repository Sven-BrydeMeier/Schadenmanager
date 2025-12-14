"""
Gutachten-Plausibilitätsprüfung UI-Seite
Automatische Prüfung von Kfz-Gutachten auf Unstimmigkeiten
"""
import streamlit as st
from datetime import datetime, date

from src.config.database import get_session
from src.services.gutachten_plausibilitaet import (
    GutachtenPlausibilitaetService, GutachtenPruefung,
    PruefungsSchwere, PruefungsKategorie
)


def render_gutachten_plausibilitaet():
    """Rendert die Gutachten-Plausibilitätsprüfung"""
    st.title("Gutachten-Plausibilitätsprüfung")

    st.info("""
    Dieses Tool prüft Kfz-Gutachten automatisch auf Unstimmigkeiten, Rechenfehler
    und Abweichungen von Referenzwerten. Es unterstützt Anwälte bei der Prüfung
    von gegnerischen Gutachten und identifiziert potenzielle Angriffspunkte.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Neue Prüfung", "Bisherige Prüfungen", "Referenzwerte"
    ])

    with tab1:
        _render_neue_pruefung()

    with tab2:
        _render_bisherige_pruefungen()

    with tab3:
        _render_referenzwerte()


def _render_neue_pruefung():
    """Neue Gutachten-Prüfung durchführen"""
    st.subheader("Gutachten-Daten eingeben")

    with get_session() as db:
        service = GutachtenPlausibilitaetService(db)

        # Projekt auswählen
        from src.models import UnfallProjekt
        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden. Bitte zuerst ein Projekt anlegen.")
            return

        projekt_options = {
            p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
            for p in projekte
        }
        projekt_id = st.selectbox(
            "Projekt auswählen",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, "")
        )

        st.markdown("---")

        # Gutachten-Grunddaten
        st.markdown("### Gutachten-Informationen")
        col1, col2 = st.columns(2)

        with col1:
            gutachten_nr = st.text_input("Gutachten-Nr.")
            gutachter_name = st.text_input("Gutachter")
            gutachten_datum = st.date_input("Gutachten-Datum", value=date.today())

        with col2:
            kennzeichen = st.text_input("Kennzeichen")
            fahrgestellnummer = st.text_input("Fahrgestellnummer (VIN)")
            erstzulassung = st.date_input("Erstzulassung", value=None)

        st.markdown("---")

        # Fahrzeugdaten
        st.markdown("### Fahrzeugdaten")
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            hersteller = st.text_input("Hersteller")
            modell = st.text_input("Modell")

        with col_f2:
            kilometerstand = st.number_input("Kilometerstand", min_value=0, step=1000)
            neupreis = st.number_input("Neupreis (EUR)", min_value=0.0, step=1000.0)

        with col_f3:
            werkstatt_typ = st.selectbox(
                "Werkstatt-Typ",
                ["markenwerkstatt", "freie_werkstatt"],
                format_func=lambda x: "Markenwerkstatt" if x == "markenwerkstatt" else "Freie Werkstatt"
            )

        st.markdown("---")

        # Wertermittlung
        st.markdown("### Wertermittlung")
        col_w1, col_w2, col_w3 = st.columns(3)

        with col_w1:
            wiederbeschaffungswert = st.number_input(
                "Wiederbeschaffungswert (EUR)", min_value=0.0, step=100.0
            )

        with col_w2:
            restwert = st.number_input("Restwert (EUR)", min_value=0.0, step=100.0)
            restwert_methode = st.selectbox(
                "Restwert-Ermittlung",
                ["", "restwertboerse", "regional", "schaetzung"],
                format_func=lambda x: {
                    "": "- Bitte wählen -",
                    "restwertboerse": "Restwertbörse",
                    "regional": "Regionale Angebote",
                    "schaetzung": "Schätzung"
                }.get(x, x)
            )

        with col_w3:
            totalschaden = st.checkbox("Als Totalschaden bewertet")
            merkantiler_minderwert = st.number_input(
                "Merkantiler Minderwert (EUR)", min_value=0.0, step=100.0
            )

        st.markdown("---")

        # Reparaturkosten
        st.markdown("### Reparaturkosten")
        col_r1, col_r2 = st.columns(2)

        with col_r1:
            reparaturkosten_netto = st.number_input(
                "Reparaturkosten netto (EUR)", min_value=0.0, step=100.0
            )
            lohnkosten = st.number_input("Lohnkosten (EUR)", min_value=0.0, step=50.0)
            ersatzteilkosten = st.number_input(
                "Ersatzteilkosten (EUR)", min_value=0.0, step=50.0
            )

        with col_r2:
            lackierkosten = st.number_input("Lackierkosten (EUR)", min_value=0.0, step=50.0)
            sonstige_kosten = st.number_input(
                "Sonstige Kosten (EUR)", min_value=0.0, step=50.0
            )
            reparaturdauer_tage = st.number_input(
                "Reparaturdauer (Tage)", min_value=0, step=1
            )

        st.markdown("---")

        # Stundenverrechnungssätze
        st.markdown("### Stundenverrechnungssätze")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)

        with col_s1:
            stundensatz_karosserie = st.number_input(
                "Karosserie (EUR/h)", min_value=0.0, step=5.0, key="svs_karosserie"
            )
        with col_s2:
            stundensatz_mechanik = st.number_input(
                "Mechanik (EUR/h)", min_value=0.0, step=5.0, key="svs_mechanik"
            )
        with col_s3:
            stundensatz_elektrik = st.number_input(
                "Elektrik (EUR/h)", min_value=0.0, step=5.0, key="svs_elektrik"
            )
        with col_s4:
            stundensatz_lackierung = st.number_input(
                "Lackierung (EUR/h)", min_value=0.0, step=5.0, key="svs_lackierung"
            )

        st.markdown("---")

        # Ersatzteile & Lackierung Details
        with st.expander("Weitere Details (optional)"):
            col_d1, col_d2 = st.columns(2)

            with col_d1:
                st.markdown("**Ersatzteile**")
                upe_aufschlag = st.number_input("UPE-Aufschlag (%)", min_value=0.0, max_value=50.0, step=1.0)
                kleinteile_pauschale = st.number_input("Kleinteile-Pauschale (EUR)", min_value=0.0, step=10.0)

            with col_d2:
                st.markdown("**Lackierung**")
                lackierpunkte = st.number_input("Lackierpunkte (LP)", min_value=0, step=1)
                lackmaterial = st.number_input("Lackmaterial (EUR)", min_value=0.0, step=10.0)
                lackierzeit_stunden = st.number_input("Lackierzeit (Stunden)", min_value=0.0, step=0.5)

            st.markdown("**Nutzungsausfall**")
            col_n1, col_n2 = st.columns(2)

            with col_n1:
                nutzungsausfall_gruppe = st.selectbox(
                    "Nutzungsausfall-Gruppe",
                    ["", "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L"]
                )
            with col_n2:
                nutzungsausfall_pro_tag = st.number_input(
                    "Nutzungsausfall (EUR/Tag)", min_value=0.0, step=5.0
                )

        st.markdown("---")

        # Prüfung starten
        if st.button("Prüfung durchführen", type="primary", use_container_width=True):
            # Daten zusammenstellen
            gutachten_daten = {
                'gutachten_nr': gutachten_nr,
                'gutachter_name': gutachter_name,
                'gutachten_datum': gutachten_datum.isoformat() if gutachten_datum else None,
                'kennzeichen': kennzeichen,
                'fahrgestellnummer': fahrgestellnummer,
                'erstzulassung': erstzulassung.isoformat() if erstzulassung else None,
                'hersteller': hersteller,
                'modell': modell,
                'kilometerstand': kilometerstand,
                'neupreis': neupreis,
                'werkstatt_typ': werkstatt_typ,
                'wiederbeschaffungswert': wiederbeschaffungswert,
                'restwert': restwert,
                'restwert_methode': restwert_methode,
                'totalschaden': totalschaden,
                'merkantiler_minderwert': merkantiler_minderwert,
                'reparaturkosten_netto': reparaturkosten_netto,
                'lohnkosten': lohnkosten,
                'ersatzteilkosten': ersatzteilkosten,
                'lackierkosten': lackierkosten,
                'sonstige_kosten': sonstige_kosten,
                'reparaturdauer_tage': reparaturdauer_tage,
                'stundensaetze': {
                    'karosserie': stundensatz_karosserie,
                    'mechanik': stundensatz_mechanik,
                    'elektrik': stundensatz_elektrik,
                    'lackierung': stundensatz_lackierung
                },
                'upe_aufschlag': upe_aufschlag if 'upe_aufschlag' in dir() else 0,
                'kleinteile_pauschale': kleinteile_pauschale if 'kleinteile_pauschale' in dir() else 0,
                'lackierpunkte': lackierpunkte if 'lackierpunkte' in dir() else 0,
                'lackmaterial': lackmaterial if 'lackmaterial' in dir() else 0,
                'lackierzeit_stunden': lackierzeit_stunden if 'lackierzeit_stunden' in dir() else 0,
                'nutzungsausfall_gruppe': nutzungsausfall_gruppe if 'nutzungsausfall_gruppe' in dir() else '',
                'nutzungsausfall_pro_tag': nutzungsausfall_pro_tag if 'nutzungsausfall_pro_tag' in dir() else 0
            }

            with st.spinner("Prüfung wird durchgeführt..."):
                pruefung = service.pruefung_durchfuehren(
                    projekt_id=projekt_id,
                    gutachten_daten=gutachten_daten,
                    geprueft_von_user_id=st.session_state.get('user_id', 1)
                )
                db.commit()

            st.success("Prüfung abgeschlossen!")

            # Ergebnis anzeigen
            _zeige_pruefungsergebnis(pruefung)


def _render_bisherige_pruefungen():
    """Bisherige Prüfungen anzeigen"""
    st.subheader("Bisherige Prüfungen")

    with get_session() as db:
        service = GutachtenPlausibilitaetService(db)

        # Projekt-Filter
        from src.models import UnfallProjekt
        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if projekte:
            projekt_options = {0: "Alle Projekte"}
            projekt_options.update({
                p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
                for p in projekte
            })

            filter_projekt = st.selectbox(
                "Projekt filtern",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, ""),
                key="filter_projekt"
            )

            # Prüfungen laden
            if filter_projekt:
                pruefungen = service.pruefungen_fuer_projekt(filter_projekt)
            else:
                pruefungen = db.query(GutachtenPruefung).order_by(
                    GutachtenPruefung.pruefung_am.desc()
                ).limit(20).all()

            if not pruefungen:
                st.info("Keine Prüfungen für dieses Projekt vorhanden.")
                return

            for pruefung in pruefungen:
                bewertung_icon = {
                    "UNAUFFAELLIG": "✅",
                    "LEICHT_AUFFAELLIG": "ℹ️",
                    "PRUEFENSWERT": "⚡",
                    "AUFFAELLIG": "⚠️"
                }.get(pruefung.gesamtbewertung, "")

                with st.expander(
                    f"{bewertung_icon} {pruefung.gutachten_nr or 'Ohne Nr.'} - "
                    f"{pruefung.pruefung_am.strftime('%d.%m.%Y %H:%M') if pruefung.pruefung_am else '-'}"
                ):
                    _zeige_pruefungsergebnis(pruefung, show_kommentar=True)

                    # Bericht generieren
                    col_btn1, col_btn2 = st.columns(2)

                    with col_btn1:
                        bericht = service.generiere_pruefbericht(pruefung.id)
                        st.download_button(
                            "Bericht herunterladen",
                            data=bericht,
                            file_name=f"Pruefbericht_{pruefung.gutachten_nr or pruefung.id}.txt",
                            mime="text/plain",
                            key=f"dl_{pruefung.id}"
                        )

                    with col_btn2:
                        # Kommentar hinzufügen
                        kommentar = st.text_area(
                            "Anwaltskommentar",
                            value=pruefung.anwalt_kommentar or "",
                            key=f"kommentar_{pruefung.id}"
                        )

                        if st.button("Kommentar speichern", key=f"save_kom_{pruefung.id}"):
                            service.anwalt_kommentar_speichern(pruefung.id, kommentar)
                            db.commit()
                            st.success("Kommentar gespeichert!")
                            st.rerun()


def _zeige_pruefungsergebnis(pruefung: GutachtenPruefung, show_kommentar: bool = False):
    """Zeigt das Ergebnis einer Prüfung an"""
    # Zusammenfassung
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    with col_s1:
        st.metric("Gesamtbewertung", pruefung.gesamtbewertung or "-")
    with col_s2:
        st.metric("Fehler", pruefung.anzahl_fehler, delta_color="inverse")
    with col_s3:
        st.metric("Warnungen", pruefung.anzahl_warnungen, delta_color="inverse")
    with col_s4:
        st.metric("Hinweise", pruefung.anzahl_hinweise, delta_color="off")

    st.markdown("---")

    # Ergebnisse nach Kategorie gruppiert
    ergebnisse = pruefung.pruefungsergebnisse

    if not ergebnisse:
        st.success("Keine Auffälligkeiten gefunden.")
        return

    # Gruppieren nach Schwere
    fehler = [e for e in ergebnisse if e['schwere'] == PruefungsSchwere.FEHLER.value]
    kritisch = [e for e in ergebnisse if e['schwere'] == PruefungsSchwere.KRITISCH.value]
    warnungen = [e for e in ergebnisse if e['schwere'] == PruefungsSchwere.WARNUNG.value]
    hinweise = [e for e in ergebnisse if e['schwere'] == PruefungsSchwere.INFO.value]

    if fehler:
        st.markdown("### Fehler")
        for e in fehler:
            st.error(f"**{e['titel']}**  \n{e['beschreibung']}")

    if kritisch:
        st.markdown("### Kritische Punkte")
        for e in kritisch:
            st.warning(f"**{e['titel']}**  \n{e['beschreibung']}")

    if warnungen:
        st.markdown("### Warnungen")
        for e in warnungen:
            st.warning(f"**{e['titel']}**  \n{e['beschreibung']}")

    if hinweise:
        with st.expander("Hinweise anzeigen"):
            for e in hinweise:
                st.info(f"**{e['titel']}**  \n{e['beschreibung']}")

    if show_kommentar and pruefung.anwalt_kommentar:
        st.markdown("---")
        st.markdown("### Anwaltskommentar")
        st.write(pruefung.anwalt_kommentar)


def _render_referenzwerte():
    """Zeigt die verwendeten Referenzwerte"""
    st.subheader("Referenzwerte")

    st.markdown("""
    Die Plausibilitätsprüfung verwendet aktuelle Referenzwerte aus der Praxis.
    Abweichungen von diesen Werten werden als potenzielle Auffälligkeiten markiert.
    """)

    # Stundenverrechnungssätze
    st.markdown("### Stundenverrechnungssätze (EUR/Stunde)")

    st.markdown("""
    | Bereich | Minimum | Maximum | Durchschnitt |
    |---------|---------|---------|--------------|
    | Karosserie | 95 | 180 | 135 |
    | Mechanik | 90 | 170 | 125 |
    | Elektrik | 95 | 175 | 130 |
    | Lackierung | 100 | 190 | 145 |
    | Freie Werkstatt | 60 | 120 | 85 |
    """)

    st.markdown("---")

    # Lackierung
    st.markdown("### Lackierung (pro Lackierpunkt)")

    st.markdown("""
    | Parameter | Minimum | Maximum | Durchschnitt |
    |-----------|---------|---------|--------------|
    | Lackmaterial | 1,50 EUR | 4,50 EUR | 2,80 EUR |
    | Arbeitszeit | 4 Min. | 8 Min. | 5,5 Min. |
    """)

    st.markdown("---")

    # Merkantiler Minderwert
    st.markdown("### Merkantiler Minderwert")

    st.markdown("""
    | Parameter | Grenzwert |
    |-----------|-----------|
    | Max. Fahrzeugalter | 60 Monate (5 Jahre) |
    | Max. Laufleistung | 100.000 km |
    | Max. % der Reparaturkosten | 30% |
    | Max. % des WBW | 10% |
    """)

    st.markdown("---")

    # Nutzungsausfall
    st.markdown("### Nutzungsausfall (nach Sanden/Danner/Küppersbusch)")

    st.markdown("""
    | Gruppe | Minimum (EUR/Tag) | Maximum (EUR/Tag) |
    |--------|-------------------|-------------------|
    | A | 23 | 29 |
    | B | 29 | 35 |
    | C | 35 | 41 |
    | D | 41 | 50 |
    | E | 50 | 59 |
    | F | 59 | 65 |
    | G | 65 | 79 |
    | H | 79 | 89 |
    | J | 89 | 103 |
    | K | 103 | 119 |
    | L | 119 | 175 |
    """)

    st.markdown("---")

    # Totalschaden
    st.markdown("### Totalschaden-Grenze")

    st.info("""
    **130%-Regel (BGH-Rechtsprechung)**

    Bei Reparaturkosten über 130% des Wiederbeschaffungswertes liegt ein
    wirtschaftlicher Totalschaden vor. Zwischen 100% und 130% kann der
    Geschädigte auf Reparatur bestehen (Integritätsinteresse).
    """)
