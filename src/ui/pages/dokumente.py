"""
Dokumenten-Verwaltung mit OCR und KI-Extraktion
"""
import streamlit as st
import os
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models import UnfallProjekt, Dokument, DokumentTyp
from src.services.ocr import get_ocr_service, get_ki_extraktor
from src.ui.components import badge, alert
from src.config.database import get_session
from src.config.settings import get_settings


def render_dokumente():
    """Rendert die Dokumenten-Verwaltung"""

    st.markdown("## Dokumente")

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

        tabs = st.tabs(["Hochladen", "Übersicht", "Verarbeitung"])

        with tabs[0]:
            _render_upload_tab(db, projekt)

        with tabs[1]:
            _render_dokumente_liste(db, projekt)

        with tabs[2]:
            _render_verarbeitung_tab(db, projekt)


def _render_upload_tab(db: Session, projekt: UnfallProjekt):
    """Rendert den Upload-Tab"""

    st.markdown("### Dokument hochladen")

    col1, col2 = st.columns(2)

    with col1:
        dokument_typ = st.selectbox(
            "Dokumenttyp",
            options=[dt.value for dt in DokumentTyp],
            format_func=lambda x: {
                "FAHRZEUGSCHEIN": "Fahrzeugschein",
                "PERSONALAUSWEIS": "Personalausweis",
                "GUTACHTEN": "Gutachten",
                "RECHNUNG": "Rechnung",
                "VERSICHERUNGSSCHREIBEN": "Versicherungsschreiben",
                "KUERZUNGSSCHREIBEN": "Kürzungsschreiben",
                "ANSPRUCHSSCHREIBEN": "Anspruchsschreiben",
                "SONSTIG": "Sonstiges"
            }.get(x, x)
        )

    with col2:
        beschreibung = st.text_input("Beschreibung (optional)")

    uploaded_file = st.file_uploader(
        "Datei auswählen",
        type=["pdf", "png", "jpg", "jpeg", "tiff"],
        help="Unterstützte Formate: PDF, PNG, JPG, TIFF"
    )

    if uploaded_file:
        st.markdown("---")
        st.markdown("### Vorschau")

        col1, col2 = st.columns([2, 1])

        with col1:
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, width=400)
            else:
                st.info(f"Datei: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

        with col2:
            st.markdown(f"**Dateiname:** {uploaded_file.name}")
            st.markdown(f"**Größe:** {uploaded_file.size / 1024:.1f} KB")
            st.markdown(f"**Typ:** {dokument_typ}")

        # Upload-Button
        col1, col2, col3 = st.columns([1, 1, 1])

        with col2:
            if st.button("Hochladen und verarbeiten", type="primary", use_container_width=True):
                erfolg = _speichere_dokument(db, projekt, uploaded_file, dokument_typ, beschreibung)
                if erfolg:
                    st.success("Dokument wurde hochgeladen!")
                    st.rerun()


def _speichere_dokument(
    db: Session,
    projekt: UnfallProjekt,
    uploaded_file,
    dokument_typ: str,
    beschreibung: str
) -> bool:
    """Speichert ein hochgeladenes Dokument"""

    settings = get_settings()

    # Upload-Verzeichnis erstellen
    upload_dir = os.path.join(settings.upload_folder, str(projekt.id))
    os.makedirs(upload_dir, exist_ok=True)

    # Dateiname generieren
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dateiname = f"{timestamp}_{uploaded_file.name}"
    dateipfad = os.path.join(upload_dir, dateiname)

    # Datei speichern
    try:
        with open(dateipfad, "wb") as f:
            f.write(uploaded_file.getbuffer())
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")
        return False

    # Dokument in DB erstellen
    dokument = Dokument(
        unfallprojekt_id=projekt.id,
        hochgeladen_von_user_id=st.session_state.get("user_id"),
        dokument_typ=DokumentTyp(dokument_typ),
        original_dateiname=uploaded_file.name,
        dateipfad=dateipfad,
        mime_typ=uploaded_file.type,
        dateigroesse=uploaded_file.size,
        beschreibung=beschreibung,
        status="HOCHGELADEN"
    )

    db.add(dokument)
    db.flush()

    # Automatische OCR-Verarbeitung starten
    _starte_ocr_verarbeitung(db, dokument)

    return True


def _starte_ocr_verarbeitung(db: Session, dokument: Dokument):
    """Startet die OCR-Verarbeitung für ein Dokument"""

    ocr_service = get_ocr_service()

    with st.spinner("OCR-Verarbeitung läuft..."):
        erfolg, fehler = ocr_service.verarbeite_dokument(dokument, db)

        if not erfolg:
            st.warning(f"OCR-Verarbeitung fehlgeschlagen: {fehler}")
            return

        # KI-Extraktion starten
        if dokument.ocr_text and dokument.dokument_typ:
            ki_extraktor = get_ki_extraktor()

            with st.spinner("KI-Extraktion läuft..."):
                erfolg, fehler = ki_extraktor.verarbeite_dokument(dokument, db)

                if not erfolg:
                    st.warning(f"KI-Extraktion fehlgeschlagen: {fehler}")


def _render_dokumente_liste(db: Session, projekt: UnfallProjekt):
    """Rendert die Liste der Dokumente"""

    st.markdown("### Dokumente")

    if not projekt.dokumente:
        st.info("Noch keine Dokumente hochgeladen.")
        return

    # Filter
    typ_filter = st.selectbox(
        "Filtern nach Typ",
        ["Alle"] + [dt.value for dt in DokumentTyp],
        index=0
    )

    dokumente = projekt.dokumente

    if typ_filter != "Alle":
        dokumente = [d for d in dokumente if d.dokument_typ and d.dokument_typ.value == typ_filter]

    st.markdown("---")

    for dok in sorted(dokumente, key=lambda x: x.erstellt_am or datetime.min, reverse=True):
        with st.expander(f"{dok.dokument_typ_anzeige}: {dok.original_dateiname}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Hochgeladen:** {dok.erstellt_am.strftime('%d.%m.%Y %H:%M') if dok.erstellt_am else '-'}")
                if dok.beschreibung:
                    st.write(f"**Beschreibung:** {dok.beschreibung}")

                # Status-Badges
                badges_html = ""
                if dok.ocr_verarbeitet:
                    badges_html += badge("OCR", "success") + " "
                if dok.ki_verarbeitet:
                    badges_html += badge("KI", "success") + " "
                if not dok.ocr_verarbeitet and not dok.ki_verarbeitet:
                    badges_html += badge("Ausstehend", "warning")

                st.markdown(badges_html, unsafe_allow_html=True)

            with col2:
                # Aktionen
                if dok.dateipfad and os.path.exists(dok.dateipfad):
                    with open(dok.dateipfad, "rb") as f:
                        st.download_button(
                            "Herunterladen",
                            data=f.read(),
                            file_name=dok.original_dateiname,
                            mime=dok.mime_typ,
                            key=f"download_{dok.id}"
                        )

            # OCR-Text anzeigen
            if dok.ocr_text:
                st.markdown("---")
                st.markdown("**Extrahierter Text:**")
                st.text_area("", dok.ocr_text[:2000], height=150, disabled=True, key=f"ocr_{dok.id}")

            # KI-Daten anzeigen
            if dok.ki_strukturierte_daten:
                st.markdown("---")
                st.markdown("**Extrahierte Daten:**")
                st.json(dok.ki_strukturierte_daten)


def _render_verarbeitung_tab(db: Session, projekt: UnfallProjekt):
    """Rendert den Verarbeitungs-Tab"""

    st.markdown("### Batch-Verarbeitung")

    unverarbeitete = [d for d in projekt.dokumente if not d.ocr_verarbeitet]

    if unverarbeitete:
        st.write(f"{len(unverarbeitete)} Dokumente warten auf Verarbeitung:")

        for dok in unverarbeitete:
            st.write(f"- {dok.original_dateiname}")

        if st.button("Alle verarbeiten"):
            ocr_service = get_ocr_service()
            ki_extraktor = get_ki_extraktor()

            progress = st.progress(0)

            for i, dok in enumerate(unverarbeitete):
                st.write(f"Verarbeite: {dok.original_dateiname}...")

                # OCR
                erfolg, fehler = ocr_service.verarbeite_dokument(dok, db)
                if erfolg and dok.dokument_typ:
                    # KI
                    ki_extraktor.verarbeite_dokument(dok, db)

                progress.progress((i + 1) / len(unverarbeitete))

            st.success("Verarbeitung abgeschlossen!")
            st.rerun()
    else:
        st.success("Alle Dokumente wurden verarbeitet.")

    # Statistik
    st.markdown("---")
    st.markdown("### Statistik")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Gesamt", len(projekt.dokumente))

    with col2:
        ocr_done = len([d for d in projekt.dokumente if d.ocr_verarbeitet])
        st.metric("OCR verarbeitet", ocr_done)

    with col3:
        ki_done = len([d for d in projekt.dokumente if d.ki_verarbeitet])
        st.metric("KI extrahiert", ki_done)
