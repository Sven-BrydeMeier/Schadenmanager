"""
Fahrzeugbewertung UI-Seite
DAT/Schwacke Integration
"""
import streamlit as st
from datetime import datetime, date
from decimal import Decimal

from src.config.database import get_session
from src.services.fahrzeugbewertung import (
    FahrzeugbewertungService, BewertungsAnbieter, BewertungsTyp,
    ZustandsNote, Fahrzeugbewertung
)


def render_fahrzeugbewertung():
    """Rendert die Fahrzeugbewertung-Seite"""
    st.title("🚗 Fahrzeugbewertung")

    st.info("""
    Professionelle Fahrzeugbewertung mit DAT/Schwacke-Schnittstelle.
    Ermitteln Sie Wiederbeschaffungswert, Restwert und mehr.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Neue Bewertung", "Bewertungen", "Totalschaden-Prüfung"
    ])

    with tab1:
        _render_neue_bewertung()

    with tab2:
        _render_bewertungen()

    with tab3:
        _render_totalschaden()


def _render_neue_bewertung():
    """Neue Fahrzeugbewertung"""
    st.subheader("Neue Bewertung erstellen")

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

            st.markdown("### Fahrzeugdaten")

            hersteller = st.text_input("Hersteller", placeholder="z.B. Volkswagen")
            modell = st.text_input("Modell", placeholder="z.B. Golf")
            variante = st.text_input("Variante", placeholder="z.B. 1.4 TSI Comfortline")

        with col2:
            erstzulassung = st.date_input(
                "Erstzulassung",
                value=date(2020, 1, 1)
            )

            kilometerstand = st.number_input(
                "Kilometerstand",
                min_value=0,
                value=50000,
                step=1000
            )

            hsn = st.text_input("HSN", placeholder="0603")
            tsn = st.text_input("TSN", placeholder="BYT")

        st.markdown("### Bewertungsdetails")

        col3, col4 = st.columns(2)

        with col3:
            anbieter = st.selectbox(
                "Bewertungsanbieter",
                [a.value for a in BewertungsAnbieter],
                format_func=lambda x: {
                    'DAT': '📊 DAT',
                    'SCHWACKE': '📈 Schwacke',
                    'EUROTAX': '📉 Eurotax',
                    'MANUELL': '✏️ Manuelle Eingabe'
                }.get(x, x)
            )

            bewertungs_typ = st.selectbox(
                "Bewertungstyp",
                [t.value for t in BewertungsTyp],
                format_func=lambda x: {
                    'WIEDERBESCHAFFUNGSWERT': '🔄 Wiederbeschaffungswert',
                    'RESTWERT': '💰 Restwert',
                    'HAENDLER_EK': '🏪 Händler-EK',
                    'HAENDLER_VK': '🏬 Händler-VK',
                    'ZEITWERT': '⏱️ Zeitwert',
                    'NEUPREIS': '🆕 Neupreis'
                }.get(x, x)
            )

        with col4:
            zustandsnote = st.selectbox(
                "Zustandsnote",
                [z.value for z in ZustandsNote],
                index=1,
                format_func=lambda x: {
                    '1': '⭐ 1 - Wie neu',
                    '2': '⭐ 2 - Gut',
                    '3': '⭐ 3 - Befriedigend',
                    '4': '⭐ 4 - Ausreichend',
                    '5': '⭐ 5 - Mangelhaft'
                }.get(x, x)
            )

        # Ausstattung
        st.markdown("### Ausstattung")

        service = FahrzeugbewertungService(db)
        ausstattung = st.multiselect(
            "Sonderausstattung",
            service.STANDARD_AUSSTATTUNGEN
        )

        # Manuelle Werteingabe
        if anbieter == "MANUELL":
            st.markdown("### Manuelle Werteingabe")

            wert_brutto = st.number_input(
                "Wert brutto (EUR)",
                min_value=0.0,
                step=100.0
            )
        else:
            wert_brutto = None

        # Bewertung durchführen
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("📊 Bewertung abrufen", type="primary"):
                if not hersteller or not modell:
                    st.error("Bitte Hersteller und Modell eingeben")
                    return

                with st.spinner("Rufe Bewertung ab..."):
                    if anbieter == "DAT":
                        ergebnis = service.dat_abfrage_simulieren(
                            hsn=hsn or "0000",
                            tsn=tsn or "AAA",
                            erstzulassung=erstzulassung,
                            kilometerstand=kilometerstand
                        )
                    else:
                        ergebnis = service.schwacke_abfrage_simulieren(
                            hersteller=hersteller,
                            modell=modell,
                            erstzulassung=erstzulassung,
                            kilometerstand=kilometerstand,
                            ausstattung=ausstattung
                        )

                st.success("Bewertung abgerufen!")

                # Ergebnis anzeigen
                st.markdown("### Bewertungsergebnis")

                col_r1, col_r2, col_r3 = st.columns(3)

                with col_r1:
                    st.metric(
                        "Wiederbeschaffungswert",
                        f"{ergebnis.get('wiederbeschaffungswert_brutto', ergebnis.get('haendler_vk', 0)):,.2f} EUR"
                    )

                with col_r2:
                    st.metric(
                        "Restwert",
                        f"{ergebnis.get('restwert', ergebnis.get('haendler_ek', 0) * 0.15):,.2f} EUR"
                    )

                with col_r3:
                    st.metric(
                        "Neupreis",
                        f"{ergebnis.get('neupreis', 0):,.2f} EUR"
                    )

                # Speichern
                if st.button("💾 Bewertung speichern"):
                    bewertung = service.bewertung_erstellen(
                        projekt_id=projekt_id,
                        hersteller=hersteller,
                        modell=modell,
                        erstzulassung=erstzulassung,
                        kilometerstand=kilometerstand,
                        anbieter=BewertungsAnbieter(anbieter),
                        bewertungs_typ=BewertungsTyp(bewertungs_typ),
                        variante=variante,
                        hsn=hsn,
                        tsn=tsn
                    )

                    # Wert setzen
                    wbw = ergebnis.get('wiederbeschaffungswert_brutto', ergebnis.get('haendler_vk', 0))
                    service.wert_berechnen(bewertung.id, Decimal(str(wbw)))

                    bewertung.ausstattung = ausstattung
                    bewertung.zustandsnote = ZustandsNote(zustandsnote)

                    db.commit()
                    st.success("Bewertung gespeichert!")


def _render_bewertungen():
    """Alle Bewertungen"""
    st.subheader("Durchgeführte Bewertungen")

    with get_session() as db:
        bewertungen = db.query(Fahrzeugbewertung).order_by(
            Fahrzeugbewertung.bewertungsdatum.desc()
        ).limit(50).all()

        if not bewertungen:
            st.info("Noch keine Bewertungen vorhanden")
            return

        for bewertung in bewertungen:
            with st.expander(
                f"🚗 {bewertung.fahrzeug_bezeichnung} - "
                f"{float(bewertung.wert_korrigiert):,.2f} EUR"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Projekt:** {bewertung.projekt_id}")
                    st.write(f"**Anbieter:** {bewertung.anbieter.value if bewertung.anbieter else '-'}")
                    st.write(f"**Bewertungstyp:** {bewertung.bewertungs_typ.value if bewertung.bewertungs_typ else '-'}")
                    st.write(f"**Erstzulassung:** {bewertung.erstzulassung.strftime('%d.%m.%Y') if bewertung.erstzulassung else '-'}")

                with col2:
                    st.write(f"**Kilometerstand:** {bewertung.kilometerstand:,} km")
                    st.write(f"**Zustandsnote:** {bewertung.zustandsnote.value if bewertung.zustandsnote else '-'}")
                    st.write(f"**Wert brutto:** {float(bewertung.wert_brutto or 0):,.2f} EUR")
                    st.write(f"**Wert netto:** {float(bewertung.wert_netto or 0):,.2f} EUR")

                # Korrekturen
                if any([bewertung.korrektur_km, bewertung.korrektur_ausstattung,
                       bewertung.korrektur_zustand, bewertung.korrektur_sonstige]):
                    st.markdown("**Korrekturen:**")
                    if bewertung.korrektur_km:
                        st.write(f"- Kilometer: {float(bewertung.korrektur_km):+,.2f} EUR")
                    if bewertung.korrektur_ausstattung:
                        st.write(f"- Ausstattung: {float(bewertung.korrektur_ausstattung):+,.2f} EUR")
                    if bewertung.korrektur_zustand:
                        st.write(f"- Zustand: {float(bewertung.korrektur_zustand):+,.2f} EUR")

                st.metric("Korrigierter Wert", f"{float(bewertung.wert_korrigiert):,.2f} EUR")

                # Report generieren
                service = FahrzeugbewertungService(db)
                if st.button("📄 Report generieren", key=f"rep_{bewertung.id}"):
                    report = service.generiere_bewertungs_report(bewertung.id)
                    st.text_area("Report", value=report, height=300)


def _render_totalschaden():
    """Totalschaden-Prüfung"""
    st.subheader("Totalschaden-Prüfung")

    st.info("""
    Prüfen Sie, ob ein wirtschaftlicher Totalschaden vorliegt.
    Ein Totalschaden liegt vor, wenn die Reparaturkosten den Wiederbeschaffungswert
    übersteigen (bei 130%-Grenze).
    """)

    col1, col2 = st.columns(2)

    with col1:
        wiederbeschaffungswert = st.number_input(
            "Wiederbeschaffungswert (EUR)",
            min_value=0.0,
            value=15000.0,
            step=100.0
        )

        restwert = st.number_input(
            "Restwert (EUR)",
            min_value=0.0,
            value=3000.0,
            step=100.0
        )

    with col2:
        reparaturkosten = st.number_input(
            "Reparaturkosten (EUR)",
            min_value=0.0,
            value=12000.0,
            step=100.0
        )

        grenzwert = st.slider(
            "Grenzwert (%)",
            min_value=100,
            max_value=150,
            value=130
        )

    if st.button("🔍 Prüfen", type="primary"):
        with get_session() as db:
            service = FahrzeugbewertungService(db)

            ergebnis = service.totalschaden_pruefen(
                wiederbeschaffungswert=Decimal(str(wiederbeschaffungswert)),
                restwert=Decimal(str(restwert)),
                reparaturkosten=Decimal(str(reparaturkosten)),
                grenzwert_prozent=Decimal(str(grenzwert))
            )

        st.markdown("---")
        st.markdown("### Ergebnis")

        col_r1, col_r2, col_r3 = st.columns(3)

        with col_r1:
            st.metric("Wirtschaftlichkeitsgrenze", f"{ergebnis['wirtschaftlichkeitsgrenze']:,.2f} EUR")

        with col_r2:
            st.metric("Reparaturkosten", f"{ergebnis['reparaturkosten']:,.2f} EUR")

        with col_r3:
            st.metric("Totalschaden-Abrechnung", f"{ergebnis['abrechnungsbetrag_totalschaden']:,.2f} EUR")

        if ergebnis['ist_totalschaden']:
            st.error(f"""
            ### ⚠️ Wirtschaftlicher Totalschaden

            Die Reparaturkosten ({reparaturkosten:,.2f} EUR) übersteigen
            die Wirtschaftlichkeitsgrenze ({ergebnis['wirtschaftlichkeitsgrenze']:,.2f} EUR = {grenzwert}% vom WBW).

            **Empfehlung:** {ergebnis['empfehlung']}

            Bei Totalschadenabrechnung erhält der Geschädigte:
            **{ergebnis['abrechnungsbetrag_totalschaden']:,.2f} EUR** (WBW - Restwert)
            """)
        else:
            st.success(f"""
            ### ✅ Reparatur wirtschaftlich

            Die Reparaturkosten ({reparaturkosten:,.2f} EUR) liegen unter
            der Wirtschaftlichkeitsgrenze ({ergebnis['wirtschaftlichkeitsgrenze']:,.2f} EUR).

            **Empfehlung:** {ergebnis['empfehlung']}

            {'Integritätszuschlag möglich (bis 130% des WBW).' if ergebnis['integritaet_moeglich'] else ''}
            """)
