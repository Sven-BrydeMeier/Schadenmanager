"""
Dokumenten-Verwaltung mit OCR und KI-Extraktion
Inklusive OCR-Korrektur und Dokumentenfreigabe
"""
import streamlit as st
import os
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models import UnfallProjekt, Dokument, DokumentTyp
from src.services.ocr import get_ocr_service, get_ki_extraktor
from src.services.papierkorb import get_papierkorb_service
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

        tabs = st.tabs(["Hochladen", "Übersicht", "OCR-Prüfung", "Freigaben", "Verarbeitung"])

        with tabs[0]:
            _render_upload_tab(db, projekt)

        with tabs[1]:
            _render_dokumente_liste(db, projekt)

        with tabs[2]:
            _render_ocr_pruefung_tab(db, projekt)

        with tabs[3]:
            _render_freigaben_tab(db, projekt)

        with tabs[4]:
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
        status="HOCHGELADEN",
        freigabe_erforderlich=True,
        freigabe_erteilt=False
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

    # Nur nicht-gelöschte Dokumente anzeigen
    alle_dokumente = [d for d in projekt.dokumente if not d.geloescht]

    if not alle_dokumente:
        st.info("Noch keine Dokumente hochgeladen.")
        return

    # Filter
    col1, col2 = st.columns(2)

    with col1:
        typ_filter = st.selectbox(
            "Filtern nach Typ",
            ["Alle"] + [dt.value for dt in DokumentTyp],
            index=0
        )

    with col2:
        freigabe_filter = st.selectbox(
            "Freigabe-Status",
            ["Alle", "Freigegeben", "Ausstehend", "Abgelehnt"],
            index=0
        )

    dokumente = list(alle_dokumente)

    if typ_filter != "Alle":
        dokumente = [d for d in dokumente if d.dokument_typ and d.dokument_typ.value == typ_filter]

    if freigabe_filter == "Freigegeben":
        dokumente = [d for d in dokumente if d.freigabe_erteilt]
    elif freigabe_filter == "Ausstehend":
        dokumente = [d for d in dokumente if d.freigabe_erforderlich and not d.freigabe_erteilt and not d.freigabe_abgelehnt]
    elif freigabe_filter == "Abgelehnt":
        dokumente = [d for d in dokumente if d.freigabe_abgelehnt]

    st.markdown("---")

    papierkorb = get_papierkorb_service(db)
    user_id = st.session_state.get("user_id")

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
                if dok.ocr_manuell_korrigiert:
                    badges_html += badge("Korrigiert", "info") + " "
                if dok.ki_verarbeitet:
                    badges_html += badge("KI", "success") + " "
                if dok.ki_daten_uebernommen:
                    badges_html += badge("Übernommen", "success") + " "
                if dok.freigabe_erteilt:
                    badges_html += badge("Freigegeben", "success") + " "
                elif dok.freigabe_abgelehnt:
                    badges_html += badge("Abgelehnt", "danger") + " "
                elif dok.freigabe_erforderlich:
                    badges_html += badge("Freigabe ausstehend", "warning") + " "

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

                # Löschen-Button (in Papierkorb verschieben)
                if st.button("Löschen", key=f"delete_{dok.id}", type="secondary"):
                    erfolg, nachricht = papierkorb.in_papierkorb_verschieben(dok.id, user_id)
                    if erfolg:
                        st.success(nachricht)
                        st.info("Das Dokument kann im Papierkorb wiederhergestellt werden.")
                    else:
                        st.error(nachricht)
                    st.rerun()

            # OCR-Text anzeigen
            if dok.ocr_text:
                st.markdown("---")
                st.markdown("**Extrahierter Text (Vorschau):**")
                st.text_area("", dok.ocr_text[:1000] + ("..." if len(dok.ocr_text) > 1000 else ""), height=100, disabled=True, key=f"ocr_{dok.id}")

            # KI-Daten anzeigen
            if dok.ki_strukturierte_daten:
                st.markdown("---")
                st.markdown("**Extrahierte Daten:**")
                try:
                    daten = json.loads(dok.ki_strukturierte_daten)
                    for key, value in daten.items():
                        if value:
                            st.write(f"**{key}:** {value}")
                except:
                    st.json(dok.ki_strukturierte_daten)


