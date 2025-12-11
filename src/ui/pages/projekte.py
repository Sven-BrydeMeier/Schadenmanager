"""
Projekt-Verwaltungsseite
"""
import streamlit as st
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, Fahrzeug, User, Organisation, Rollen,
    TimelineMeilenstein, MeilensteinStatus
)
from src.services.meilenstein_engine import get_meilenstein_engine
from src.ui.components import projekt_header, timeline, badge, alert
from src.config.database import get_session


def render_projekte():
    """Rendert die Projekt-Übersicht und -Verwaltung"""

    st.markdown("## Projekte")

    rolle = st.session_state.get("user_rolle", "")
    user_id = st.session_state.get("user_id")

    # Tabs für verschiedene Ansichten
    tab1, tab2 = st.tabs(["Übersicht", "Neues Projekt"])

    with tab1:
        _render_projekt_liste(user_id, rolle)

    with tab2:
        if rolle in ["WERKSTATT", "ANWALT", "GUTACHTER", "ADMIN"]:
            _render_neues_projekt_formular()
        else:
            st.info("Sie haben keine Berechtigung, neue Projekte anzulegen.")


def _render_projekt_liste(user_id: int, rolle: str):
    """Zeigt die Liste der Projekte an"""

    with get_session() as db:
        query = db.query(UnfallProjekt)

        # Rollenbasierte Filterung
        if rolle == "ANWALT":
            query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
        elif rolle == "WERKSTATT":
            query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)
        elif rolle == "GUTACHTER":
            query = query.filter(UnfallProjekt.gutachter_user_id == user_id)
        elif rolle == "UNFALLOPFER":
            query = query.filter(UnfallProjekt.unfallopfer_user_id == user_id)
        elif rolle == "VERSICHERUNG_EIGEN":
            query = query.filter(UnfallProjekt.versicherung_eigen_user_id == user_id)
        elif rolle == "VERSICHERUNG_GEGNER":
            query = query.filter(UnfallProjekt.versicherung_gegner_user_id == user_id)
        # ADMIN sieht alle

        # Filter-Optionen
        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox(
                "Status",
                ["Alle", "Offen", "In Bearbeitung", "Abgeschlossen"],
                index=0
            )

        with col2:
            such_text = st.text_input("Suche (Projektnummer, Kennzeichen)")

        with col3:
            sortierung = st.selectbox(
                "Sortierung",
                ["Neueste zuerst", "Älteste zuerst", "Projektnummer"],
                index=0
            )

        # Filter anwenden
        if status_filter != "Alle":
            status_map = {
                "Offen": "OFFEN",
                "In Bearbeitung": "IN_BEARBEITUNG",
                "Abgeschlossen": "ABGESCHLOSSEN"
            }
            query = query.filter(UnfallProjekt.status == status_map.get(status_filter))

        if such_text:
            such_pattern = f"%{such_text}%"
            query = query.filter(
                UnfallProjekt.projektnummer.ilike(such_pattern)
            )

        # Sortierung
        if sortierung == "Neueste zuerst":
            query = query.order_by(UnfallProjekt.erstellt_am.desc())
        elif sortierung == "Älteste zuerst":
            query = query.order_by(UnfallProjekt.erstellt_am.asc())
        else:
            query = query.order_by(UnfallProjekt.projektnummer)

        projekte = query.all()

        st.markdown("---")

        if not projekte:
            st.info("Keine Projekte gefunden.")
        else:
            st.caption(f"{len(projekte)} Projekte gefunden")

            for projekt in projekte:
                _render_projekt_karte(projekt, rolle)


def _render_projekt_karte(projekt: UnfallProjekt, rolle: str):
    """Rendert eine Projekt-Karte"""

    with st.container():
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

        with col1:
            st.markdown(f"### {projekt.projektnummer}")
            if projekt.kfz_eigen:
                st.caption(f"{projekt.kfz_eigen.kennzeichen} - {projekt.kfz_eigen.fahrzeug_bezeichnung}")

        with col2:
            if projekt.datum_unfall:
                st.write(f"**Unfall:** {projekt.datum_unfall.strftime('%d.%m.%Y')}")
            if projekt.ort_unfall:
                st.write(f"**Ort:** {projekt.ort_unfall}")

        with col3:
            # Status-Badge
            status_farbe = {
                "OFFEN": "warning",
                "IN_BEARBEITUNG": "info",
                "ABGESCHLOSSEN": "success",
                "STORNIERT": "danger"
            }.get(projekt.status, "secondary")
            st.markdown(badge(projekt.status_anzeige, status_farbe), unsafe_allow_html=True)

            # Meilenstein-Fortschritt
            if projekt.timeline_meilensteine:
                gruen = sum(1 for m in projekt.timeline_meilensteine if m.status == MeilensteinStatus.GRUEN)
                gesamt = len(projekt.timeline_meilensteine)
                st.caption(f"Fortschritt: {gruen}/{gesamt}")

        with col4:
            if st.button("Öffnen", key=f"open_{projekt.id}"):
                st.session_state["aktives_projekt_id"] = projekt.id
                st.session_state["page"] = "Dashboard"
                st.rerun()

        st.markdown("---")


