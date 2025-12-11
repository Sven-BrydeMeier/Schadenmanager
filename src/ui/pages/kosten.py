"""
Kostenpositionen und Ampelsystem
"""
import streamlit as st
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, KostenPosition, KostenKategorie, KostenAmpel
)
from src.ui.components import kosten_uebersicht, metric_card, badge, alert
from src.config.database import get_session


def render_kosten():
    """Rendert die Kosten-Verwaltung"""

    st.markdown("## Kostenpositionen")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Bitte wählen Sie zuerst ein Projekt aus.")
        return

    with get_session() as db:
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == aktives_projekt_id
        ).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        # Zusammenfassung
        _render_kosten_zusammenfassung(projekt)

        st.markdown("---")

        tabs = st.tabs(["Übersicht", "Neue Position", "Kürzungen"])

        with tabs[0]:
            _render_kosten_liste(db, projekt)

        with tabs[1]:
            _render_neue_position(db, projekt)

        with tabs[2]:
            _render_kuerzungen(db, projekt)


def _render_kosten_zusammenfassung(projekt: UnfallProjekt):
    """Zeigt die Kosten-Zusammenfassung an"""

    positionen = projekt.kostenpositionen

    gesamt = sum(kp.betrag_brutto or 0 for kp in positionen)
    freigegeben = sum(kp.von_versicherung_freigegeben_betrag or 0 for kp in positionen)
    offen = gesamt - freigegeben

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("Gefordert", f"{gesamt:,.2f} €")

    with col2:
        metric_card("Freigegeben", f"{freigegeben:,.2f} €", "success")

    with col3:
        metric_card("Offen", f"{offen:,.2f} €", "warning" if offen > 0 else "success")

    with col4:
        rot = sum(1 for kp in positionen if kp.status_ampel == KostenAmpel.ROT)
        orange = sum(1 for kp in positionen if kp.status_ampel == KostenAmpel.ORANGE)
        gruen = sum(1 for kp in positionen if kp.status_ampel == KostenAmpel.GRUEN)

        st.markdown(f"""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 0.875rem; color: #64748b;">Ampelstatus</div>
            <div style="margin-top: 0.5rem;">
                <span style="color: #dc3545; font-weight: bold;">● {rot}</span>
                <span style="color: #fd7e14; font-weight: bold; margin-left: 1rem;">● {orange}</span>
                <span style="color: #28a745; font-weight: bold; margin-left: 1rem;">● {gruen}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_kosten_liste(db: Session, projekt: UnfallProjekt):
    """Rendert die Liste der Kostenpositionen"""

    st.markdown("### Alle Positionen")

    if not projekt.kostenpositionen:
        st.info("Noch keine Kostenpositionen erfasst.")
        return

    # Sortierung
    sortierung = st.selectbox(
        "Sortierung",
        ["Kategorie", "Betrag (absteigend)", "Status"],
        index=0
    )

    positionen = list(projekt.kostenpositionen)

    if sortierung == "Kategorie":
        positionen.sort(key=lambda x: x.kategorie.value if x.kategorie else "Z")
    elif sortierung == "Betrag (absteigend)":
        positionen.sort(key=lambda x: x.betrag_brutto or 0, reverse=True)
    else:
        status_order = {"ROT": 0, "ORANGE": 1, "GRUEN": 2}
        positionen.sort(key=lambda x: status_order.get(x.status_ampel.value if x.status_ampel else "ROT", 0))

    st.markdown("---")

    rolle = st.session_state.get("user_rolle", "")

    for kp in positionen:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([0.5, 2, 1.5, 1, 1])

            with col1:
                # Ampel-Punkt
                farbe = {
                    KostenAmpel.ROT: "#dc3545",
                    KostenAmpel.ORANGE: "#fd7e14",
                    KostenAmpel.GRUEN: "#28a745"
                }.get(kp.status_ampel, "#6c757d")

                st.markdown(f"""
                <div style="
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    background-color: {farbe};
                    margin-top: 5px;
                "></div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"**{kp.kategorie_anzeige}**")
                if kp.beschreibung:
                    st.caption(kp.beschreibung)

            with col3:
                if kp.gekuerzt and kp.von_versicherung_freigegeben_betrag is not None:
                    st.markdown(f"~~{kp.betrag_brutto:,.2f} €~~ → **{kp.von_versicherung_freigegeben_betrag:,.2f} €**")
                else:
                    st.markdown(f"**{kp.betrag_brutto:,.2f} €**")

            with col4:
                status_text = {
                    KostenAmpel.ROT: "Nicht eingereicht",
                    KostenAmpel.ORANGE: "In Prüfung",
                    KostenAmpel.GRUEN: "Freigegeben"
                }.get(kp.status_ampel, "Unbekannt")
                st.caption(status_text)

            with col5:
                if rolle in ["ANWALT", "WERKSTATT", "ADMIN"]:
                    if st.button("Bearbeiten", key=f"edit_{kp.id}"):
                        st.session_state["edit_kosten_id"] = kp.id
                        st.rerun()

            # Kürzungsinfo anzeigen
            if kp.gekuerzt and kp.kuerzung_grund:
                st.caption(f"Kürzungsgrund: {kp.kuerzung_grund}")

            st.markdown("---")


def _render_neue_position(db: Session, projekt: UnfallProjekt):
    """Formular für neue Kostenposition"""

    st.markdown("### Neue Kostenposition")

    with st.form("neue_kostenposition"):
        col1, col2 = st.columns(2)

        with col1:
            kategorie = st.selectbox(
                "Kategorie*",
                options=[k.value for k in KostenKategorie],
                format_func=lambda x: {
                    "REPARATUR": "Reparaturkosten",
                    "GUTACHTEN": "Gutachterkosten",
                    "ERSATZWAGEN": "Ersatzwagen/Mietwagen",
                    "NUTZUNGSAUSFALL": "Nutzungsausfall",
                    "WERTMINDERUNG": "Wertminderung",
                    "SONSTIG": "Sonstige Kosten",
                    "RA_GEBUEHREN": "Rechtsanwaltsgebühren"
                }.get(x, x)
            )

        with col2:
            beschreibung = st.text_input("Beschreibung")

        col1, col2, col3 = st.columns(3)

        with col1:
            betrag_netto = st.number_input("Nettobetrag (€)", min_value=0.0, step=10.0)

        with col2:
            mwst_satz = st.selectbox("MwSt-Satz", [0.0, 7.0, 19.0], index=2)

        with col3:
            betrag_brutto = betrag_netto * (1 + mwst_satz / 100) if betrag_netto > 0 else 0
            st.metric("Bruttobetrag", f"{betrag_brutto:,.2f} €")

        status = st.selectbox(
            "Status",
            options=[s.value for s in KostenAmpel],
            format_func=lambda x: {
                "ROT": "Nicht eingereicht",
                "ORANGE": "Eingereicht / In Prüfung",
                "GRUEN": "Freigegeben / Bezahlt"
            }.get(x, x),
            index=0
        )

        submitted = st.form_submit_button("Position hinzufügen", use_container_width=True)

        if submitted:
            if betrag_netto <= 0:
                st.error("Bitte einen Betrag eingeben.")
            else:
                neue_position = KostenPosition(
                    unfallprojekt_id=projekt.id,
                    kategorie=KostenKategorie(kategorie),
                    beschreibung=beschreibung,
                    betrag_netto=betrag_netto,
                    mwst_satz=mwst_satz,
                    betrag_brutto=round(betrag_brutto, 2),
                    status_ampel=KostenAmpel(status),
                    erstellt_von_user_id=st.session_state.get("user_id")
                )

                db.add(neue_position)
                db.flush()

                st.success("Kostenposition wurde hinzugefügt.")
                st.rerun()


def _render_kuerzungen(db: Session, projekt: UnfallProjekt):
    """Zeigt Kürzungen und ermöglicht deren Bearbeitung"""

    st.markdown("### Kürzungen verwalten")

    rolle = st.session_state.get("user_rolle", "")

    gekuerzte_positionen = [
        kp for kp in projekt.kostenpositionen
        if kp.gekuerzt or kp.von_versicherung_freigegeben_betrag is not None
    ]

    if not gekuerzte_positionen:
        st.info("Keine Kürzungen vorhanden.")

        # Für Versicherungen: Kürzungen hinzufügen
        if rolle in ["VERSICHERUNG_EIGEN", "VERSICHERUNG_GEGNER", "ADMIN"]:
            st.markdown("---")
            st.markdown("### Position kürzen")

            offene_positionen = [
                kp for kp in projekt.kostenpositionen
                if kp.status_ampel in [KostenAmpel.ROT, KostenAmpel.ORANGE]
            ]

            if offene_positionen:
                position_optionen = {
                    f"{kp.kategorie_anzeige} - {kp.betrag_brutto:,.2f} €": kp
                    for kp in offene_positionen
                }

                ausgewaehlte = st.selectbox(
                    "Position auswählen",
                    list(position_optionen.keys())
                )

                if ausgewaehlte:
                    position = position_optionen[ausgewaehlte]

                    col1, col2 = st.columns(2)

                    with col1:
                        freigabe_betrag = st.number_input(
                            "Freigegebener Betrag (€)",
                            min_value=0.0,
                            max_value=float(position.betrag_brutto),
                            value=float(position.betrag_brutto)
                        )

                    with col2:
                        kuerzung_grund = st.text_area("Begründung der Kürzung")

                    if st.button("Kürzung speichern"):
                        position.von_versicherung_freigegeben_betrag = freigabe_betrag
                        position.gekuerzt = freigabe_betrag < position.betrag_brutto
                        position.kuerzung_betrag = position.betrag_brutto - freigabe_betrag
                        position.kuerzung_grund = kuerzung_grund
                        position.status_ampel = KostenAmpel.GRUEN if not position.gekuerzt else KostenAmpel.ORANGE
                        position.entscheidung_am = datetime.now()

                        db.flush()
                        st.success("Kürzung wurde gespeichert.")
                        st.rerun()
        return

    # Kürzungen anzeigen
    gesamt_gefordert = sum(kp.betrag_brutto or 0 for kp in gekuerzte_positionen)
    gesamt_freigegeben = sum(kp.von_versicherung_freigegeben_betrag or 0 for kp in gekuerzte_positionen)
    gesamt_gekuerzt = gesamt_gefordert - gesamt_freigegeben

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Gefordert", f"{gesamt_gefordert:,.2f} €")

    with col2:
        st.metric("Freigegeben", f"{gesamt_freigegeben:,.2f} €")

    with col3:
        st.metric("Kürzung", f"{gesamt_gekuerzt:,.2f} €", delta=f"-{gesamt_gekuerzt:,.2f} €")

    st.markdown("---")

    for kp in gekuerzte_positionen:
        with st.expander(f"{kp.kategorie_anzeige} - Kürzung: {kp.differenz_betrag:,.2f} €"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Gefordert:** {kp.betrag_brutto:,.2f} €")
                st.write(f"**Freigegeben:** {kp.von_versicherung_freigegeben_betrag:,.2f} €")
                st.write(f"**Differenz:** {kp.differenz_betrag:,.2f} €")

            with col2:
                st.write("**Begründung:**")
                st.write(kp.kuerzung_grund or "Keine Begründung angegeben")

            # Für Anwälte: Erwiderung erstellen
            if rolle == "ANWALT":
                st.markdown("---")
                if st.button("Erwiderung erstellen", key=f"erwidern_{kp.id}"):
                    st.session_state["erwiderung_position_id"] = kp.id
                    st.session_state["page"] = "Korrespondenz"
                    st.rerun()
