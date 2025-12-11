"""
Korrespondenz-Verwaltung mit KI-Textgenerierung
"""
import streamlit as st
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, Korrespondenz, KorrespondenzRichtung
)
from src.services.ki_textgenerator import get_ki_textgenerator
from src.ui.components import badge, alert
from src.config.database import get_session


def render_korrespondenz():
    """Rendert die Korrespondenz-Verwaltung"""

    st.markdown("## Korrespondenz")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Bitte wählen Sie zuerst ein Projekt aus.")
        return

    rolle = st.session_state.get("user_rolle", "")

    with get_session() as db:
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == aktives_projekt_id
        ).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        tabs = st.tabs(["Übersicht", "Neues Schreiben", "KI-Assistent"])

        with tabs[0]:
            _render_korrespondenz_liste(db, projekt)

        with tabs[1]:
            if rolle in ["ANWALT", "ADMIN"]:
                _render_neues_schreiben(db, projekt)
            else:
                st.info("Nur Anwälte können Schreiben erstellen.")

        with tabs[2]:
            if rolle in ["ANWALT", "ADMIN"]:
                _render_ki_assistent(db, projekt)
            else:
                st.info("Der KI-Assistent ist nur für Anwälte verfügbar.")


def _render_korrespondenz_liste(db: Session, projekt: UnfallProjekt):
    """Zeigt die Korrespondenzliste an"""

    st.markdown("### Korrespondenz-Verlauf")

    if not projekt.korrespondenzen:
        st.info("Noch keine Korrespondenz vorhanden.")
        return

    # Filter
    col1, col2 = st.columns(2)

    with col1:
        richtung_filter = st.selectbox(
            "Richtung",
            ["Alle"] + [r.value for r in KorrespondenzRichtung],
            format_func=lambda x: {
                "Alle": "Alle",
                "RA_AN_VERSICHERUNG": "Anwalt → Versicherung",
                "VERSICHERUNG_AN_RA": "Versicherung → Anwalt",
                "RA_AN_MANDANT": "Anwalt → Mandant",
                "MANDANT_AN_RA": "Mandant → Anwalt",
                "WERKSTATT_AN_VERSICHERUNG": "Werkstatt → Versicherung",
                "SONSTIG": "Sonstige"
            }.get(x, x),
            index=0
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["Alle", "ENTWURF", "FREIGEGEBEN", "VERSENDET"],
            format_func=lambda x: {
                "Alle": "Alle",
                "ENTWURF": "Entwurf",
                "FREIGEGEBEN": "Freigegeben",
                "VERSENDET": "Versendet"
            }.get(x, x),
            index=0
        )

    # Filtern
    korrespondenzen = list(projekt.korrespondenzen)

    if richtung_filter != "Alle":
        korrespondenzen = [k for k in korrespondenzen if k.richtung and k.richtung.value == richtung_filter]

    if status_filter != "Alle":
        korrespondenzen = [k for k in korrespondenzen if k.status == status_filter]

    # Sortieren
    korrespondenzen.sort(key=lambda x: x.erstellt_am or datetime.min, reverse=True)

    st.markdown("---")

    for korr in korrespondenzen:
        with st.expander(f"{korr.richtung_anzeige}: {korr.betreff or 'Ohne Betreff'}"):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**Erstellt:** {korr.erstellt_am.strftime('%d.%m.%Y %H:%M') if korr.erstellt_am else '-'}")
                if korr.bezug:
                    st.write(f"**Bezug:** {korr.bezug}")

            with col2:
                status_style = {
                    "ENTWURF": "warning",
                    "FREIGEGEBEN": "info",
                    "VERSENDET": "success"
                }.get(korr.status, "secondary")
                st.markdown(badge(korr.status_anzeige, status_style), unsafe_allow_html=True)

            with col3:
                if korr.ki_generiert:
                    st.markdown(badge("KI", "info"), unsafe_allow_html=True)

            # Text anzeigen
            st.markdown("---")
            st.text_area(
                "Inhalt",
                korr.aktueller_text,
                height=200,
                disabled=True,
                key=f"text_{korr.id}"
            )

            # Aktionen
            rolle = st.session_state.get("user_rolle", "")

            if rolle in ["ANWALT", "ADMIN"]:
                col1, col2, col3 = st.columns(3)

                with col1:
                    if korr.status == "ENTWURF":
                        if st.button("Freigeben", key=f"approve_{korr.id}"):
                            korr.text_final = korr.text_entwurf
                            korr.status = "FREIGEGEBEN"
                            db.flush()
                            st.rerun()

                with col2:
                    if korr.status == "FREIGEGEBEN":
                        if st.button("Als versendet markieren", key=f"send_{korr.id}"):
                            korr.status = "VERSENDET"
                            korr.versendet_am = datetime.now()
                            db.flush()
                            st.rerun()

                with col3:
                    if korr.status == "ENTWURF":
                        if st.button("Bearbeiten", key=f"edit_{korr.id}"):
                            st.session_state["edit_korrespondenz_id"] = korr.id
                            st.rerun()