def _render_neues_projekt_formular():
    """Formular zum Anlegen eines neuen Projekts"""

    st.markdown("### Neues Projekt anlegen")

    with st.form("neues_projekt"):
        st.markdown("#### Unfalldaten")

        col1, col2 = st.columns(2)
        with col1:
            datum_unfall = st.date_input("Unfalldatum", value=datetime.now())
            uhrzeit_unfall = st.time_input("Uhrzeit (optional)")
        with col2:
            ort_unfall = st.text_input("Unfallort")
            polizei_aktenzeichen = st.text_input("Polizei-Aktenzeichen (optional)")

        beschreibung = st.text_area("Unfallbeschreibung (optional)")

        st.markdown("---")
        st.markdown("#### Fahrzeugdaten (eigenes Fahrzeug)")

        col1, col2 = st.columns(2)
        with col1:
            kennzeichen = st.text_input("Kennzeichen*")
            hersteller = st.text_input("Hersteller")
            modell = st.text_input("Modell")
        with col2:
            halter_name = st.text_input("Name des Halters")
            fin = st.text_input("Fahrgestellnummer (FIN)")

        st.markdown("---")
        st.markdown("#### Gegnerisches Fahrzeug (optional)")

        col1, col2 = st.columns(2)
        with col1:
            kennzeichen_gegner = st.text_input("Kennzeichen Gegner")
        with col2:
            versicherung_gegner = st.text_input("Versicherung Gegner")

        st.markdown("---")
        st.markdown("#### Einstellungen")

        schuld_eigen = st.slider("Eigene Schuld (%)", 0, 100, 0)

        submitted = st.form_submit_button("Projekt anlegen", use_container_width=True)

        if submitted:
            if not kennzeichen:
                st.error("Bitte mindestens das Kennzeichen eingeben.")
            else:
                with get_session() as db:
                    # Eigenes Fahrzeug erstellen
                    fahrzeug_eigen = Fahrzeug(
                        kennzeichen=kennzeichen.upper(),
                        hersteller=hersteller,
                        modell=modell,
                        halter_name=halter_name,
                        fin=fin,
                        quelle="MANUELL"
                    )
                    db.add(fahrzeug_eigen)
                    db.flush()

                    # Gegnerisches Fahrzeug (falls vorhanden)
                    fahrzeug_gegner_id = None
                    if kennzeichen_gegner:
                        fahrzeug_gegner = Fahrzeug(
                            kennzeichen=kennzeichen_gegner.upper(),
                            versicherung_name=versicherung_gegner,
                            quelle="MANUELL"
                        )
                        db.add(fahrzeug_gegner)
                        db.flush()
                        fahrzeug_gegner_id = fahrzeug_gegner.id

                    # Projekt erstellen
                    user_id = st.session_state.get("user_id")
                    rolle = st.session_state.get("user_rolle")
                    organisation_id = st.session_state.get("user_organisation_id")

                    projekt = UnfallProjekt(
                        datum_unfall=datetime.combine(datum_unfall, uhrzeit_unfall) if uhrzeit_unfall else datetime.combine(datum_unfall, datetime.min.time()),
                        ort_unfall=ort_unfall,
                        beschreibung_unfall=beschreibung,
                        polizei_aktenzeichen=polizei_aktenzeichen,
                        schuld_eigen_prozent=schuld_eigen,
                        kfz_eigen_id=fahrzeug_eigen.id,
                        kfz_gegner_id=fahrzeug_gegner_id,
                        anlegende_organisation_id=organisation_id,
                        angelegt_von_user_id=user_id,
                        status="OFFEN",
                        einladungs_code=uuid.uuid4().hex[:12].upper()
                    )

                    # Zuweisungen basierend auf Rolle
                    if rolle == "ANWALT":
                        projekt.anwalt_user_id = user_id
                    elif rolle == "WERKSTATT":
                        projekt.werkstatt_user_id = user_id
                    elif rolle == "GUTACHTER":
                        projekt.gutachter_user_id = user_id

                    db.add(projekt)
                    db.flush()

                    # Meilensteine initialisieren
                    engine = get_meilenstein_engine()
                    engine.initialisiere_meilensteine(db, projekt)

                    st.success(f"Projekt {projekt.projektnummer} wurde erfolgreich angelegt!")

                    # Einladungslink anzeigen
                    st.info(f"Einladungscode für Unfallopfer: **{projekt.einladungs_code}**")

                    st.session_state["aktives_projekt_id"] = projekt.id
                    st.rerun()


