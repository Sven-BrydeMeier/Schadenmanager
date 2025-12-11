"""
Ersatzwagen-Modul
"""
import streamlit as st
from typing import List, Optional
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, Organisation, OrgTyp,
    ErsatzwagenAnbieter, MietfahrzeugAngebot,
    KostenPosition, KostenKategorie, KostenAmpel
)
from src.ui.components import metric_card, badge, alert
from src.config.database import get_session


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Berechnet die Entfernung zwischen zwei Koordinaten in km.
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius der Erde in km

    return c * r


def render_ersatzwagen_modul():
    """Rendert das Ersatzwagen-Modul"""

    st.markdown("## Ersatzwagen")

    rolle = st.session_state.get("user_rolle", "")
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

        # Prüfen ob bereits ein Ersatzwagen gewählt wurde
        if projekt.ersatzwagenanbieter_id:
            _render_aktueller_ersatzwagen(db, projekt)
        else:
            _render_ersatzwagen_auswahl(db, projekt)


def _render_aktueller_ersatzwagen(db: Session, projekt: UnfallProjekt):
    """Zeigt den aktuell gewählten Ersatzwagen an"""

    anbieter_org = db.query(Organisation).filter(
        Organisation.id == projekt.ersatzwagenanbieter_id
    ).first()

    st.markdown("### Aktueller Ersatzwagen")

    if anbieter_org:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Anbieter:** {anbieter_org.name}")
            st.markdown(f"**Adresse:** {anbieter_org.vollstaendige_adresse}")
            if anbieter_org.telefon:
                st.markdown(f"**Telefon:** {anbieter_org.telefon}")

        with col2:
            if projekt.ersatzwagen_von:
                st.markdown(f"**Von:** {projekt.ersatzwagen_von.strftime('%d.%m.%Y')}")
            if projekt.ersatzwagen_bis:
                st.markdown(f"**Bis:** {projekt.ersatzwagen_bis.strftime('%d.%m.%Y')}")

    # Kosten anzeigen
    ersatzwagen_kosten = [
        kp for kp in projekt.kostenpositionen
        if kp.kategorie == KostenKategorie.ERSATZWAGEN
    ]

    if ersatzwagen_kosten:
        st.markdown("---")
        st.markdown("### Kosten")

        for kp in ersatzwagen_kosten:
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(kp.beschreibung or "Ersatzwagen-Kosten")

            with col2:
                st.write(f"{kp.betrag_brutto:,.2f} €")

            with col3:
                ampel_style = {
                    KostenAmpel.ROT: "danger",
                    KostenAmpel.ORANGE: "warning",
                    KostenAmpel.GRUEN: "success"
                }.get(kp.status_ampel, "secondary")
                st.markdown(badge(kp.status_ampel.value, ampel_style), unsafe_allow_html=True)

    # Option zum Ändern
    st.markdown("---")
    if st.button("Ersatzwagen ändern"):
        projekt.ersatzwagenanbieter_id = None
        db.flush()
        st.rerun()