def _render_neues_schreiben(db: Session, projekt: UnfallProjekt):
    """Formular für neues Schreiben"""

    st.markdown("### Neues Schreiben erstellen")

    # Prüfen ob Bearbeitung
    edit_id = st.session_state.get("edit_korrespondenz_id")
    bestehende_korrespondenz = None

    if edit_id:
        bestehende_korrespondenz = db.query(Korrespondenz).filter(
            Korrespondenz.id == edit_id
        ).first()

    with st.form("neue_korrespondenz"):
        richtung = st.selectbox(
            "Richtung",
            options=[r.value for r in KorrespondenzRichtung],
            format_func=lambda x: {
                "RA_AN_VERSICHERUNG": "Anwalt → Versicherung",
                "VERSICHERUNG_AN_RA": "Versicherung → Anwalt",
                "RA_AN_MANDANT": "Anwalt → Mandant",
                "MANDANT_AN_RA": "Mandant → Anwalt",
                "WERKSTATT_AN_VERSICHERUNG": "Werkstatt → Versicherung",
                "SONSTIG": "Sonstige"
            }.get(x, x),
            index=0
        )

        col1, col2 = st.columns(2)

        with col1:
            betreff = st.text_input(
                "Betreff",
                value=bestehende_korrespondenz.betreff if bestehende_korrespondenz else ""
            )

        with col2:
            bezug = st.text_input(
                "Bezug/Aktenzeichen",
                value=bestehende_korrespondenz.bezug if bestehende_korrespondenz else ""
            )

        text = st.text_area(
            "Text",
            value=bestehende_korrespondenz.aktueller_text if bestehende_korrespondenz else "",
            height=400
        )

        col1, col2 = st.columns(2)

        with col1:
            als_entwurf = st.checkbox("Als Entwurf speichern", value=True)

        with col2:
            antwort_erwartet = st.checkbox("Antwort erwartet", value=True)

        submitted = st.form_submit_button("Speichern", use_container_width=True)

        if submitted:
            if not text:
                st.error("Bitte Text eingeben.")
            else:
                if bestehende_korrespondenz:
                    # Bearbeiten
                    bestehende_korrespondenz.betreff = betreff
                    bestehende_korrespondenz.bezug = bezug
                    bestehende_korrespondenz.text_entwurf = text
                    bestehende_korrespondenz.status = "ENTWURF" if als_entwurf else "FREIGEGEBEN"
                    if not als_entwurf:
                        bestehende_korrespondenz.text_final = text
                    st.session_state["edit_korrespondenz_id"] = None
                else:
                    # Neu erstellen
                    neue_korrespondenz = Korrespondenz(
                        unfallprojekt_id=projekt.id,
                        erstellt_von_user_id=st.session_state.get("user_id"),
                        richtung=KorrespondenzRichtung(richtung),
                        betreff=betreff,
                        bezug=bezug,
                        text_entwurf=text,
                        text_final=None if als_entwurf else text,
                        status="ENTWURF" if als_entwurf else "FREIGEGEBEN",
                        antwort_erwartet=antwort_erwartet,
                        ki_generiert=False
                    )
                    db.add(neue_korrespondenz)

                db.flush()
                st.success("Schreiben wurde gespeichert.")
                st.rerun()


