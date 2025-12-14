"""
Ermittlungsakte - Verwaltung von Ermittlungsakten der Staatsanwaltschaft
"""
import streamlit as st
import json
from datetime import datetime

from src.config.database import get_session
from src.services.ermittlungsakte import (
    get_ermittlungsakte_service,
    ErmittlungsakteStatus,
    SeitenBereich
)
from src.models import UnfallProjekt, Dokument, User
from src.ui.components import badge


def render_ermittlungsakte():
    """Rendert die Ermittlungsakte-Verwaltungsseite"""

    st.markdown("## Ermittlungsakte")

    rolle = st.session_state.get("user_role", "")

    if rolle not in ["ADMIN", "ANWALT"]:
        st.warning("Diese Funktion steht nur Anwälten und Administratoren zur Verfügung.")
        return

    with get_session() as db:
        ea_service = get_ermittlungsakte_service(db)

        # Tabs
        tabs = st.tabs([
            "Übersicht",
            "Akte anfordern",
            "Akte einlesen",
            "Auswertung",
            "Weitergabe"
        ])

        with tabs[0]:
            _render_uebersicht(db, ea_service)

        with tabs[1]:
            _render_anfordern(db, ea_service)

        with tabs[2]:
            _render_einlesen(db, ea_service)

        with tabs[3]:
            _render_auswertung(db, ea_service)

        with tabs[4]:
            _render_weitergabe(db, ea_service)


def _render_uebersicht(db, ea_service):
    """Rendert die Übersicht aller Ermittlungsakten"""

    st.markdown("### Ermittlungsakten-Übersicht")

    # Filter
    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    akten = ea_service.get_ermittlungsakten(projekt_id=aktives_projekt_id)

    if not akten:
        st.info("Keine Ermittlungsakten vorhanden.")
        return

    for akte in akten:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 2])

            with col1:
                st.markdown(f"**{akte.staatsanwaltschaft}**")
                st.markdown(f"Az.: {akte.aktenzeichen_sta}")

            with col2:
                if akte.projekt:
                    st.markdown(f"Projekt: {akte.projekt.aktenzeichen or akte.projekt.projektnummer}")

            with col3:
                status_farben = {
                    ErmittlungsakteStatus.ANGEFORDERT: "warning",
                    ErmittlungsakteStatus.EINGEGANGEN: "info",
                    ErmittlungsakteStatus.IN_BEARBEITUNG: "info",
                    ErmittlungsakteStatus.AUSGEWERTET: "success",
                    ErmittlungsakteStatus.ARCHIVIERT: "secondary"
                }
                st.markdown(
                    badge(akte.status.value.upper(), status_farben.get(akte.status, "secondary")),
                    unsafe_allow_html=True
                )

            with col4:
                if akte.eingegangen_am:
                    st.markdown(f"Eingegangen: {akte.eingegangen_am.strftime('%d.%m.%Y')}")
                elif akte.angefordert_am:
                    st.markdown(f"Angefordert: {akte.angefordert_am.strftime('%d.%m.%Y')}")

                if akte.seitenanzahl:
                    st.caption(f"{akte.seitenanzahl} Seiten")

            # Details
            with st.expander("Details & Zusammenfassung"):
                if akte.zusammenfassung:
                    st.markdown("**Zusammenfassung:**")
                    st.markdown(akte.zusammenfassung)

                if akte.unfallhergang_extrakt:
                    st.markdown("**Unfallhergang:**")
                    st.markdown(akte.unfallhergang_extrakt)

                if akte.verursacher_info:
                    st.markdown("**Verursacher:**")
                    st.markdown(akte.verursacher_info)

                # Weitergaben
                weitergaben = ea_service.get_weitergaben(akte.id)
                if weitergaben:
                    st.markdown(f"**Weitergaben:** {len(weitergaben)}")

                # Zur Bearbeitung auswählen
                if st.button("Bearbeiten", key=f"edit_akte_{akte.id}"):
                    st.session_state["aktive_ermittlungsakte_id"] = akte.id
                    st.rerun()

            st.markdown("---")


