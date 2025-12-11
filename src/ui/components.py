"""
Wiederverwendbare UI-Komponenten für Streamlit
"""
import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models import MeilensteinStatus, KostenAmpel
from src.ui.styles import AMPEL_COLORS


def card(title: str = None, content: str = None, key: str = None):
    """
    Erstellt eine Card-Komponente.

    Usage:
        with card("Titel"):
            st.write("Inhalt")
    """
    html = '<div class="card">'
    if title:
        html += f'<div class="card-header">{title}</div>'
    html += '<div class="card-body">'

    st.markdown(html, unsafe_allow_html=True)

    # Return context manager
    class CardContext:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            st.markdown('</div></div>', unsafe_allow_html=True)

    return CardContext()


def card_simple(title: str, content: str):
    """Erstellt eine einfache Card ohne Context Manager"""
    st.markdown(f'''
    <div class="card">
        <div class="card-header">{title}</div>
        <div class="card-body">{content}</div>
    </div>
    ''', unsafe_allow_html=True)


def metric_card(label: str, value: str, style: str = "default"):
    """
    Erstellt eine Metrik-Card mit Farbverlauf.

    Args:
        label: Beschriftung
        value: Anzuzeigender Wert
        style: "default", "success", "warning", "info"
    """
    style_class = f"metric-card {style}" if style != "default" else "metric-card"
    st.markdown(f'''
    <div class="{style_class}">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    ''', unsafe_allow_html=True)


def badge(text: str, style: str = "secondary"):
    """
    Erstellt ein Badge.

    Args:
        text: Badge-Text
        style: "success", "warning", "danger", "info", "secondary"
    """
    return f'<span class="badge badge-{style}">{text}</span>'


def ampel_punkt(status: str):
    """
    Erstellt einen Ampel-Punkt.

    Args:
        status: "ROT", "ORANGE", "GRUEN"
    """
    status_lower = status.lower()
    return f'<span class="ampel ampel-{status_lower}"></span>'


def alert(message: str, style: str = "info"):
    """
    Zeigt eine Alert-Box an.

    Args:
        message: Nachricht
        style: "success", "warning", "danger", "info"
    """
    st.markdown(f'''
    <div class="alert alert-{style}">
        {message}
    </div>
    ''', unsafe_allow_html=True)


def timeline(meilensteine: List[Dict[str, Any]]):
    """
    Zeigt eine horizontale Timeline mit Meilensteinen an.

    Args:
        meilensteine: Liste von Meilensteinen mit keys: code, beschreibung, status
    """
    if not meilensteine:
        st.info("Keine Meilensteine vorhanden")
        return

    # Container für die Timeline
    cols = st.columns(len(meilensteine))

    for i, (col, ms) in enumerate(zip(cols, meilensteine)):
        with col:
            # Status-Farbe bestimmen
            status = ms.get("status", "ROT")
            if isinstance(status, MeilensteinStatus):
                status = status.value
            farbe = AMPEL_COLORS.get(status, "#6c757d")

            # Icon basierend auf Status
            if status == "GRUEN":
                icon = "✓"
            elif status == "ORANGE":
                icon = "◐"
            else:
                icon = "○"

            st.markdown(f'''
            <div style="text-align: center;">
                <div style="
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    background-color: {farbe};
                    color: white;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                    margin-bottom: 8px;
                ">{icon}</div>
                <div style="font-size: 0.75rem; color: #64748b;">
                    {ms.get("beschreibung", ms.get("code", ""))}
                </div>
            </div>
            ''', unsafe_allow_html=True)


def kosten_uebersicht(kostenpositionen: List[Dict[str, Any]]):
    """
    Zeigt eine Übersicht der Kostenpositionen mit Ampeln.

    Args:
        kostenpositionen: Liste von Kostenpositionen
    """
    if not kostenpositionen:
        st.info("Keine Kostenpositionen vorhanden")
        return

    gesamt = 0
    gesamt_freigegeben = 0

    for kp in kostenpositionen:
        status = kp.get("status_ampel", "ROT")
        if isinstance(status, KostenAmpel):
            status = status.value
        farbe = AMPEL_COLORS.get(status, "#6c757d")

        kategorie = kp.get("kategorie_anzeige", kp.get("kategorie", "Sonstig"))
        betrag = kp.get("betrag_brutto", 0)
        freigegeben = kp.get("von_versicherung_freigegeben_betrag", 0)
        gekuerzt = kp.get("gekuerzt", False)

        gesamt += betrag
        gesamt_freigegeben += freigegeben or 0

        # Zeile erstellen
        col1, col2, col3 = st.columns([0.5, 3, 1.5])

        with col1:
            st.markdown(f'''
            <div style="
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background-color: {farbe};
                margin-top: 8px;
            "></div>
            ''', unsafe_allow_html=True)

        with col2:
            beschreibung = kp.get("beschreibung", "")
            text = f"**{kategorie}**"
            if beschreibung:
                text += f" - {beschreibung}"
            st.markdown(text)

        with col3:
            if gekuerzt and freigegeben is not None:
                st.markdown(f"~~{betrag:,.2f} €~~ → **{freigegeben:,.2f} €**")
            else:
                st.markdown(f"**{betrag:,.2f} €**")

    # Summenzeile
    st.markdown("---")
    col1, col2, col3 = st.columns([0.5, 3, 1.5])
    with col2:
        st.markdown("**Gesamt**")
    with col3:
        if gesamt_freigegeben > 0 and gesamt_freigegeben != gesamt:
            st.markdown(f"~~{gesamt:,.2f} €~~ → **{gesamt_freigegeben:,.2f} €**")
        else:
            st.markdown(f"**{gesamt:,.2f} €**")


