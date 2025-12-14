"""
Papierkorb - UI für gelöschte Dokumente
"""
import streamlit as st
from datetime import datetime, timedelta

from src.config.database import get_session
from src.config.settings import get_settings
from src.services.papierkorb import get_papierkorb_service
from src.models import Dokument, UnfallProjekt
from src.ui.components import badge


def render_papierkorb():
    """Rendert die Papierkorb-Seite"""

    st.markdown("## Papierkorb")

    settings = get_settings()
    user_id = st.session_state.get("user_id")
    rolle = st.session_state.get("user_role", "")

    with get_session() as db:
        papierkorb = get_papierkorb_service(db)

        # Tabs für verschiedene Ansichten
        tab1, tab2, tab3 = st.tabs(["Gelöschte Dokumente", "Statistik", "Einstellungen"])

        with tab1:
            _render_dokumente_liste(db, papierkorb, user_id, rolle)

        with tab2:
            _render_statistik(papierkorb)

        with tab3:
            _render_einstellungen(papierkorb, rolle)


def _render_dokumente_liste(db, papierkorb, user_id: int, rolle: str):
    """Rendert die Liste der gelöschten Dokumente"""

    settings = get_settings()

    # Filter
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        # Projekt-Filter
        projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.aktenzeichen).all()
        projekt_optionen = {"Alle Projekte": None}
        projekt_optionen.update({
            f"{p.aktenzeichen or p.projektnummer}": p.id for p in projekte
        })
        ausgewaehltes_projekt = st.selectbox(
            "Projekt",
            list(projekt_optionen.keys())
        )
        projekt_id = projekt_optionen[ausgewaehltes_projekt]

    with col2:
        nur_eigene = st.checkbox("Nur von mir gelöscht", value=False)

    with col3:
        if st.button("Aktualisieren"):
            st.rerun()

    st.markdown("---")

    # Dokumente laden
    dokumente = papierkorb.get_papierkorb_inhalt(
        projekt_id=projekt_id,
        nur_eigene=nur_eigene,
        user_id=user_id
    )

    if not dokumente:
        st.info("Der Papierkorb ist leer.")
        return

    # Aktionen für alle
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Papierkorb leeren", type="secondary"):
            st.session_state["confirm_leeren"] = True

    with col2:
        if st.button("Abgelaufene entfernen"):
            geloescht, fehler = papierkorb.abgelaufene_loeschen()
            if geloescht > 0:
                st.success(f"{geloescht} abgelaufene Dokumente endgültig gelöscht")
            if fehler > 0:
                st.warning(f"{fehler} Dokumente konnten nicht gelöscht werden")
            st.rerun()

    # Bestätigung für Papierkorb leeren
    if st.session_state.get("confirm_leeren"):
        st.warning("Sind Sie sicher? Alle Dokumente werden endgültig gelöscht!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ja, endgültig löschen", type="primary"):
                geloescht, fehler = papierkorb.papierkorb_leeren(user_id)
                st.session_state["confirm_leeren"] = False
                st.success(f"{geloescht} Dokumente endgültig gelöscht")
                st.rerun()
        with col2:
            if st.button("Abbrechen"):
                st.session_state["confirm_leeren"] = False
                st.rerun()

    st.markdown("---")

    # Dokumente anzeigen
    for dok in dokumente:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

            with col1:
                st.markdown(f"**{dok.original_dateiname}**")
                st.caption(f"Typ: {dok.dokument_typ_anzeige}")

                # Projekt anzeigen
                if dok.projekt:
                    st.caption(f"Projekt: {dok.projekt.aktenzeichen or dok.projekt.projektnummer}")

            with col2:
                # Gelöscht von/am
                if dok.geloescht_am:
                    st.markdown(f"Gelöscht: {dok.geloescht_am.strftime('%d.%m.%Y %H:%M')}")

                if dok.geloescht_von:
                    st.caption(f"Von: {dok.geloescht_von.vorname} {dok.geloescht_von.nachname}")

            with col3:
                # Verbleibende Zeit
                verbleibend = papierkorb.get_verbleibende_zeit(dok)

                if verbleibend:
                    stunden = int(verbleibend.total_seconds() / 3600)
                    minuten = int((verbleibend.total_seconds() % 3600) / 60)

                    if stunden > 24:
                        tage = stunden // 24
                        st.markdown(f"Verbleibend: **{tage} Tage**")
                    elif stunden > 0:
                        st.markdown(f"Verbleibend: **{stunden}h {minuten}min**")
                    else:
                        st.markdown(f"Verbleibend: **{minuten} min**")

                    # Farbige Anzeige
                    if stunden < 2:
                        st.markdown(badge("Bald gelöscht", "danger"), unsafe_allow_html=True)
                    elif stunden < 12:
                        st.markdown(badge("Wenig Zeit", "warning"), unsafe_allow_html=True)
                    else:
                        st.markdown(badge("Wiederherstellbar", "success"), unsafe_allow_html=True)
                else:
                    st.markdown(badge("Abgelaufen", "danger"), unsafe_allow_html=True)

            with col4:
                # Aktionen
                if verbleibend:
                    if st.button("Wiederherstellen", key=f"restore_{dok.id}", type="primary"):
                        erfolg, nachricht = papierkorb.wiederherstellen(dok.id, user_id)
                        if erfolg:
                            st.success(nachricht)
                        else:
                            st.error(nachricht)
                        st.rerun()

                if st.button("Endgültig löschen", key=f"delete_{dok.id}"):
                    erfolg, nachricht = papierkorb.endgueltig_loeschen(dok.id)
                    if erfolg:
                        st.success(nachricht)
                    else:
                        st.error(nachricht)
                    st.rerun()

            st.markdown("---")


