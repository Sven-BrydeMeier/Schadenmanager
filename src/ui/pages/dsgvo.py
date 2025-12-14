"""
DSGVO-Management - Datenauskunft, Löschung und Protokollierung
"""
import streamlit as st
import json
from datetime import datetime

from src.config.database import get_session
from src.services.dsgvo import get_dsgvo_service, DSGVOAktionTyp
from src.models import UnfallProjekt, User, Dokument
from src.ui.components import badge


def render_dsgvo():
    """Rendert die DSGVO-Verwaltungsseite"""

    st.markdown("## DSGVO-Datenmanagement")

    rolle = st.session_state.get("user_role", "")

    if rolle not in ["ADMIN", "ANWALT", "WERKSTATT"]:
        st.warning("Diese Funktion steht nur Administratoren, Anwälten und Werkstätten zur Verfügung.")
        return

    with get_session() as db:
        dsgvo_service = get_dsgvo_service(db)

        # Tabs
        tabs = st.tabs([
            "Datenauskunft (Art. 15)",
            "Datenlöschung (Art. 17)",
            "Protokolle"
        ])

        with tabs[0]:
            _render_datenauskunft(db, dsgvo_service)

        with tabs[1]:
            _render_datenloeschung(db, dsgvo_service)

        with tabs[2]:
            _render_protokolle(db, dsgvo_service)