def _render_anfordern(db, ea_service):
    """Rendert das Formular zum Anfordern einer Ermittlungsakte"""

    st.markdown("### Ermittlungsakte anfordern")

    # Projekt auswählen
    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.aktenzeichen).all()
        if not projekte:
            st.warning("Keine Projekte vorhanden.")
            return

        projekt_optionen = {
            f"{p.aktenzeichen or p.projektnummer}": p.id for p in projekte
        }
        ausgewaehltes = st.selectbox("Projekt auswählen", list(projekt_optionen.keys()), key="anf_projekt")
        projekt_id = projekt_optionen[ausgewaehltes]
    else:
        projekt_id = aktives_projekt_id
        projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == projekt_id).first()
        st.info(f"Aktives Projekt: {projekt.aktenzeichen or projekt.projektnummer}")

    st.markdown("---")

    # Staatsanwaltschaft-Daten
    st.markdown("#### Staatsanwaltschaft")

    col1, col2 = st.columns(2)

    with col1:
        staatsanwaltschaft = st.text_input(
            "Name der Staatsanwaltschaft",
            placeholder="z.B. Staatsanwaltschaft Berlin"
        )

    with col2:
        aktenzeichen_sta = st.text_input(
            "Aktenzeichen bei der StA",
            placeholder="z.B. 123 Js 456/24"
        )

    sachbearbeiter = st.text_input(
        "Sachbearbeiter (optional)",
        placeholder="z.B. StA Müller"
    )

    st.markdown("---")

    # Anforderung erstellen
    if st.button("Anforderung erstellen", type="primary"):
        if not staatsanwaltschaft or not aktenzeichen_sta:
            st.error("Bitte füllen Sie alle Pflichtfelder aus.")
            return

        user_id = st.session_state.get("user_id")

        erfolg, nachricht, akte = ea_service.anforderung_erstellen(
            projekt_id=projekt_id,
            user_id=user_id,
            staatsanwaltschaft=staatsanwaltschaft,
            aktenzeichen_sta=aktenzeichen_sta,
            sachbearbeiter_sta=sachbearbeiter
        )

        if erfolg:
            st.success(nachricht)

            # Anforderungsschreiben generieren
            st.markdown("---")
            st.markdown("#### Anforderungsschreiben")

            schreiben = ea_service.generiere_anforderungsschreiben(akte)
            st.text_area("Vorlage", value=schreiben, height=400)

            st.download_button(
                "Schreiben herunterladen",
                data=schreiben,
                file_name=f"anforderung_ermittlungsakte_{aktenzeichen_sta.replace('/', '_')}.txt",
                mime="text/plain"
            )
        else:
            st.error(nachricht)