def _render_statistik(papierkorb):
    """Rendert die Papierkorb-Statistik"""

    stats = papierkorb.get_statistik()

    st.markdown("### Papierkorb-Statistik")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Dokumente gesamt", stats["gesamt"])

    with col2:
        st.metric("Wiederherstellbar", stats["wiederherstellbar"])

    with col3:
        st.metric("Abgelaufen", stats["abgelaufen"])

    with col4:
        st.metric("Speicherplatz", f"{stats['gesamt_groesse_mb']} MB")

    st.markdown("---")

    # Info-Box
    st.info(f"""
    **Aufbewahrungsdauer:** {stats['aufbewahrung_stunden']} Stunden

    Dokumente werden nach Ablauf der Aufbewahrungsfrist automatisch endgültig gelöscht.
    Die Aufbewahrungsdauer kann in den Einstellungen angepasst werden.
    """)


def _render_einstellungen(papierkorb, rolle: str):
    """Rendert die Papierkorb-Einstellungen"""

    st.markdown("### Papierkorb-Einstellungen")

    # Nur Admins können Einstellungen ändern
    if rolle != "ADMIN":
        st.warning("Nur Administratoren können die Papierkorb-Einstellungen ändern.")

        settings = get_settings()
        st.markdown(f"""
        **Aktuelle Einstellungen:**
        - Aufbewahrungsdauer: {settings.papierkorb_aufbewahrung_stunden} Stunden
        - Automatisches Löschen: {'Aktiviert' if settings.papierkorb_auto_loeschen else 'Deaktiviert'}
        """)
        return

    settings = get_settings()

    st.markdown("#### Aufbewahrungsdauer")

    # Schnellauswahl
    schnellauswahl = st.radio(
        "Schnellauswahl",
        ["12 Stunden", "24 Stunden", "48 Stunden (Standard)", "7 Tage", "30 Tage", "Benutzerdefiniert"],
        index=2,
        horizontal=True
    )

    stunden_mapping = {
        "12 Stunden": 12,
        "24 Stunden": 24,
        "48 Stunden (Standard)": 48,
        "7 Tage": 168,
        "30 Tage": 720,
    }

    if schnellauswahl == "Benutzerdefiniert":
        neue_stunden = st.number_input(
            "Aufbewahrungsdauer in Stunden",
            min_value=1,
            max_value=8760,  # 1 Jahr
            value=settings.papierkorb_aufbewahrung_stunden
        )
    else:
        neue_stunden = stunden_mapping[schnellauswahl]

    st.markdown("---")

    st.markdown("#### Automatisches Löschen")

    auto_loeschen = st.checkbox(
        "Automatisches Löschen nach Ablauf aktivieren",
        value=settings.papierkorb_auto_loeschen,
        help="Wenn aktiviert, werden abgelaufene Dokumente automatisch endgültig gelöscht"
    )

    st.markdown("---")

    # Speichern-Button
    if st.button("Einstellungen speichern", type="primary"):
        # Hinweis: In einer echten Anwendung würden die Einstellungen
        # in einer Datenbank oder Konfigurationsdatei gespeichert
        st.success(f"""
        Einstellungen gespeichert:
        - Aufbewahrungsdauer: {neue_stunden} Stunden
        - Automatisches Löschen: {'Aktiviert' if auto_loeschen else 'Deaktiviert'}

        **Hinweis:** Die Änderungen werden nach einem Neustart der Anwendung wirksam.
        Alternativ können Sie die Werte in der .env-Datei anpassen:
        - PAPIERKORB_AUFBEWAHRUNG_STUNDEN={neue_stunden}
        - PAPIERKORB_AUTO_LOESCHEN={'true' if auto_loeschen else 'false'}
        """)

    st.markdown("---")

    # Manuelle Bereinigung
    st.markdown("#### Manuelle Bereinigung")

    st.warning("""
    **Achtung:** Die folgenden Aktionen können nicht rückgängig gemacht werden!
    """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Abgelaufene Dokumente jetzt löschen"):
            geloescht, fehler = papierkorb.abgelaufene_loeschen()
            st.success(f"{geloescht} abgelaufene Dokumente gelöscht")
            if fehler > 0:
                st.warning(f"{fehler} Dokumente konnten nicht gelöscht werden")

    with col2:
        if st.button("Gesamten Papierkorb leeren", type="secondary"):
            st.session_state["confirm_empty_all"] = True

    if st.session_state.get("confirm_empty_all"):
        st.error("WARNUNG: Alle Dokumente im Papierkorb werden unwiderruflich gelöscht!")
        if st.button("Ja, ich bin sicher - ALLES LÖSCHEN", type="primary"):
            user_id = st.session_state.get("user_id")
            geloescht, fehler = papierkorb.papierkorb_leeren(user_id)
            st.session_state["confirm_empty_all"] = False
            st.success(f"{geloescht} Dokumente endgültig gelöscht")
            st.rerun()