def _render_ocr_pruefung_tab(db: Session, projekt: UnfallProjekt):
    """Rendert den OCR-Prüfungs-Tab"""

    st.markdown("### OCR-Ergebnisse prüfen und korrigieren")

    # Dokumente mit OCR-Text laden
    dokumente_mit_ocr = [d for d in projekt.dokumente if d.ocr_verarbeitet]

    if not dokumente_mit_ocr:
        st.info("Keine Dokumente mit OCR-Ergebnissen vorhanden.")
        return

    # Dokument auswählen
    dok_optionen = {
        f"{d.dokument_typ_anzeige}: {d.original_dateiname}": d
        for d in dokumente_mit_ocr
    }

    ausgewaehltes = st.selectbox("Dokument auswählen", list(dok_optionen.keys()))

    if ausgewaehltes:
        dok = dok_optionen[ausgewaehltes]

        st.markdown("---")

        # Status anzeigen
        col1, col2, col3 = st.columns(3)

        with col1:
            if dok.ocr_manuell_korrigiert:
                st.success("OCR wurde manuell korrigiert")
            else:
                st.info("OCR-Original")

        with col2:
            if dok.ki_daten_uebernommen:
                st.success("KI-Daten übernommen")
            else:
                st.warning("KI-Daten nicht übernommen")

        with col3:
            if dok.ocr_korrigiert_am:
                st.caption(f"Zuletzt bearbeitet: {dok.ocr_korrigiert_am.strftime('%d.%m.%Y %H:%M')}")

        st.markdown("---")

        # OCR-Text bearbeiten
        st.markdown("#### OCR-Text")
        st.caption("Sie können den erkannten Text hier korrigieren:")

        neuer_ocr_text = st.text_area(
            "OCR-Text",
            value=dok.ocr_text or "",
            height=300,
            key=f"edit_ocr_{dok.id}"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("OCR-Text speichern", type="primary", key=f"save_ocr_{dok.id}"):
                dok.ocr_text = neuer_ocr_text
                dok.ocr_manuell_korrigiert = True
                dok.ocr_korrigiert_von_user_id = st.session_state.get("user_id")
                dok.ocr_korrigiert_am = datetime.now()
                db.flush()
                st.success("OCR-Text wurde gespeichert!")
                st.rerun()

        with col2:
            if st.button("KI-Extraktion neu starten", key=f"rerun_ki_{dok.id}"):
                if dok.ocr_text:
                    ki_extraktor = get_ki_extraktor()
                    with st.spinner("KI-Extraktion läuft..."):
                        erfolg, fehler = ki_extraktor.verarbeite_dokument(dok, db)
                        if erfolg:
                            st.success("KI-Extraktion abgeschlossen!")
                            st.rerun()
                        else:
                            st.error(f"Fehler: {fehler}")

        # KI-Daten anzeigen und bearbeiten
        if dok.ki_strukturierte_daten:
            st.markdown("---")
            st.markdown("#### Extrahierte Daten (KI)")
            st.caption("Prüfen Sie die extrahierten Daten und übernehmen Sie sie:")

            try:
                ki_daten = json.loads(dok.ki_strukturierte_daten)

                # Daten in bearbeitbarem Format anzeigen
                bearbeitete_daten = {}

                for key, value in ki_daten.items():
                    if isinstance(value, (str, int, float)):
                        bearbeitete_daten[key] = st.text_input(
                            key.replace("_", " ").title(),
                            value=str(value) if value else "",
                            key=f"ki_{dok.id}_{key}"
                        )
                    elif isinstance(value, dict):
                        st.markdown(f"**{key.replace('_', ' ').title()}:**")
                        for sub_key, sub_value in value.items():
                            bearbeitete_daten[f"{key}.{sub_key}"] = st.text_input(
                                f"  {sub_key.replace('_', ' ').title()}",
                                value=str(sub_value) if sub_value else "",
                                key=f"ki_{dok.id}_{key}_{sub_key}"
                            )
                    elif isinstance(value, list):
                        st.markdown(f"**{key.replace('_', ' ').title()}:** {len(value)} Einträge")

                st.markdown("---")

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button("Daten übernehmen", type="primary", key=f"uebernehmen_{dok.id}"):
                        # Bearbeitete Daten speichern
                        dok.ki_strukturierte_daten = json.dumps(bearbeitete_daten, ensure_ascii=False)
                        dok.ki_daten_uebernommen = True
                        db.flush()
                        st.success("Daten wurden übernommen!")
                        st.rerun()

                with col2:
                    if st.button("Automatisch übernehmen", key=f"auto_uebernehmen_{dok.id}"):
                        dok.ki_daten_uebernommen = True
                        db.flush()
                        st.success("Daten wurden automatisch übernommen!")
                        st.rerun()

                with col3:
                    if st.button("Verwerfen", key=f"verwerfen_{dok.id}"):
                        dok.ki_strukturierte_daten = None
                        dok.ki_daten_uebernommen = False
                        db.flush()
                        st.info("Daten wurden verworfen.")
                        st.rerun()

            except json.JSONDecodeError:
                st.error("KI-Daten konnten nicht gelesen werden.")
                st.text(dok.ki_strukturierte_daten)


def _render_freigaben_tab(db: Session, projekt: UnfallProjekt):
    """Rendert den Freigaben-Tab"""

    st.markdown("### Dokumentenfreigabe für Beteiligte")

    rolle = st.session_state.get("user_rolle", "")

    # Ausstehende Freigaben zählen
    ausstehende = [
        d for d in projekt.dokumente
        if d.freigabe_erforderlich and not d.freigabe_erteilt and not d.freigabe_abgelehnt
    ]

    if ausstehende:
        st.warning(f"{len(ausstehende)} Dokumente warten auf Freigabe")

    st.markdown("---")

    # Freigabe-Übersicht
    st.markdown("#### Freigabe-Status")

    for dok in sorted(projekt.dokumente, key=lambda x: x.erstellt_am or datetime.min, reverse=True):
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            st.write(f"**{dok.dokument_typ_anzeige}:** {dok.original_dateiname}")
            if dok.hochgeladen_von:
                st.caption(f"Hochgeladen von: {dok.hochgeladen_von.voller_name}")

        with col2:
            if dok.freigabe_erteilt:
                st.markdown(badge("Freigegeben", "success"), unsafe_allow_html=True)
            elif dok.freigabe_abgelehnt:
                st.markdown(badge("Abgelehnt", "danger"), unsafe_allow_html=True)
            elif dok.freigabe_erforderlich:
                st.markdown(badge("Ausstehend", "warning"), unsafe_allow_html=True)
            else:
                st.markdown(badge("Keine Freigabe nötig", "secondary"), unsafe_allow_html=True)

        with col3:
            if not dok.freigabe_erteilt and not dok.freigabe_abgelehnt and dok.freigabe_erforderlich:
                if st.button("Freigeben", key=f"freigabe_{dok.id}", type="primary"):
                    dok.freigabe_erteilt = True
                    dok.freigabe_erteilt_von_user_id = st.session_state.get("user_id")
                    dok.freigabe_erteilt_am = datetime.now()
                    db.flush()
                    st.rerun()

        with col4:
            if not dok.freigabe_erteilt and not dok.freigabe_abgelehnt and dok.freigabe_erforderlich:
                if st.button("Ablehnen", key=f"ablehnen_{dok.id}"):
                    dok.freigabe_abgelehnt = True
                    dok.freigabe_abgelehnt_am = datetime.now()
                    db.flush()
                    st.rerun()

        st.markdown("---")

    # Alle freigeben Button
    if ausstehende:
        st.markdown("---")
        if st.button("Alle ausstehenden freigeben", type="primary"):
            for dok in ausstehende:
                dok.freigabe_erteilt = True
                dok.freigabe_erteilt_von_user_id = st.session_state.get("user_id")
                dok.freigabe_erteilt_am = datetime.now()
            db.flush()
            st.success(f"{len(ausstehende)} Dokumente wurden freigegeben!")
            st.rerun()


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

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Gesamt", len(projekt.dokumente))

    with col2:
        ocr_done = len([d for d in projekt.dokumente if d.ocr_verarbeitet])
        st.metric("OCR verarbeitet", ocr_done)

    with col3:
        ki_done = len([d for d in projekt.dokumente if d.ki_verarbeitet])
        st.metric("KI extrahiert", ki_done)

    with col4:
        freigegeben = len([d for d in projekt.dokumente if d.freigabe_erteilt])
        st.metric("Freigegeben", freigegeben)


def get_ausstehende_freigaben(db: Session, user_id: int, include_skipped: bool = False) -> list:
    """
    Gibt alle Dokumente zurück, die auf Freigabe durch den Benutzer warten.
    Wird für die Logout-Warnung verwendet.

    Args:
        db: Datenbank-Session
        user_id: ID des Benutzers
        include_skipped: Wenn False, werden übersprungene Dokumente nicht zurückgegeben

    Returns:
        Liste der ausstehenden Dokumente
    """
    from src.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    # Projekte des Benutzers finden
    projekte_ids = []

    # Je nach Rolle die relevanten Projekte finden
    rolle = user.rolle.value

    from src.models import UnfallProjekt

    query = db.query(UnfallProjekt)

    if rolle == "ANWALT":
        query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
    elif rolle == "WERKSTATT":
        query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)
    elif rolle == "GUTACHTER":
        query = query.filter(UnfallProjekt.gutachter_user_id == user_id)
    elif rolle == "VERSICHERUNG_GEGNER":
        query = query.filter(UnfallProjekt.versicherung_gegner_user_id == user_id)
    elif rolle == "ADMIN":
        pass  # Admin sieht alle
    else:
        return []

    projekte = query.all()

    # Ausstehende Freigaben sammeln
    ausstehende = []
    for projekt in projekte:
        for dok in projekt.dokumente:
            # Gelöschte Dokumente überspringen
            if dok.geloescht:
                continue
            if dok.freigabe_erforderlich and not dok.freigabe_erteilt and not dok.freigabe_abgelehnt:
                # Wenn include_skipped=False, übersprungene Dokumente ausfiltern
                if not include_skipped and dok.hat_freigabe_uebersprungen(user_id):
                    continue
                ausstehende.append(dok)

    return ausstehende