def render_projekt_details():
    """Rendert die Detail-Ansicht eines Projekts"""

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Kein Projekt ausgewählt.")
        return

    with get_session() as db:
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == aktives_projekt_id
        ).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        # Header
        projekt_header(projekt)

        st.markdown("---")

        # Timeline
        st.markdown("### Status-Timeline")
        meilensteine = [
            {
                "code": m.code,
                "beschreibung": m.beschreibung,
                "status": m.status
            }
            for m in sorted(projekt.timeline_meilensteine, key=lambda x: x.reihenfolge)
        ]
        timeline(meilensteine)

        st.markdown("---")

        # Projekt-Bearbeitung
        tabs = st.tabs(["Details", "Beteiligte", "Einstellungen"])

        with tabs[0]:
            _render_projekt_details_tab(projekt)

        with tabs[1]:
            _render_beteiligte_tab(db, projekt)

        with tabs[2]:
            _render_einstellungen_tab(db, projekt)


def _render_projekt_details_tab(projekt: UnfallProjekt):
    """Rendert den Details-Tab"""

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Unfalldaten")
        st.write(f"**Datum:** {projekt.datum_unfall.strftime('%d.%m.%Y %H:%M') if projekt.datum_unfall else '-'}")
        st.write(f"**Ort:** {projekt.ort_unfall or '-'}")
        st.write(f"**Polizei-Az.:** {projekt.polizei_aktenzeichen or '-'}")
        st.write(f"**Schuld eigen:** {projekt.schuld_eigen_prozent}%")

        if projekt.beschreibung_unfall:
            st.markdown("**Beschreibung:**")
            st.text(projekt.beschreibung_unfall)

    with col2:
        st.markdown("#### Fahrzeugdaten")

        if projekt.kfz_eigen:
            st.markdown("**Eigenes Fahrzeug:**")
            st.write(f"Kennzeichen: {projekt.kfz_eigen.kennzeichen}")
            st.write(f"Modell: {projekt.kfz_eigen.fahrzeug_bezeichnung}")
            st.write(f"Halter: {projekt.kfz_eigen.halter_name or '-'}")

        if projekt.kfz_gegner:
            st.markdown("**Gegnerisches Fahrzeug:**")
            st.write(f"Kennzeichen: {projekt.kfz_gegner.kennzeichen}")
            if projekt.kfz_gegner.versicherung_name:
                st.write(f"Versicherung: {projekt.kfz_gegner.versicherung_name}")


def _render_beteiligte_tab(db: Session, projekt: UnfallProjekt):
    """Rendert den Beteiligte-Tab"""

    st.markdown("#### Beteiligte Parteien")

    beteiligte = [
        ("Unfallopfer", projekt.unfallopfer, projekt.unfallopfer_user_id),
        ("Rechtsanwalt", projekt.anwalt, projekt.anwalt_user_id),
        ("Werkstatt", projekt.werkstatt, projekt.werkstatt_user_id),
        ("Gutachter", projekt.gutachter, projekt.gutachter_user_id),
        ("Eigene Versicherung", projekt.versicherung_eigen, projekt.versicherung_eigen_user_id),
        ("Gegnerische Versicherung", projekt.versicherung_gegner, projekt.versicherung_gegner_user_id),
    ]

    for bezeichnung, user, user_id in beteiligte:
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.write(f"**{bezeichnung}:**")

        with col2:
            if user:
                st.write(user.voller_name)
                st.caption(user.email)
            else:
                st.caption("Nicht zugewiesen")

        with col3:
            if not user_id:
                pass  # TODO: Zuweisung-Button

    # Einladungslink
    if projekt.einladungs_code:
        st.markdown("---")
        st.markdown("#### Einladungslink für Unfallopfer")
        st.code(projekt.einladungs_code)


def _render_einstellungen_tab(db: Session, projekt: UnfallProjekt):
    """Rendert den Einstellungen-Tab"""

    rolle = st.session_state.get("user_rolle", "")

    st.markdown("#### Projekt-Status")

    neuer_status = st.selectbox(
        "Status",
        ["OFFEN", "IN_BEARBEITUNG", "ABGESCHLOSSEN", "STORNIERT"],
        index=["OFFEN", "IN_BEARBEITUNG", "ABGESCHLOSSEN", "STORNIERT"].index(projekt.status)
    )

    if st.button("Status speichern"):
        projekt.status = neuer_status
        if neuer_status == "ABGESCHLOSSEN":
            projekt.abgeschlossen = True
            projekt.abgeschlossen_am = datetime.now()
        db.flush()
        st.success("Status wurde aktualisiert.")
        st.rerun()

    if rolle == "ADMIN":
        st.markdown("---")
        st.markdown("#### Gefahrenzone")

        if st.button("Projekt löschen", type="secondary"):
            st.warning("Diese Aktion kann nicht rückgängig gemacht werden!")
            if st.button("Wirklich löschen?"):
                db.delete(projekt)
                st.session_state["aktives_projekt_id"] = None
                st.success("Projekt wurde gelöscht.")
                st.rerun()