def _render_ersatzwagen_auswahl(db: Session, projekt: UnfallProjekt):
    """Zeigt die Ersatzwagen-Auswahl an"""

    st.markdown("### Ersatzwagen auswählen")

    # Filter
    col1, col2, col3 = st.columns(3)

    with col1:
        sortierung = st.selectbox(
            "Sortierung",
            ["Preis aufsteigend", "Preis absteigend", "Entfernung"],
            index=0
        )

    with col2:
        fahrzeugklasse = st.selectbox(
            "Fahrzeugklasse",
            ["Alle", "Kleinwagen", "Kompaktklasse", "Mittelklasse", "Oberklasse", "SUV", "Transporter"],
            index=0
        )

    with col3:
        angebot_typ = st.selectbox(
            "Angebotstyp",
            ["Alle", "Mietwagen", "Carsharing"],
            index=0
        )

    # Geschätzte Mietdauer
    col1, col2 = st.columns(2)

    with col1:
        mietdauer_tage = st.number_input("Geschätzte Mietdauer (Tage)", min_value=1, value=7)

    with col2:
        geschaetzte_km = st.number_input("Geschätzte Kilometer", min_value=0, value=500)

    st.markdown("---")

    # Anbieter laden
    anbieter = db.query(ErsatzwagenAnbieter).join(
        Organisation
    ).filter(
        ErsatzwagenAnbieter.aktiv == True,
        Organisation.aktiv == True
    ).all()

    if not anbieter:
        st.info("Keine Ersatzwagenanbieter verfügbar.")
        return

    # Angebote sammeln und filtern
    alle_angebote = []

    for a in anbieter:
        if not a.organisation:
            continue

        # Filter nach Typ
        if angebot_typ == "Mietwagen" and not a.bietet_mietwagen:
            continue
        if angebot_typ == "Carsharing" and not a.bietet_carsharing:
            continue

        for angebot in a.angebote:
            if not angebot.verfuegbar:
                continue

            # Filter nach Klasse
            if fahrzeugklasse != "Alle" and angebot.fahrzeugkategorie != fahrzeugklasse:
                continue

            # Kosten berechnen
            gesamtkosten = angebot.berechne_gesamtkosten(mietdauer_tage, geschaetzte_km)

            # Entfernung berechnen (falls Koordinaten vorhanden)
            entfernung = None
            if projekt.kfz_eigen and projekt.kfz_eigen.halter_plz:
                # Hier könnte man die Koordinaten des Halters mit dem Anbieter vergleichen
                if a.organisation.geo_lat and a.organisation.geo_lon:
                    # Beispiel: Annahme von Koordinaten basierend auf PLZ
                    # In der Praxis würde man hier einen Geocoding-Service nutzen
                    entfernung = 10.0  # Placeholder

            alle_angebote.append({
                "anbieter": a,
                "organisation": a.organisation,
                "angebot": angebot,
                "gesamtkosten": gesamtkosten,
                "entfernung": entfernung
            })

    # Sortieren
    if sortierung == "Preis aufsteigend":
        alle_angebote.sort(key=lambda x: x["gesamtkosten"])
    elif sortierung == "Preis absteigend":
        alle_angebote.sort(key=lambda x: x["gesamtkosten"], reverse=True)
    elif sortierung == "Entfernung":
        alle_angebote.sort(key=lambda x: x["entfernung"] or float('inf'))

    # Angebote anzeigen
    st.markdown(f"### {len(alle_angebote)} Angebote gefunden")

    for item in alle_angebote:
        angebot = item["angebot"]
        org = item["organisation"]

        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

            with col1:
                st.markdown(f"**{org.name}**")
                st.caption(angebot.kategorie_anzeige)

            with col2:
                st.markdown(f"**Tagespreis:** {angebot.tagespreis:,.2f} €")
                st.markdown(f"**Gesamt ({mietdauer_tage} Tage):** {item['gesamtkosten']:,.2f} €")

            with col3:
                if item["entfernung"]:
                    st.markdown(f"**{item['entfernung']:.1f} km**")
                else:
                    st.caption("Entfernung unbekannt")

            with col4:
                if st.button("Auswählen", key=f"select_{angebot.id}"):
                    _waehle_ersatzwagen(db, projekt, item, mietdauer_tage, item['gesamtkosten'])
                    st.rerun()

            st.markdown("---")


def _waehle_ersatzwagen(
    db: Session,
    projekt: UnfallProjekt,
    auswahl: dict,
    mietdauer_tage: int,
    gesamtkosten: float
):
    """Speichert die Ersatzwagen-Auswahl"""

    anbieter = auswahl["anbieter"]
    angebot = auswahl["angebot"]

    # Projekt aktualisieren
    projekt.ersatzwagenanbieter_id = anbieter.organisation_id
    projekt.ersatzwagen_von = datetime.now()

    # Kostenposition erstellen
    kostenposition = KostenPosition(
        unfallprojekt_id=projekt.id,
        kategorie=KostenKategorie.ERSATZWAGEN,
        beschreibung=f"{angebot.fahrzeugkategorie} - {anbieter.organisation.name} ({mietdauer_tage} Tage)",
        betrag_brutto=gesamtkosten,
        status_ampel=KostenAmpel.ROT,
        erstellt_von_user_id=st.session_state.get("user_id")
    )

    db.add(kostenposition)
    db.flush()


def render_ersatzwagen_verwaltung():
    """Rendert die Ersatzwagen-Verwaltung für Admins"""

    st.markdown("## Ersatzwagen-Verwaltung")

    tab1, tab2 = st.tabs(["Anbieter", "Angebote"])

    with tab1:
        _render_anbieter_verwaltung()

    with tab2:
        _render_angebote_verwaltung()


