"""
Rechtsanwaltsgebühren-Berechnung
"""
import streamlit as st
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from src.models import UnfallProjekt, GebuehrenBerechnung, KostenPosition, KostenKategorie
from src.ui.components import metric_card, alert
from src.config.database import get_session


def render_gebuehren():
    """Rendert die Gebührenberechnung"""

    st.markdown("## Rechtsanwaltsgebühren")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Bitte wählen Sie zuerst ein Projekt aus.")
        return

    rolle = st.session_state.get("user_rolle", "")

    if rolle not in ["ANWALT", "ADMIN"]:
        st.warning("Diese Funktion ist nur für Rechtsanwälte verfügbar.")
        return

    with get_session() as db:
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == aktives_projekt_id
        ).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        tabs = st.tabs(["Berechnung", "Historische Berechnungen"])

        with tabs[0]:
            _render_berechnung(db, projekt)

        with tabs[1]:
            _render_historie(projekt)


def _render_berechnung(db: Session, projekt: UnfallProjekt):
    """Rendert die Gebührenberechnung"""

    st.markdown("### Streitwert ermitteln")

    # Verfügbare Kostenpositionen anzeigen
    st.markdown("**Kostenpositionen für Streitwertberechnung:**")

    streitwert_kategorien = [
        KostenKategorie.REPARATUR,
        KostenKategorie.GUTACHTEN,
        KostenKategorie.ERSATZWAGEN,
        KostenKategorie.NUTZUNGSAUSFALL,
        KostenKategorie.WERTMINDERUNG,
        KostenKategorie.SONSTIG
    ]

    ausgewaehlte_positionen = []
    streitwert = 0.0

    for kp in projekt.kostenpositionen:
        if kp.kategorie in streitwert_kategorien:
            col1, col2, col3 = st.columns([0.5, 3, 1])

            with col1:
                auswahl = st.checkbox("", value=True, key=f"sw_{kp.id}")

            with col2:
                st.write(f"{kp.kategorie_anzeige}: {kp.beschreibung or ''}")

            with col3:
                st.write(f"{kp.betrag_brutto:,.2f} €")

            if auswahl:
                ausgewaehlte_positionen.append(kp)
                streitwert += kp.betrag_brutto or 0

    # Manueller Streitwert
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        manueller_streitwert = st.number_input(
            "Streitwert manuell festlegen (€)",
            min_value=0.0,
            value=streitwert,
            step=100.0
        )

    with col2:
        st.metric("Berechneter Streitwert", f"{streitwert:,.2f} €")

    # Endgültiger Streitwert
    verwendeter_streitwert = manueller_streitwert if manueller_streitwert > 0 else streitwert

    if verwendeter_streitwert <= 0:
        st.warning("Bitte Streitwert festlegen.")
        return

    st.markdown("---")
    st.markdown("### Gebührenberechnung")

    # Gebührenoptionen
    col1, col2 = st.columns(2)

    with col1:
        geschaeftsgebuehr_faktor = st.slider(
            "Geschäftsgebühr (Faktor)",
            min_value=0.5,
            max_value=2.5,
            value=1.3,
            step=0.1,
            help="Standard: 1,3 (Rahmen: 0,5 - 2,5)"
        )

    with col2:
        einigungsgebuehr = st.checkbox("Einigungsgebühr hinzufügen (1,5-fach)")

    col1, col2 = st.columns(2)

    with col1:
        auslagenpauschale = st.number_input(
            "Auslagenpauschale (€)",
            min_value=0.0,
            value=20.0,
            step=5.0
        )

    with col2:
        sonstige_auslagen = st.number_input(
            "Sonstige Auslagen (€)",
            min_value=0.0,
            value=0.0,
            step=10.0
        )

    # Berechnung durchführen
    berechnung = GebuehrenBerechnung(
        unfallprojekt_id=projekt.id,
        streitwert=verwendeter_streitwert,
        geschaeftsgebuehr_faktor=geschaeftsgebuehr_faktor,
        einigungsgebuehr_faktor=1.5 if einigungsgebuehr else 0,
        auslagenpauschale=auslagenpauschale,
        sonstige_auslagen=sonstige_auslagen,
        gesamt_brutto=0  # Wird von berechne() gesetzt
    )

    berechnung.berechne()

    # Ergebnis anzeigen
    st.markdown("---")
    st.markdown("### Ergebnis")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Aufstellung
        for label, wert in berechnung.aufstellung:
            if label == "":
                st.markdown("---")
            elif "Gesamt" in label:
                st.markdown(f"**{label}:** **{wert}**")
            else:
                st.write(f"{label}: {wert}")

    with col2:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            color: white;
        ">
            <div style="font-size: 0.875rem; opacity: 0.9;">Gesamtgebühren</div>
            <div style="font-size: 2rem; font-weight: 700; margin-top: 0.5rem;">
                {berechnung.gesamt_brutto:,.2f} €
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Speichern
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Berechnung speichern", type="primary", use_container_width=True):
            db.add(berechnung)
            db.flush()
            st.success("Berechnung wurde gespeichert.")

            # Kostenposition erstellen
            if st.checkbox("Als Kostenposition hinzufügen", value=True):
                kostenposition = KostenPosition(
                    unfallprojekt_id=projekt.id,
                    kategorie=KostenKategorie.RA_GEBUEHREN,
                    beschreibung=f"Rechtsanwaltsgebühren (Streitwert: {verwendeter_streitwert:,.2f} €)",
                    betrag_brutto=berechnung.gesamt_brutto,
                    erstellt_von_user_id=st.session_state.get("user_id")
                )
                db.add(kostenposition)

            st.rerun()

    with col2:
        if st.button("RVG-Tabelle anzeigen"):
            _zeige_rvg_tabelle()