def _render_ki_assistent(db: Session, projekt: UnfallProjekt):
    """KI-Assistent für Textgenerierung"""

    st.markdown("### KI-Textassistent")

    ki_generator = get_ki_textgenerator()

    schreiben_typ = st.selectbox(
        "Art des Schreibens",
        [
            "Anspruchsschreiben an Versicherung",
            "Erwiderung auf Kürzungsschreiben",
            "Mandanteninformation"
        ]
    )

    if schreiben_typ == "Anspruchsschreiben an Versicherung":
        st.markdown("""
        Der KI-Assistent erstellt ein professionelles Anspruchsschreiben basierend auf:
        - Den Unfalldaten
        - Den erfassten Kostenpositionen
        - Rechtlichen Standardformulierungen
        """)

        if st.button("Anspruchsschreiben generieren", type="primary"):
            with st.spinner("KI generiert Schreiben..."):
                text, fehler = ki_generator.generiere_anspruchsschreiben(projekt, db)

                if text:
                    st.markdown("---")
                    st.markdown("### Generierter Entwurf")
                    st.text_area("", text, height=500, key="generated_text")

                    if st.button("Als Entwurf speichern"):
                        korrespondenz = Korrespondenz(
                            unfallprojekt_id=projekt.id,
                            erstellt_von_user_id=st.session_state.get("user_id"),
                            richtung=KorrespondenzRichtung.RA_AN_VERSICHERUNG,
                            betreff=f"Schadensersatzansprüche aus Verkehrsunfall vom {projekt.datum_unfall.strftime('%d.%m.%Y') if projekt.datum_unfall else 'unbekannt'}",
                            text_entwurf=text,
                            status="ENTWURF",
                            ki_generiert=True,
                            antwort_erwartet=True
                        )
                        db.add(korrespondenz)
                        db.flush()
                        st.success("Entwurf wurde gespeichert!")
                        st.rerun()
                else:
                    st.error(f"Fehler bei der Generierung: {fehler}")

    elif schreiben_typ == "Erwiderung auf Kürzungsschreiben":
        st.markdown("""
        Der KI-Assistent erstellt eine Erwiderung auf Kürzungen der Versicherung.
        """)

        # Kürzungen anzeigen
        gekuerzte = [kp for kp in projekt.kostenpositionen if kp.gekuerzt]

        if not gekuerzte:
            st.info("Keine Kürzungen im Projekt vorhanden.")
        else:
            st.markdown("**Gekürzte Positionen:**")

            kuerzungen = []
            for kp in gekuerzte:
                st.write(f"- {kp.kategorie_anzeige}: {kp.betrag_brutto:,.2f} € → {kp.von_versicherung_freigegeben_betrag:,.2f} €")
                kuerzungen.append({
                    "position": kp.kategorie_anzeige,
                    "gefordert": kp.betrag_brutto,
                    "anerkannt": kp.von_versicherung_freigegeben_betrag,
                    "gekuerzt": kp.kuerzung_betrag,
                    "begruendung": kp.kuerzung_grund
                })

            if st.button("Erwiderung generieren", type="primary"):
                with st.spinner("KI generiert Erwiderung..."):
                    text, fehler = ki_generator.generiere_kuerzungserwiderung(projekt, kuerzungen, db)

                    if text:
                        st.markdown("---")
                        st.markdown("### Generierter Entwurf")
                        st.text_area("", text, height=500, key="generated_response")

                        if st.button("Als Entwurf speichern", key="save_response"):
                            korrespondenz = Korrespondenz(
                                unfallprojekt_id=projekt.id,
                                erstellt_von_user_id=st.session_state.get("user_id"),
                                richtung=KorrespondenzRichtung.RA_AN_VERSICHERUNG,
                                betreff="Erwiderung auf Ihre Kürzungen",
                                text_entwurf=text,
                                status="ENTWURF",
                                ki_generiert=True,
                                antwort_erwartet=True
                            )
                            db.add(korrespondenz)
                            db.flush()
                            st.success("Entwurf wurde gespeichert!")
                            st.rerun()
                    else:
                        st.error(f"Fehler bei der Generierung: {fehler}")

    else:  # Mandanteninformation
        st.markdown("""
        Der KI-Assistent erstellt eine verständliche Information für den Mandanten.
        """)

        thema = st.selectbox(
            "Thema",
            [
                "Aktueller Verfahrensstand",
                "Erklärung der Kürzungen",
                "Nächste Schritte"
            ]
        )

        if st.button("Information generieren", type="primary"):
            with st.spinner("KI generiert Information..."):
                text, fehler = ki_generator.generiere_mandanteninformation(projekt, thema, db)

                if text:
                    st.markdown("---")
                    st.markdown("### Generierter Entwurf")
                    st.text_area("", text, height=400, key="generated_info")

                    if st.button("Als Entwurf speichern", key="save_info"):
                        korrespondenz = Korrespondenz(
                            unfallprojekt_id=projekt.id,
                            erstellt_von_user_id=st.session_state.get("user_id"),
                            richtung=KorrespondenzRichtung.RA_AN_MANDANT,
                            betreff=f"Information: {thema}",
                            text_entwurf=text,
                            status="ENTWURF",
                            ki_generiert=True,
                            antwort_erwartet=False
                        )
                        db.add(korrespondenz)
                        db.flush()
                        st.success("Entwurf wurde gespeichert!")
                        st.rerun()
                else:
                    st.error(f"Fehler bei der Generierung: {fehler}")