def _render_anbieter_verwaltung():
    """Verwaltung der Ersatzwagenanbieter"""

    st.markdown("### Anbieter")

    with get_session() as db:
        # Bestehende Anbieter laden
        organisationen = db.query(Organisation).filter(
            Organisation.typ == OrgTyp.ERSATZWAGENANBIETER
        ).all()

        if organisationen:
            for org in organisationen:
                with st.expander(org.name):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Adresse:** {org.vollstaendige_adresse}")
                        st.write(f"**Telefon:** {org.telefon or '-'}")
                        st.write(f"**E-Mail:** {org.email or '-'}")

                    with col2:
                        status = "Aktiv" if org.aktiv else "Inaktiv"
                        st.markdown(badge(status, "success" if org.aktiv else "danger"), unsafe_allow_html=True)
        else:
            st.info("Keine Ersatzwagenanbieter vorhanden.")

        # Neuen Anbieter hinzufügen
        st.markdown("---")
        st.markdown("### Neuen Anbieter hinzufügen")

        with st.form("new_anbieter"):
            name = st.text_input("Name")
            strasse = st.text_input("Straße")
            col1, col2 = st.columns(2)
            with col1:
                hausnummer = st.text_input("Hausnummer")
                plz = st.text_input("PLZ")
            with col2:
                ort = st.text_input("Ort")
                telefon = st.text_input("Telefon")

            col1, col2 = st.columns(2)
            with col1:
                bietet_mietwagen = st.checkbox("Bietet Mietwagen", value=True)
            with col2:
                bietet_carsharing = st.checkbox("Bietet Carsharing")

            if st.form_submit_button("Anbieter hinzufügen"):
                if name:
                    # Organisation erstellen
                    neue_org = Organisation(
                        name=name,
                        typ=OrgTyp.ERSATZWAGENANBIETER,
                        strasse=strasse,
                        hausnummer=hausnummer,
                        plz=plz,
                        ort=ort,
                        telefon=telefon,
                        aktiv=True
                    )
                    db.add(neue_org)
                    db.flush()

                    # Ersatzwagenanbieter erstellen
                    neuer_anbieter = ErsatzwagenAnbieter(
                        organisation_id=neue_org.id,
                        bietet_mietwagen=bietet_mietwagen,
                        bietet_carsharing=bietet_carsharing,
                        aktiv=True
                    )
                    db.add(neuer_anbieter)

                    st.success(f"Anbieter '{name}' wurde hinzugefügt.")
                    st.rerun()
                else:
                    st.error("Bitte einen Namen eingeben.")


def _render_angebote_verwaltung():
    """Verwaltung der Mietfahrzeugangebote"""

    st.markdown("### Angebote")

    with get_session() as db:
        # Anbieter laden
        anbieter = db.query(ErsatzwagenAnbieter).join(Organisation).all()

        if not anbieter:
            st.info("Zuerst Anbieter anlegen.")
            return

        # Anbieter auswählen
        anbieter_optionen = {a.organisation.name: a for a in anbieter if a.organisation}
        ausgewaehlter_anbieter_name = st.selectbox("Anbieter", list(anbieter_optionen.keys()))

        if ausgewaehlter_anbieter_name:
            anbieter_obj = anbieter_optionen[ausgewaehlter_anbieter_name]

            # Bestehende Angebote anzeigen
            if anbieter_obj.angebote:
                for angebot in anbieter_obj.angebote:
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                    with col1:
                        st.write(angebot.kategorie_anzeige)

                    with col2:
                        st.write(f"{angebot.tagespreis:,.2f} €/Tag")

                    with col3:
                        status = "Verfügbar" if angebot.verfuegbar else "Nicht verfügbar"
                        st.markdown(badge(status, "success" if angebot.verfuegbar else "danger"), unsafe_allow_html=True)

                    with col4:
                        pass  # Bearbeiten/Löschen Buttons

            # Neues Angebot
            st.markdown("---")
            st.markdown("### Neues Angebot hinzufügen")

            with st.form("new_angebot"):
                fahrzeugkategorie = st.selectbox(
                    "Fahrzeugkategorie",
                    ["Kleinwagen", "Kompaktklasse", "Mittelklasse", "Oberklasse", "SUV", "Transporter"]
                )
                beispiel_modell = st.text_input("Beispiel-Modell (z.B. 'VW Golf oder ähnlich')")

                col1, col2, col3 = st.columns(3)
                with col1:
                    tagespreis = st.number_input("Tagespreis (€)", min_value=0.0, value=50.0, step=5.0)
                with col2:
                    wochenpreis = st.number_input("Wochenpreis (€)", min_value=0.0, value=280.0, step=10.0)
                with col3:
                    freikilometer = st.number_input("Freikilometer/Tag", min_value=0, value=200, step=50)

                if st.form_submit_button("Angebot hinzufügen"):
                    neues_angebot = MietfahrzeugAngebot(
                        ersatzwagenanbieter_id=anbieter_obj.id,
                        fahrzeugkategorie=fahrzeugkategorie,
                        beispiel_modell=beispiel_modell,
                        tagespreis=tagespreis,
                        wochenpreis=wochenpreis,
                        freikilometer_pro_tag=freikilometer,
                        verfuegbar=True
                    )
                    db.add(neues_angebot)

                    st.success("Angebot wurde hinzugefügt.")
                    st.rerun()