def _render_historie(projekt: UnfallProjekt):
    """Zeigt historische Berechnungen an"""

    st.markdown("### Berechnungshistorie")

    if not projekt.gebuehrenberechnungen:
        st.info("Noch keine Berechnungen gespeichert.")
        return

    for berechnung in sorted(
        projekt.gebuehrenberechnungen,
        key=lambda x: x.stand_datum or date.min,
        reverse=True
    ):
        with st.expander(f"Berechnung vom {berechnung.stand_datum.strftime('%d.%m.%Y') if berechnung.stand_datum else '-'}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Streitwert:** {berechnung.streitwert:,.2f} €")
                st.write(f"**Geschäftsgebühr ({berechnung.geschaeftsgebuehr_faktor}x):** {berechnung.geschaeftsgebuehr:,.2f} €")
                if berechnung.einigungsgebuehr > 0:
                    st.write(f"**Einigungsgebühr:** {berechnung.einigungsgebuehr:,.2f} €")

            with col2:
                st.write(f"**Auslagenpauschale:** {berechnung.auslagenpauschale:,.2f} €")
                st.write(f"**MwSt ({berechnung.umsatzsteuer_satz}%):** {berechnung.umsatzsteuer:,.2f} €")
                st.write(f"**Gesamt:** {berechnung.gesamt_brutto:,.2f} €")


def _zeige_rvg_tabelle():
    """Zeigt die RVG-Gebührentabelle an"""

    st.markdown("### RVG-Gebührentabelle (Auszug)")

    tabelle = [
        (500, 49.00),
        (1000, 88.00),
        (2000, 166.00),
        (3000, 222.00),
        (4000, 278.00),
        (5000, 334.00),
        (6000, 390.00),
        (8000, 502.00),
        (10000, 614.00),
        (13000, 666.00),
        (16000, 718.00),
        (22000, 822.00),
        (30000, 955.00),
        (40000, 1117.00),
        (50000, 1279.00),
        (65000, 1373.00),
        (80000, 1467.00),
        (100000, 1561.00),
    ]

    col1, col2 = st.columns(2)

    for i, (grenze, wert) in enumerate(tabelle):
        with (col1 if i < len(tabelle) // 2 else col2):
            st.write(f"bis {grenze:,} €: **{wert:,.2f} €**")