def projekt_header(projekt: Any):
    """
    Zeigt den Projekt-Header mit wichtigen Infos an.

    Args:
        projekt: UnfallProjekt-Objekt
    """
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.markdown(f"### Projekt {projekt.projektnummer}")
        if projekt.kfz_eigen:
            st.caption(f"Fahrzeug: {projekt.kfz_eigen.kennzeichen} ({projekt.kfz_eigen.fahrzeug_bezeichnung})")

    with col2:
        if projekt.datum_unfall:
            st.markdown(f"**Unfalldatum:** {projekt.datum_unfall.strftime('%d.%m.%Y')}")
        if projekt.ort_unfall:
            st.markdown(f"**Unfallort:** {projekt.ort_unfall}")

    with col3:
        status_farbe = {
            "OFFEN": "warning",
            "IN_BEARBEITUNG": "info",
            "ABGESCHLOSSEN": "success",
            "STORNIERT": "danger"
        }.get(projekt.status, "secondary")
        st.markdown(badge(projekt.status_anzeige, status_farbe), unsafe_allow_html=True)


def dokument_upload(label: str = "Dokument hochladen", accepted_types: List[str] = None, key: str = None):
    """
    Erstellt einen Dokument-Upload mit Vorschau.

    Args:
        label: Upload-Label
        accepted_types: Liste erlaubter Dateitypen
        key: Streamlit-Key

    Returns:
        Hochgeladene Datei oder None
    """
    if accepted_types is None:
        accepted_types = ["pdf", "png", "jpg", "jpeg", "tiff"]

    uploaded_file = st.file_uploader(
        label,
        type=accepted_types,
        key=key
    )

    if uploaded_file:
        # Dateiinfo anzeigen
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"Datei: {uploaded_file.name}")
            st.caption(f"Größe: {uploaded_file.size / 1024:.1f} KB")
        with col2:
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, width=100)

    return uploaded_file


def sidebar_navigation(rolle: str, aktives_projekt: Any = None):
    """
    Erstellt die Sidebar-Navigation basierend auf der Rolle.

    Args:
        rolle: Benutzerrolle
        aktives_projekt: Optional das aktive Projekt

    Returns:
        Ausgewählter Menüpunkt
    """
    st.sidebar.markdown("## Navigation")

    # Gemeinsame Menüpunkte
    menu_punkte = ["Dashboard", "Projekte"]

    # Rollenspezifische Menüpunkte
    if rolle in ["ANWALT", "ADMIN"]:
        menu_punkte.extend(["Korrespondenz", "Gebührenberechnung"])

    if rolle in ["WERKSTATT", "ADMIN"]:
        menu_punkte.extend(["Ersatzwagen"])

    if rolle in ["GUTACHTER", "ADMIN"]:
        menu_punkte.extend(["Gutachten"])

    if rolle == "ADMIN":
        menu_punkte.extend(["Organisationen", "Benutzer", "Einstellungen"])

    menu_punkte.append("Dokumente")

    auswahl = st.sidebar.radio("", menu_punkte, label_visibility="collapsed")

    # Aktives Projekt anzeigen
    if aktives_projekt:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Aktives Projekt:**")
        st.sidebar.markdown(f"{aktives_projekt.projektnummer}")

    # Logout-Button
    st.sidebar.markdown("---")
    if st.sidebar.button("Abmelden", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    return auswahl


def bestaetigung_dialog(title: str, message: str, key: str):
    """
    Zeigt einen Bestätigungsdialog an.

    Args:
        title: Titel des Dialogs
        message: Nachricht
        key: Eindeutiger Key für den State

    Returns:
        True wenn bestätigt, False sonst
    """
    if f"confirm_{key}" not in st.session_state:
        st.session_state[f"confirm_{key}"] = False

    if not st.session_state[f"confirm_{key}"]:
        with st.expander(title, expanded=True):
            st.warning(message)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Bestätigen", key=f"btn_confirm_{key}", type="primary"):
                    st.session_state[f"confirm_{key}"] = True
                    st.rerun()
            with col2:
                if st.button("Abbrechen", key=f"btn_cancel_{key}"):
                    return False
        return False

    return True


def fortschritt_anzeige(aktuell: int, gesamt: int, label: str = ""):
    """
    Zeigt eine Fortschrittsanzeige an.

    Args:
        aktuell: Aktuelle Anzahl
        gesamt: Gesamtanzahl
        label: Optionales Label
    """
    if gesamt == 0:
        prozent = 0
    else:
        prozent = int((aktuell / gesamt) * 100)

    st.progress(prozent / 100, text=f"{label} {aktuell}/{gesamt} ({prozent}%)")