def _render_datenauskunft(db, dsgvo_service):
    """Rendert den Datenauskunft-Tab"""

    st.markdown("### Datenauskunft gemäß Art. 15 DSGVO")

    st.info("""
    **Voraussetzung:** Ein schriftliches Auskunftsersuchen des Betroffenen muss
    in der Akte hinterlegt sein, bevor die Datenauskunft erstellt werden kann.
    """)

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
        ausgewaehltes = st.selectbox("Projekt auswählen", list(projekt_optionen.keys()))
        projekt_id = projekt_optionen[ausgewaehltes]
    else:
        projekt_id = aktives_projekt_id
        projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == projekt_id).first()
        st.info(f"Aktives Projekt: {projekt.aktenzeichen or projekt.projektnummer}")

    projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == projekt_id).first()

    st.markdown("---")

    # Anforderungsdokument prüfen
    hat_anforderung, dok, msg = dsgvo_service.pruefe_anforderungsdokument(projekt_id)

    if hat_anforderung:
        st.success(f"DSGVO-Anforderung gefunden: {dok.original_dateiname}")
        anforderungs_dok_id = dok.id
    else:
        st.error(msg)
        st.markdown("""
        **So laden Sie ein Anforderungsschreiben hoch:**
        1. Gehen Sie zur Dokumenten-Seite
        2. Laden Sie das Schreiben des Betroffenen hoch
        3. Benennen Sie es mit "DSGVO" im Dateinamen oder in der Beschreibung
        """)
        return

    # Betroffene Person auswählen
    st.markdown("#### Betroffene Person")

    # Projektbeteiligte als Optionen
    beteiligte = []
    if projekt.unfallopfer:
        beteiligte.append((f"Unfallopfer: {projekt.unfallopfer.vorname} {projekt.unfallopfer.nachname}", projekt.unfallopfer.id))
    if projekt.werkstatt:
        beteiligte.append((f"Werkstatt: {projekt.werkstatt.vorname} {projekt.werkstatt.nachname}", projekt.werkstatt.id))
    if projekt.gutachter:
        beteiligte.append((f"Gutachter: {projekt.gutachter.vorname} {projekt.gutachter.nachname}", projekt.gutachter.id))

    if not beteiligte:
        st.warning("Keine Projektbeteiligten gefunden.")
        return

    beteiligte_optionen = {name: uid for name, uid in beteiligte}
    ausgewaehlter = st.selectbox("Betroffene Person", list(beteiligte_optionen.keys()))
    betroffene_person_id = beteiligte_optionen[ausgewaehlter]

    st.markdown("---")

    # Vorschau der Daten
    st.markdown("#### Vorschau der personenbezogenen Daten")

    personendaten = dsgvo_service.sammle_personendaten(projekt_id, betroffene_person_id)

    if personendaten:
        for pd in personendaten:
            with st.expander(f"{pd.kategorie} ({pd.quelle})"):
                for key, value in pd.daten.items():
                    if value:
                        st.markdown(f"**{key}:** {value}")

                if not pd.loeschbar:
                    st.warning(f"Nicht löschbar: {pd.loeschausnahme_grund}")
    else:
        st.info("Keine personenbezogenen Daten gefunden.")

    st.markdown("---")

    # Auskunft erstellen
    if st.button("Datenauskunft erstellen", type="primary"):
        user_id = st.session_state.get("user_id")

        erfolg, nachricht, daten = dsgvo_service.erstelle_datenauskunft(
            projekt_id=projekt_id,
            betroffene_person_id=betroffene_person_id,
            durchgefuehrt_von_user_id=user_id,
            anforderungs_dokument_id=anforderungs_dok_id
        )

        if erfolg:
            st.success(nachricht)

            # Download anbieten
            json_str = json.dumps(daten, ensure_ascii=False, indent=2, default=str)
            st.download_button(
                "Datenauskunft herunterladen (JSON)",
                data=json_str,
                file_name=f"dsgvo_auskunft_{projekt.aktenzeichen or projekt_id}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        else:
            st.error(nachricht)


def _render_datenloeschung(db, dsgvo_service):
    """Rendert den Datenlöschung-Tab"""

    st.markdown("### Datenlöschung gemäß Art. 17 DSGVO")

    st.warning("""
    **Achtung:** Die Datenlöschung ist unwiderruflich. Bestimmte Daten können aufgrund
    gesetzlicher Aufbewahrungspflichten nicht gelöscht werden.
    """)

    st.info("""
    **Voraussetzung:** Ein schriftliches Löschungsersuchen des Betroffenen muss
    in der Akte hinterlegt sein.
    """)

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
        ausgewaehltes = st.selectbox("Projekt auswählen", list(projekt_optionen.keys()), key="del_projekt")
        projekt_id = projekt_optionen[ausgewaehltes]
    else:
        projekt_id = aktives_projekt_id

    projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == projekt_id).first()

    st.markdown("---")

    # Anforderungsdokument prüfen
    hat_anforderung, dok, msg = dsgvo_service.pruefe_anforderungsdokument(projekt_id)

    if hat_anforderung:
        st.success(f"DSGVO-Anforderung gefunden: {dok.original_dateiname}")
        anforderungs_dok_id = dok.id
    else:
        st.error(msg)
        return

    # Betroffene Person auswählen
    st.markdown("#### Betroffene Person")

    beteiligte = []
    if projekt.unfallopfer:
        beteiligte.append((f"Unfallopfer: {projekt.unfallopfer.vorname} {projekt.unfallopfer.nachname}", projekt.unfallopfer.id))

    if not beteiligte:
        st.warning("Keine betroffenen Personen gefunden.")
        return

    beteiligte_optionen = {name: uid for name, uid in beteiligte}
    ausgewaehlter = st.selectbox("Betroffene Person", list(beteiligte_optionen.keys()), key="del_person")
    betroffene_person_id = beteiligte_optionen[ausgewaehlter]

    st.markdown("---")

    # Vorschau der zu löschenden/beizubehaltenden Daten
    st.markdown("#### Löschungsübersicht")

    personendaten = dsgvo_service.sammle_personendaten(projekt_id, betroffene_person_id)

    loeschbar = [pd for pd in personendaten if pd.loeschbar]
    nicht_loeschbar = [pd for pd in personendaten if not pd.loeschbar]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Wird gelöscht:**")
        for pd in loeschbar:
            st.markdown(f"- {pd.kategorie}")

    with col2:
        st.markdown("**Kann nicht gelöscht werden:**")
        for pd in nicht_loeschbar:
            with st.expander(pd.kategorie):
                st.markdown(f"**Grund:** {pd.loeschausnahme_grund}")

    st.markdown("---")

    # Begründung
    begruendung = st.text_area(
        "Begründung/Anmerkungen",
        placeholder="Optional: Zusätzliche Anmerkungen zur Löschung..."
    )

    # Bestätigung
    st.markdown("---")
    st.error("Diese Aktion kann nicht rückgängig gemacht werden!")

    bestaetigung = st.checkbox(
        "Ich bestätige, dass ich die Löschung im Auftrag des Betroffenen durchführe und das Anforderungsschreiben vorliegt."
    )

    if st.button("Löschung durchführen", type="primary", disabled=not bestaetigung):
        user_id = st.session_state.get("user_id")

        erfolg, nachricht, protokoll = dsgvo_service.fuehre_loeschung_durch(
            projekt_id=projekt_id,
            betroffene_person_id=betroffene_person_id,
            durchgefuehrt_von_user_id=user_id,
            anforderungs_dokument_id=anforderungs_dok_id,
            begruendung=begruendung
        )

        if erfolg:
            st.success(nachricht)

            # Löschprotokoll anzeigen
            if protokoll:
                st.markdown("#### Löschprotokoll")

                protokoll_text = dsgvo_service.exportiere_loeschprotokoll_pdf(protokoll)
                st.download_button(
                    "Löschprotokoll herunterladen",
                    data=protokoll_text,
                    file_name=f"loeschprotokoll_{projekt.aktenzeichen or projekt_id}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
        else:
            st.error(nachricht)


def _render_protokolle(db, dsgvo_service):
    """Rendert den Protokolle-Tab"""

    st.markdown("### DSGVO-Protokolle")

    # Filter
    col1, col2 = st.columns(2)

    with col1:
        aktionstyp_filter = st.selectbox(
            "Aktionstyp",
            ["Alle", "Auskunft", "Löschung"],
            key="proto_filter"
        )

    # Protokolle laden
    protokolle = dsgvo_service.get_protokolle()

    if aktionstyp_filter == "Auskunft":
        protokolle = [p for p in protokolle if p.aktion_typ == DSGVOAktionTyp.AUSKUNFT]
    elif aktionstyp_filter == "Löschung":
        protokolle = [p for p in protokolle if p.aktion_typ == DSGVOAktionTyp.LOESCHUNG]

    if not protokolle:
        st.info("Keine DSGVO-Protokolle vorhanden.")
        return

    for proto in protokolle:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 2])

            with col1:
                aktion_badge = badge(
                    proto.aktion_typ.value.upper(),
                    "info" if proto.aktion_typ == DSGVOAktionTyp.AUSKUNFT else "warning"
                )
                st.markdown(aktion_badge, unsafe_allow_html=True)

                if proto.projekt:
                    st.markdown(f"**Projekt:** {proto.projekt.aktenzeichen or proto.projekt.projektnummer}")

            with col2:
                if proto.betroffene_person:
                    st.markdown(f"**Betroffene Person:** {proto.betroffene_person.vorname} {proto.betroffene_person.nachname}")

            with col3:
                st.markdown(badge(proto.status, "success" if proto.status == "DURCHGEFUEHRT" else "secondary"), unsafe_allow_html=True)

            with col4:
                if proto.durchgefuehrt_am:
                    st.markdown(f"**Datum:** {proto.durchgefuehrt_am.strftime('%d.%m.%Y %H:%M')}")

                if proto.durchgefuehrt_von:
                    st.caption(f"Von: {proto.durchgefuehrt_von.vorname} {proto.durchgefuehrt_von.nachname}")

            # Details
            with st.expander("Details"):
                if proto.begruendung:
                    st.markdown(f"**Begründung:** {proto.begruendung}")

                if proto.abschluss_bemerkung:
                    st.markdown(f"**Bemerkung:** {proto.abschluss_bemerkung}")

                if proto.ausgenommene_daten:
                    st.markdown("**Ausgenommene Daten:**")
                    try:
                        ausgenommen = json.loads(proto.ausgenommene_daten)
                        for item in ausgenommen:
                            st.markdown(f"- {item['kategorie']}: {item['ausnahmegrund']}")
                    except:
                        st.text(proto.ausgenommene_daten)

                # Download
                protokoll_text = dsgvo_service.exportiere_loeschprotokoll_pdf(proto)
                st.download_button(
                    "Protokoll herunterladen",
                    data=protokoll_text,
                    file_name=f"dsgvo_protokoll_{proto.id}.json",
                    mime="application/json",
                    key=f"dl_proto_{proto.id}"
                )

            st.markdown("---")