def _render_einlesen(db, ea_service):
    """Rendert das Formular zum Einlesen einer Ermittlungsakte"""

    st.markdown("### Ermittlungsakte einlesen")

    # Offene Anforderungen anzeigen
    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    akten = ea_service.get_ermittlungsakten(projekt_id=aktives_projekt_id)
    offene_akten = [a for a in akten if a.status == ErmittlungsakteStatus.ANGEFORDERT]

    if not offene_akten:
        st.info("Keine offenen Anforderungen vorhanden.")
        return

    # Akte auswählen
    akte_optionen = {
        f"{a.staatsanwaltschaft} - {a.aktenzeichen_sta}": a.id for a in offene_akten
    }

    ausgewaehlte = st.selectbox("Ermittlungsakte auswählen", list(akte_optionen.keys()))
    akte_id = akte_optionen[ausgewaehlte]
    akte = next(a for a in offene_akten if a.id == akte_id)

    st.markdown("---")

    # Datei hochladen
    st.markdown("#### Ermittlungsakte hochladen")

    uploaded_file = st.file_uploader(
        "PDF-Datei auswählen",
        type=["pdf"],
        help="Laden Sie die Ermittlungsakte als PDF hoch"
    )

    seitenanzahl = st.number_input("Seitenanzahl", min_value=1, value=1)

    if uploaded_file and st.button("Akte importieren", type="primary"):
        # Datei speichern
        from src.config.settings import get_settings
        import os

        settings = get_settings()
        upload_dir = os.path.join(settings.upload_folder, str(akte.unfallprojekt_id))
        os.makedirs(upload_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dateiname = f"ermittlungsakte_{akte.aktenzeichen_sta.replace('/', '_')}_{timestamp}.pdf"
        dateipfad = os.path.join(upload_dir, dateiname)

        with open(dateipfad, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Dokument erstellen
        from src.models import DokumentTyp

        dokument = Dokument(
            unfallprojekt_id=akte.unfallprojekt_id,
            hochgeladen_von_user_id=st.session_state.get("user_id"),
            dokument_typ=DokumentTyp.SONSTIG,
            original_dateiname=uploaded_file.name,
            dateipfad=dateipfad,
            mime_typ="application/pdf",
            dateigroesse=uploaded_file.size,
            beschreibung=f"Ermittlungsakte {akte.staatsanwaltschaft} - {akte.aktenzeichen_sta}",
            status="HOCHGELADEN"
        )

        db.add(dokument)
        db.flush()

        # Akte aktualisieren
        erfolg, nachricht = ea_service.akte_importieren(
            ermittlungsakte_id=akte_id,
            dokument_id=dokument.id,
            seitenanzahl=seitenanzahl
        )

        if erfolg:
            st.success(nachricht)
            st.rerun()
        else:
            st.error(nachricht)


def _render_auswertung(db, ea_service):
    """Rendert die Auswertungsseite"""

    st.markdown("### Ermittlungsakte auswerten")

    # Eingelesene Akten anzeigen
    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    akten = ea_service.get_ermittlungsakten(projekt_id=aktives_projekt_id)
    auswertbare_akten = [a for a in akten if a.status in [
        ErmittlungsakteStatus.EINGEGANGEN,
        ErmittlungsakteStatus.IN_BEARBEITUNG,
        ErmittlungsakteStatus.AUSGEWERTET
    ]]

    if not auswertbare_akten:
        st.info("Keine auswertbaren Akten vorhanden. Bitte importieren Sie zuerst eine Akte.")
        return

    # Akte auswählen
    akte_optionen = {
        f"{a.staatsanwaltschaft} - {a.aktenzeichen_sta} ({a.status.value})": a.id for a in auswertbare_akten
    }

    ausgewaehlte = st.selectbox("Ermittlungsakte auswählen", list(akte_optionen.keys()), key="ausw_akte")
    akte_id = akte_optionen[ausgewaehlte]
    akte = next(a for a in auswertbare_akten if a.id == akte_id)

    st.markdown("---")

    # KI-Zusammenfassung
    st.markdown("#### Automatische Analyse")

    if st.button("KI-Zusammenfassung erstellen"):
        erfolg, nachricht, zusammenfassung = ea_service.ki_zusammenfassung_erstellen(akte_id)

        if erfolg:
            st.success(nachricht)
            st.session_state["ki_zusammenfassung"] = zusammenfassung
        else:
            st.error(nachricht)

    st.markdown("---")

    # Manuelle Auswertung
    st.markdown("#### Manuelle Auswertung")

    col1, col2 = st.columns(2)

    with col1:
        zusammenfassung = st.text_area(
            "Allgemeine Zusammenfassung",
            value=akte.zusammenfassung or st.session_state.get("ki_zusammenfassung", {}).get("unfallhergang", ""),
            height=150
        )

        unfallhergang = st.text_area(
            "Unfallhergang",
            value=akte.unfallhergang_extrakt or "",
            height=150,
            help="Beschreiben Sie den Unfallhergang basierend auf der Ermittlungsakte"
        )

    with col2:
        verursacher = st.text_area(
            "Verursacher-Informationen",
            value=akte.verursacher_info or "",
            height=150,
            help="Informationen zum Unfallverursacher"
        )

        zeugenaussagen = st.text_area(
            "Zeugenaussagen (Zusammenfassung)",
            value=akte.zeugenaussagen or "",
            height=150
        )

    polizeibericht = st.text_area(
        "Polizeibericht (Extrakt)",
        value=akte.polizeibericht_extrakt or "",
        height=100
    )

    # Wichtige Seitenbereiche
    st.markdown("#### Wichtige Seitenbereiche")

    bereiche = []
    bestehende_bereiche = json.loads(akte.wichtige_blattzahlen) if akte.wichtige_blattzahlen else []

    for i, bereich in enumerate(bestehende_bereiche):
        col1, col2, col3, col4 = st.columns([1, 1, 2, 2])
        with col1:
            von = st.number_input("Von", value=bereich.get("von", 1), min_value=1, key=f"von_{i}")
        with col2:
            bis = st.number_input("Bis", value=bereich.get("bis", 1), min_value=1, key=f"bis_{i}")
        with col3:
            bez = st.text_input("Bezeichnung", value=bereich.get("bezeichnung", ""), key=f"bez_{i}")
        with col4:
            besch = st.text_input("Beschreibung", value=bereich.get("beschreibung", ""), key=f"besch_{i}")

        bereiche.append(SeitenBereich(von=von, bis=bis, bezeichnung=bez, beschreibung=besch))

    # Neuen Bereich hinzufügen
    if st.button("Seitenbereich hinzufügen"):
        bestehende_bereiche.append({"von": 1, "bis": 1, "bezeichnung": "", "beschreibung": ""})
        akte.wichtige_blattzahlen = json.dumps(bestehende_bereiche)
        db.flush()
        st.rerun()

    st.markdown("---")

    # Speichern
    if st.button("Auswertung speichern", type="primary"):
        erfolg, nachricht = ea_service.akte_auswerten(
            ermittlungsakte_id=akte_id,
            zusammenfassung=zusammenfassung,
            unfallhergang_extrakt=unfallhergang,
            verursacher_info=verursacher,
            zeugenaussagen=zeugenaussagen,
            polizeibericht_extrakt=polizeibericht,
            wichtige_bereiche=bereiche if bereiche else None
        )

        if erfolg:
            st.success(nachricht)
        else:
            st.error(nachricht)


def _render_weitergabe(db, ea_service):
    """Rendert die Weitergabe-Seite"""

    st.markdown("### Ermittlungsakte weitergeben")

    st.info("""
    Hier können Sie die Ermittlungsakte (ganz oder teilweise) an Beteiligte übermitteln:
    - Eigene Haftpflichtversicherung
    - Gegnerische Versicherung
    - Unfallgegner/deren Anwalt
    """)

    # Ausgewertete Akten anzeigen
    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    akten = ea_service.get_ermittlungsakten(projekt_id=aktives_projekt_id)
    weitergabe_akten = [a for a in akten if a.status == ErmittlungsakteStatus.AUSGEWERTET and a.dokument_id]

    if not weitergabe_akten:
        st.warning("Keine ausgewerteten Akten mit Dokument vorhanden.")
        return

    # Akte auswählen
    akte_optionen = {
        f"{a.staatsanwaltschaft} - {a.aktenzeichen_sta}": a.id for a in weitergabe_akten
    }

    ausgewaehlte = st.selectbox("Ermittlungsakte auswählen", list(akte_optionen.keys()), key="wg_akte")
    akte_id = akte_optionen[ausgewaehlte]
    akte = next(a for a in weitergabe_akten if a.id == akte_id)

    st.markdown("---")

    # Empfänger
    st.markdown("#### Empfänger")

    col1, col2 = st.columns(2)

    with col1:
        empfaenger_typ = st.selectbox(
            "Empfänger-Typ",
            [
                "VERSICHERUNG_EIGEN",
                "VERSICHERUNG_GEGNER",
                "ANWALT_GEGNER",
                "UNFALLGEGNER",
                "SONSTIG"
            ],
            format_func=lambda x: {
                "VERSICHERUNG_EIGEN": "Eigene Haftpflichtversicherung",
                "VERSICHERUNG_GEGNER": "Gegnerische Versicherung",
                "ANWALT_GEGNER": "Anwalt des Unfallgegners",
                "UNFALLGEGNER": "Unfallgegner direkt",
                "SONSTIG": "Sonstige"
            }.get(x, x)
        )

    with col2:
        empfaenger_name = st.text_input("Name des Empfängers")

    empfaenger_email = st.text_input("E-Mail des Empfängers (optional)")

    st.markdown("---")

    # Umfang der Weitergabe
    st.markdown("#### Umfang der Weitergabe")

    umfang = st.radio(
        "Was soll weitergegeben werden?",
        ["Gesamte Akte", "Ausgewählte Seiten", "Nur zusammenfassender Text"],
        horizontal=True
    )

    komplett = umfang == "Gesamte Akte"
    blattzahlen_von = None
    blattzahlen_bis = None
    ausgewaehlte_bereiche = None

    if umfang == "Ausgewählte Seiten":
        col1, col2 = st.columns(2)
        with col1:
            blattzahlen_von = st.number_input("Von Seite", min_value=1, value=1)
        with col2:
            blattzahlen_bis = st.number_input("Bis Seite", min_value=1, value=akte.seitenanzahl or 10)

        # Wichtige Bereiche anzeigen
        if akte.wichtige_blattzahlen:
            st.markdown("**Dokumentierte wichtige Bereiche:**")
            bereiche = json.loads(akte.wichtige_blattzahlen)
            for b in bereiche:
                st.caption(f"Seiten {b['von']}-{b['bis']}: {b['bezeichnung']}")

    st.markdown("---")

    # Verwendungstext
    st.markdown("#### Begleittext")

    verwendungszweck = st.selectbox(
        "Verwendungszweck",
        ["versicherung", "gegner", "sonstig"],
        format_func=lambda x: {
            "versicherung": "Gegenüber Versicherung",
            "gegner": "Gegenüber Unfallgegner",
            "sonstig": "Sonstiger Zweck"
        }.get(x, x)
    )

    # Vorgeschlagenen Text anzeigen
    if akte.unfallhergang_extrakt:
        vorgeschlagener_text = ea_service.generiere_verwendungstext(akte, verwendungszweck)
        anschreiben = st.text_area(
            "Anschreiben",
            value=vorgeschlagener_text,
            height=300
        )
    else:
        anschreiben = st.text_area(
            "Anschreiben",
            placeholder="Fügen Sie hier Ihr Anschreiben ein...",
            height=300
        )

    st.markdown("---")

    # Weitergabe durchführen
    if st.button("Weitergabe protokollieren und durchführen", type="primary"):
        if not empfaenger_name:
            st.error("Bitte geben Sie einen Empfänger an.")
            return

        user_id = st.session_state.get("user_id")

        erfolg, nachricht, weitergabe = ea_service.weitergabe_erstellen(
            ermittlungsakte_id=akte_id,
            user_id=user_id,
            empfaenger_typ=empfaenger_typ,
            empfaenger_name=empfaenger_name,
            empfaenger_email=empfaenger_email,
            komplett=komplett,
            blattzahlen_von=blattzahlen_von,
            blattzahlen_bis=blattzahlen_bis,
            anschreiben=anschreiben,
            verwendungszweck=verwendungszweck
        )

        if erfolg:
            st.success(nachricht)

            # Downloads anbieten
            st.markdown("#### Downloads")

            col1, col2 = st.columns(2)

            with col1:
                st.download_button(
                    "Anschreiben herunterladen",
                    data=anschreiben,
                    file_name=f"anschreiben_{empfaenger_name}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )

            with col2:
                if akte.dokument and komplett:
                    st.info("Die vollständige Akte kann über die Dokumentenverwaltung heruntergeladen werden.")
        else:
            st.error(nachricht)

    # Bisherige Weitergaben
    st.markdown("---")
    st.markdown("#### Bisherige Weitergaben")

    weitergaben = ea_service.get_weitergaben(akte_id)

    if weitergaben:
        for wg in weitergaben:
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"**{wg.empfaenger_name}**")
                st.caption(wg.empfaenger_typ)

            with col2:
                if wg.komplett:
                    st.markdown("Gesamte Akte")
                elif wg.blattzahlen_von and wg.blattzahlen_bis:
                    st.markdown(f"Seiten {wg.blattzahlen_von}-{wg.blattzahlen_bis}")

            with col3:
                st.caption(wg.erstellt_am.strftime('%d.%m.%Y') if wg.erstellt_am else "")

            st.markdown("---")
    else:
        st.info("Noch keine Weitergaben für diese Akte.")
