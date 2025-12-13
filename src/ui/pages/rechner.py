"""
Schadensrechner für Nutzungsausfall und Merkantilen Minderwert
"""
import streamlit as st
from decimal import Decimal
from datetime import datetime

from src.services.schadensrechner import (
    get_nutzungsausfall_rechner,
    get_minderwert_rechner
)
from src.services.pdf_export import get_pdf_service
from src.ui.components import badge
from src.config.database import get_session
from src.models import UnfallProjekt


def render_rechner():
    """Rendert die Schadensrechner-Seite"""

    st.markdown("## Schadensrechner")

    tabs = st.tabs([
        "Nutzungsausfall",
        "Merkantiler Minderwert",
        "PDF-Export"
    ])

    with tabs[0]:
        _render_nutzungsausfall_rechner()

    with tabs[1]:
        _render_minderwert_rechner()

    with tabs[2]:
        _render_pdf_export()


def _render_nutzungsausfall_rechner():
    """Rendert den Nutzungsausfallrechner"""

    st.markdown("### Nutzungsausfallentschädigung")
    st.caption("Berechnung nach Sanden/Danner/Küppersbusch")

    rechner = get_nutzungsausfall_rechner()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Fahrzeugdaten")

        # Option 1: Manuelle Auswahl
        eingabe_art = st.radio(
            "Eingabeart",
            ["Fahrzeuggruppe auswählen", "Modell eingeben"],
            horizontal=True
        )

        if eingabe_art == "Fahrzeuggruppe auswählen":
            gruppen_optionen = {
                "A - Kleinstwagen (Smart, Twingo) - 23 €/Tag": "A",
                "B - Kleinwagen (Polo, Corsa) - 29 €/Tag": "B",
                "C - Kompaktklasse (Golf, Focus) - 35 €/Tag": "C",
                "D - Mittelklasse (Passat, A4, 3er) - 43 €/Tag": "D",
                "E - Obere Mittelklasse (E-Klasse, 5er) - 50 €/Tag": "E",
                "F - Oberklasse (S-Klasse, 7er) - 59 €/Tag": "F",
                "G - Luxusklasse - 65 €/Tag": "G",
                "H - Sportwagen - 79 €/Tag": "H",
                "SUV Klein - Kompakt-SUV - 43 €/Tag": "SUV_KLEIN",
                "SUV Mittel - Mittelklasse-SUV - 59 €/Tag": "SUV_MITTEL",
                "SUV Groß - Oberklasse-SUV - 79 €/Tag": "SUV_GROSS",
            }

            auswahl = st.selectbox("Fahrzeuggruppe", list(gruppen_optionen.keys()))
            fahrzeuggruppe = gruppen_optionen[auswahl]

        else:
            modell = st.text_input("Fahrzeugmodell", placeholder="z.B. Golf, 3er, E-Klasse")
            if modell:
                fahrzeuggruppe = rechner.ermittle_fahrzeuggruppe(modell)
                st.info(f"Ermittelte Gruppe: {fahrzeuggruppe} ({rechner._get_hinweis(fahrzeuggruppe)})")
            else:
                fahrzeuggruppe = "C"

    with col2:
        st.markdown("#### Ausfallzeit")

        ausfall_tage = st.number_input(
            "Ausfalltage gesamt",
            min_value=1,
            max_value=365,
            value=14
        )

        schadensart = st.radio(
            "Schadensart",
            ["Reparaturschaden", "Totalschaden"],
            horizontal=True
        )

        if schadensart == "Reparaturschaden":
            reparatur_tage = st.number_input(
                "Reparaturdauer (Tage)",
                min_value=1,
                max_value=90,
                value=min(ausfall_tage, 7),
                help="Die Nutzungsausfallentschädigung ist auf die Reparaturdauer begrenzt"
            )
            wiederbeschaffung_tage = None
        else:
            wiederbeschaffung_tage = st.number_input(
                "Wiederbeschaffungsdauer (Tage)",
                min_value=1,
                max_value=30,
                value=14,
                help="Standard: 14 Tage für Wiederbeschaffung"
            )
            reparatur_tage = None

    # Berechnung
    st.markdown("---")

    if st.button("Berechnen", type="primary", use_container_width=True):
        ergebnis = rechner.berechne_nutzungsausfall(
            fahrzeuggruppe=fahrzeuggruppe,
            ausfall_tage=ausfall_tage,
            reparatur_tage=reparatur_tage,
            wiederbeschaffung_tage=wiederbeschaffung_tage
        )

        st.session_state["nutzungsausfall_ergebnis"] = ergebnis

    # Ergebnis anzeigen
    if "nutzungsausfall_ergebnis" in st.session_state:
        ergebnis = st.session_state["nutzungsausfall_ergebnis"]

        st.markdown("### Ergebnis")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Tagessatz", f"{float(ergebnis['tagessatz']):,.2f} €")

        with col2:
            st.metric("Ausfalltage", ergebnis['ausfall_tage'])

        with col3:
            st.metric("Gesamtbetrag", f"{float(ergebnis['gesamt_betrag']):,.2f} €")

        st.info(f"**Fahrzeuggruppe:** {ergebnis['fahrzeuggruppe']} - {ergebnis['hinweis']}")

        # Formel anzeigen
        with st.expander("Berechnungsdetails"):
            st.markdown(f"""
            **Formel:**
            ```
            Nutzungsausfall = Tagessatz × Ausfalltage
            {float(ergebnis['tagessatz']):,.2f} € × {ergebnis['ausfall_tage']} Tage = {float(ergebnis['gesamt_betrag']):,.2f} €
            ```

            **Hinweise:**
            - Die Tagessätze basieren auf der Tabelle Sanden/Danner/Küppersbusch
            - Bei Totalschaden: Beschränkung auf Wiederbeschaffungsdauer (i.d.R. 14 Tage)
            - Bei Reparatur: Beschränkung auf tatsächliche Reparaturdauer
            """)


def _render_minderwert_rechner():
    """Rendert den Minderwertrechner"""

    st.markdown("### Merkantiler Minderwert")
    st.caption("Berechnung nach verschiedenen Methoden")

    rechner = get_minderwert_rechner()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Fahrzeugwerte")

        wiederbeschaffungswert = st.number_input(
            "Wiederbeschaffungswert (€)",
            min_value=1000,
            max_value=500000,
            value=25000,
            step=500
        )

        reparaturkosten = st.number_input(
            "Reparaturkosten netto (€)",
            min_value=100,
            max_value=100000,
            value=5000,
            step=100
        )

    with col2:
        st.markdown("#### Fahrzeugdaten")

        fahrzeugalter_monate = st.number_input(
            "Fahrzeugalter (Monate)",
            min_value=1,
            max_value=180,
            value=36,
            help="Fahrzeugalter in Monaten seit Erstzulassung"
        )

        laufleistung = st.number_input(
            "Laufleistung (km)",
            min_value=1000,
            max_value=500000,
            value=50000,
            step=1000
        )

    # Anspruchsprüfung
    st.markdown("---")

    anspruch, begruendung = rechner.pruefe_anspruch(
        fahrzeugalter_monate=fahrzeugalter_monate,
        laufleistung_km=laufleistung,
        wiederbeschaffungswert=Decimal(str(wiederbeschaffungswert))
    )

    if anspruch:
        st.success(begruendung)
    else:
        st.warning(begruendung)

    # Berechnung
    if st.button("Minderwert berechnen", type="primary", use_container_width=True):
        ergebnis = rechner.berechne_alle_methoden(
            wiederbeschaffungswert=Decimal(str(wiederbeschaffungswert)),
            reparaturkosten=Decimal(str(reparaturkosten)),
            fahrzeugalter_monate=fahrzeugalter_monate,
            laufleistung_km=laufleistung
        )

        st.session_state["minderwert_ergebnis"] = ergebnis

    # Ergebnis anzeigen
    if "minderwert_ergebnis" in st.session_state:
        ergebnis = st.session_state["minderwert_ergebnis"]

        st.markdown("### Ergebnis")

        # Empfehlung
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(
                f"""
                <div style="background-color: #dcfce7; border: 2px solid #16a34a; border-radius: 10px; padding: 20px; text-align: center;">
                    <h3 style="color: #16a34a; margin: 0;">Empfohlener Minderwert</h3>
                    <h1 style="color: #16a34a; margin: 10px 0;">{float(ergebnis['empfehlung']):,.2f} €</h1>
                    <p style="color: #6b7280; margin: 0;">Mittelwert aller Methoden</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("#### Methodenvergleich")

        col1, col2, col3 = st.columns(3)

        with col1:
            rs = ergebnis['ruhkopf_sahm']
            st.markdown("**Ruhkopf/Sahm**")
            st.metric("Minderwert", f"{float(rs['minderwert']):,.2f} €")
            st.caption(f"Altersfaktor: {rs['faktor']}")

        with col2:
            hg = ergebnis['halbgewachs']
            st.markdown("**Halbgewachs**")
            st.metric("Minderwert", f"{float(hg['minderwert']):,.2f} €")
            st.caption(f"Faktor: {hg['faktor']*100}%")

        with col3:
            dvgt = ergebnis['dvgt']
            st.markdown("**DVGT**")
            st.metric("Minderwert", f"{float(dvgt['minderwert']):,.2f} €")
            st.caption(dvgt['hinweis'])

        # Details
        with st.expander("Berechnungsdetails"):
            st.markdown("""
            **Methode Ruhkopf/Sahm:**
            ```
            Minderwert = (Reparaturkosten × WBW) / (Reparaturkosten + WBW) × Altersfaktor
            ```

            **Methode Halbgewachs:**
            ```
            Minderwert = Reparaturkosten × Faktor (5-10%)
            ```

            **Methode DVGT:**
            ```
            Minderwert = WBW × Grundfaktor × Altersfaktor × Laufleistungsfaktor
            ```

            **Hinweise:**
            - Der Anspruch auf merkantilen Minderwert kann entfallen bei:
              - Fahrzeugalter > 5-7 Jahre
              - Laufleistung > 100.000-150.000 km
              - Wiederbeschaffungswert < 4.000-5.000 €
            - Die Rechtsprechung variiert regional
            """)


def _render_pdf_export():
    """Rendert die PDF-Export-Optionen"""

    st.markdown("### PDF-Export")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Bitte wählen Sie zuerst ein Projekt aus.")

        # Projektauswahl anbieten
        with get_session() as db:
            rolle = st.session_state.get("user_rolle")
            user_id = st.session_state.get("user_id")

            query = db.query(UnfallProjekt)
            if rolle == "ANWALT":
                query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
            elif rolle == "WERKSTATT":
                query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)

            projekte = query.all()

            if projekte:
                projekt_optionen = {
                    f"{p.aktenzeichen or p.projektnummer}": p.id
                    for p in projekte
                }

                ausgewaehltes = st.selectbox("Projekt auswählen", list(projekt_optionen.keys()))

                if st.button("Projekt auswählen"):
                    st.session_state["aktives_projekt_id"] = projekt_optionen[ausgewaehltes]
                    st.rerun()
        return

    with get_session() as db:
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == aktives_projekt_id
        ).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        st.info(f"**Aktives Projekt:** {projekt.aktenzeichen or projekt.projektnummer}")

        pdf_service = get_pdf_service()

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Projektbericht")
            st.caption("Vollständiger Bericht mit allen Projektdaten")

            if st.button("Projektbericht generieren", use_container_width=True):
                try:
                    pdf_bytes = pdf_service.exportiere_projektbericht(projekt)
                    st.download_button(
                        "📥 PDF herunterladen",
                        data=pdf_bytes,
                        file_name=f"Projektbericht_{projekt.aktenzeichen or projekt.projektnummer}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Fehler beim Generieren: {e}")

        with col2:
            st.markdown("#### Kostenübersicht")
            st.caption("Aufstellung aller Schadenspositionen")

            if st.button("Kostenübersicht generieren", use_container_width=True):
                try:
                    pdf_bytes = pdf_service.exportiere_kostenuebersicht(projekt)
                    st.download_button(
                        "📥 PDF herunterladen",
                        data=pdf_bytes,
                        file_name=f"Kostenuebersicht_{projekt.aktenzeichen or projekt.projektnummer}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Fehler beim Generieren: {e}")

        st.markdown("---")

        st.markdown("#### Schadensaufstellung für Anwalt")
        st.caption("Detaillierte Aufstellung mit Nutzungsausfall und Minderwert")

        col1, col2 = st.columns(2)

        with col1:
            include_nutzungsausfall = st.checkbox(
                "Nutzungsausfall einbeziehen",
                value="nutzungsausfall_ergebnis" in st.session_state
            )

        with col2:
            include_minderwert = st.checkbox(
                "Merkantilen Minderwert einbeziehen",
                value="minderwert_ergebnis" in st.session_state
            )

        if st.button("Schadensaufstellung generieren", type="primary", use_container_width=True):
            try:
                nutzungsausfall = st.session_state.get("nutzungsausfall_ergebnis") if include_nutzungsausfall else None
                minderwert = st.session_state.get("minderwert_ergebnis") if include_minderwert else None

                pdf_bytes = pdf_service.exportiere_schadensaufstellung(
                    projekt,
                    nutzungsausfall=nutzungsausfall,
                    minderwert=minderwert
                )
                st.download_button(
                    "📥 Schadensaufstellung herunterladen",
                    data=pdf_bytes,
                    file_name=f"Schadensaufstellung_{projekt.aktenzeichen or projekt.projektnummer}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
            except Exception as e:
                st.error(f"Fehler beim Generieren: {e}")
