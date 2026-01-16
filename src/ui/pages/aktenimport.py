"""
Aktenimport UI-Seite
Import von PDF-Akten mit Dokumententrennung und Beteiligten-Verwaltung
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.aktenimport import (
    AktenImportService, AktenImport, AktenDokument, AktenBeteiligter,
    DokumentFreigabe, Einladung, EinladungsStatus, BeteiligtenRolle
)


def _render_inhaltsverzeichnis_baum(inhaltsverzeichnis: list, anzahl_seiten: int = 0):
    """Rendert das Inhaltsverzeichnis als grafischen Baum"""
    if not inhaltsverzeichnis:
        st.warning("Kein Inhaltsverzeichnis vorhanden")
        return

    # CSS für die Baumdarstellung
    st.markdown("""
    <style>
    .tree-container {
        font-family: monospace;
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .tree-root {
        font-weight: bold;
        color: #1f77b4;
        font-size: 16px;
    }
    .tree-item {
        margin: 8px 0;
        padding: 8px;
        background-color: white;
        border-left: 3px solid #4CAF50;
        border-radius: 4px;
    }
    .tree-item-title {
        font-weight: bold;
        color: #333;
    }
    .tree-item-pages {
        color: #666;
        font-size: 12px;
    }
    .tree-item-type {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 11px;
        margin-left: 8px;
    }
    .tree-branch {
        color: #999;
    }
    </style>
    """, unsafe_allow_html=True)

    # Baum-Header
    total_docs = len(inhaltsverzeichnis)
    st.markdown(f"""
    <div class="tree-container">
        <div class="tree-root">📁 Akte ({total_docs} Dokumente, {anzahl_seiten} Seiten)</div>
    </div>
    """, unsafe_allow_html=True)

    # Dokumente als Baum-Einträge
    for i, eintrag in enumerate(inhaltsverzeichnis):
        titel = eintrag.get('titel', f'Dokument {i+1}')
        seite_von = eintrag.get('seite_von', '?')
        seite_bis = eintrag.get('seite_bis', '?')
        typ = eintrag.get('typ', 'SONSTIGES')

        # Seitenbereich berechnen
        if seite_von == seite_bis:
            seiten_text = f"Seite {seite_von}"
        else:
            seiten_text = f"Seite {seite_von} - {seite_bis}"

        # Anzahl Seiten
        try:
            num_seiten = int(seite_bis) - int(seite_von) + 1
            seiten_text += f" ({num_seiten} Seiten)"
        except:
            pass

        # Typ-Icon
        typ_icons = {
            'GUTACHTEN': '📋',
            'KOSTENVORANSCHLAG': '💰',
            'RECHNUNG': '🧾',
            'VOLLMACHT': '📝',
            'KORRESPONDENZ': '✉️',
            'FOTOS': '📷',
            'POLIZEIBERICHT': '🚔',
            'URTEIL': '⚖️',
            'KLAGESCHRIFT': '📄',
            'AKTE': '📁',
            'SONSTIGES': '📎'
        }
        icon = typ_icons.get(typ, '📎')

        # Verzweigung anzeigen
        is_last = (i == len(inhaltsverzeichnis) - 1)
        branch = "└──" if is_last else "├──"

        # Dokument-Eintrag
        col1, col2, col3 = st.columns([0.5, 3, 1])
        with col1:
            st.markdown(f"<span style='color: #999; font-family: monospace;'>{branch}</span>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"{icon} **{titel}**")
            st.caption(seiten_text)
        with col3:
            st.markdown(f"<span style='background-color: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 3px; font-size: 12px;'>{typ}</span>", unsafe_allow_html=True)


def render_aktenimport():
    """Rendert die Aktenimport-Seite"""
    st.title("Aktenimport")

    st.info("""
    Importieren Sie komplette PDF-Akten. Das System erkennt automatisch:
    - Inhaltsverzeichnis und Dokumentstruktur
    - Aktenzeichen und Beteiligte
    - Einzelne Dokumente werden getrennt und können individuell freigegeben werden
    """)

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📁 RA-Micro Import",
        "📄 Standard Import",
        "📋 Importierte Akten",
        "👥 Beteiligte & Einladungen",
        "🔓 Dokumentfreigaben",
        "📊 Fortschritt"
    ])

    with tab1:
        _render_ramicro_import()

    with tab2:
        _render_import_wizard()

    with tab3:
        _render_importierte_akten()

    with tab4:
        _render_beteiligte_einladungen()

    with tab5:
        _render_dokumentfreigaben()

    with tab6:
        _render_fortschritt()


def _render_ramicro_import():
    """RA-Micro Aktengestalter Import"""
    st.subheader("📁 RA-Micro Aktengestalter Import")

    st.info("""
    **Spezieller Import für RA-Micro Aktengestalter PDFs:**
    - Automatische Erkennung des Aktenvorblatt
    - Extraktion von Beteiligten (Mandant, Gegner, Versicherung)
    - Erkennung von Schadenskosten und Kostenpositionen
    - Dokumententrennung anhand von PDF-Lesezeichen
    - Aktenzeichen im Format NNN/YY wird automatisch übernommen
    """)

    with get_session() as db:
        # Schritt 1: PDF hochladen
        st.markdown("### 1. RA-Micro PDF hochladen")

        uploaded_file = st.file_uploader(
            "RA-Micro PDF-Akte auswählen",
            type=["pdf"],
            help="Laden Sie die aus RA-Micro exportierte PDF hoch",
            key="ramicro_upload"
        )

        if uploaded_file:
            st.success(f"Datei: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

            # Analysieren-Button
            if st.button("📊 RA-Micro Akte analysieren", type="primary", use_container_width=True):
                with st.spinner("Analysiere RA-Micro PDF..."):
                    try:
                        from src.services.ramicro_parser import RAMicroParser

                        pdf_bytes = uploaded_file.read()
                        uploaded_file.seek(0)

                        parser = RAMicroParser()
                        ergebnis = parser.parse(pdf_bytes, uploaded_file.name)

                        st.session_state['ramicro_ergebnis'] = ergebnis
                        st.session_state['ramicro_pdf_bytes'] = pdf_bytes
                        st.session_state['ramicro_filename'] = uploaded_file.name

                    except Exception as e:
                        st.error(f"Fehler bei der Analyse: {str(e)}")

            # Ergebnis anzeigen
            if 'ramicro_ergebnis' in st.session_state:
                ergebnis = st.session_state['ramicro_ergebnis']

                st.markdown("---")
                st.markdown("### 2. Analyse-Ergebnis")

                # Fehler anzeigen
                if ergebnis.fehler:
                    for fehler in ergebnis.fehler:
                        st.warning(f"Hinweis: {fehler}")

                # Metriken
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Seiten", ergebnis.seitenzahl)
                with col2:
                    st.metric("Dokumente", len(ergebnis.dokument_segmente))
                with col3:
                    st.metric("Beteiligte", len(ergebnis.beteiligte))
                with col4:
                    if ergebnis.gegenstandswert:
                        st.metric("Gegenstandswert", f"{ergebnis.gegenstandswert:,.2f} €")
                    else:
                        st.metric("Gegenstandswert", "-")

                # Aktenzeichen
                if ergebnis.aktenzeichen:
                    st.success(f"📋 Erkanntes Aktenzeichen: **{ergebnis.aktenzeichen}**")

                if ergebnis.kurzbezeichnung:
                    st.info(f"Kurzbezeichnung: {ergebnis.kurzbezeichnung}")

                # Unfalldaten
                if ergebnis.unfalldatum or ergebnis.unfallort:
                    st.markdown("#### Unfalldaten")
                    col1, col2 = st.columns(2)
                    with col1:
                        if ergebnis.unfalldatum:
                            st.write(f"**Unfalldatum:** {ergebnis.unfalldatum.strftime('%d.%m.%Y')}")
                    with col2:
                        if ergebnis.unfallort:
                            st.write(f"**Unfallort:** {ergebnis.unfallort}")

                # Beteiligte
                if ergebnis.beteiligte:
                    st.markdown("#### Erkannte Beteiligte")

                    for bet in ergebnis.beteiligte:
                        with st.expander(f"👤 {bet.typ.value}: {bet.firma or bet.name or 'Unbekannt'}"):
                            col1, col2 = st.columns(2)

                            with col1:
                                if bet.firma:
                                    st.write(f"**Firma:** {bet.firma}")
                                if bet.name:
                                    st.write(f"**Name:** {bet.vorname or ''} {bet.name}")
                                if bet.strasse:
                                    st.write(f"**Adresse:** {bet.strasse}")
                                if bet.plz and bet.ort:
                                    st.write(f"**PLZ/Ort:** {bet.plz} {bet.ort}")

                            with col2:
                                if bet.telefon:
                                    st.write(f"**Telefon:** {', '.join(bet.telefon)}")
                                if bet.email:
                                    st.write(f"**E-Mail:** {', '.join(bet.email)}")
                                if bet.kennzeichen:
                                    st.write(f"**Kennzeichen:** {bet.kennzeichen}")
                                if bet.versicherungsnummer:
                                    st.write(f"**Vers.-Nr.:** {bet.versicherungsnummer}")
                                if bet.iban:
                                    st.write(f"**IBAN:** {bet.iban}")

                # Dokumentstruktur
                if ergebnis.dokument_segmente:
                    st.markdown("#### Dokumentstruktur (aus Lesezeichen)")

                    for seg in ergebnis.dokument_segmente:
                        seiten = f"S. {seg.start_seite}"
                        if seg.end_seite != seg.start_seite:
                            seiten = f"S. {seg.start_seite}-{seg.end_seite}"

                        typ_icon = {
                            "GUTACHTEN": "📋",
                            "RECHNUNG": "🧾",
                            "VOLLMACHT": "📝",
                            "AKTENVORBLATT": "📁",
                            "FOTOS": "📷",
                            "POLIZEIBERICHT": "🚔",
                        }.get(seg.typ, "📄")

                        st.write(f"{typ_icon} **{seg.titel}** ({seiten}) - {seg.typ or 'SONSTIG'}")

                # Kostenpositionen
                if ergebnis.kostenpositionen:
                    st.markdown("#### Erkannte Kostenpositionen")

                    # Gruppieren nach Kategorie
                    kosten_gruppen = {}
                    for kp in ergebnis.kostenpositionen:
                        if kp.kategorie not in kosten_gruppen:
                            kosten_gruppen[kp.kategorie] = []
                        kosten_gruppen[kp.kategorie].append(kp)

                    for kategorie, positionen in kosten_gruppen.items():
                        summe = sum(p.betrag for p in positionen)
                        with st.expander(f"💰 {kategorie}: {summe:,.2f} € ({len(positionen)} Positionen)"):
                            for pos in positionen[:5]:  # Max 5 pro Kategorie anzeigen
                                st.write(f"• {pos.betrag:,.2f} € - {pos.beschreibung[:50]}...")

                st.markdown("---")

                # Schritt 3: Import-Optionen
                st.markdown("### 3. Import durchführen")

                col1, col2 = st.columns(2)

                with col1:
                    import_option = st.radio(
                        "Akte importieren in:",
                        ["Neue Akte erstellen", "Bestehende Akte auswählen", "Aktenzeichen aus PDF verwenden"],
                        key="ramicro_import_option"
                    )

                with col2:
                    if import_option == "Bestehende Akte auswählen":
                        from src.models import UnfallProjekt

                        projekte = db.query(UnfallProjekt).order_by(
                            UnfallProjekt.erstellt_am.desc()
                        ).limit(50).all()

                        if projekte:
                            projekt_options = {
                                p.id: f"{p.aktenzeichen or p.projektnummer}"
                                for p in projekte
                            }
                            ziel_projekt_id = st.selectbox(
                                "Ziel-Akte",
                                list(projekt_options.keys()),
                                format_func=lambda x: projekt_options.get(x, ""),
                                key="ramicro_ziel_projekt"
                            )
                        else:
                            st.warning("Keine bestehenden Projekte")
                            ziel_projekt_id = None

                    elif import_option == "Aktenzeichen aus PDF verwenden":
                        if ergebnis.aktenzeichen:
                            st.info(f"Aktenzeichen: **{ergebnis.aktenzeichen}** wird verwendet")
                            # Prüfen ob Akte existiert
                            from src.models import UnfallProjekt

                            existierende = db.query(UnfallProjekt).filter(
                                UnfallProjekt.aktenzeichen == ergebnis.aktenzeichen
                            ).first()

                            if existierende:
                                st.warning(f"Akte {ergebnis.aktenzeichen} existiert bereits (ID: {existierende.id})")
                                ziel_projekt_id = existierende.id
                            else:
                                st.success("Neue Akte wird mit diesem Aktenzeichen erstellt")
                                ziel_projekt_id = "NEU_MIT_AZ"
                        else:
                            st.error("Kein Aktenzeichen im PDF erkannt")
                            ziel_projekt_id = None
                    else:
                        ziel_projekt_id = "NEU"
                        st.info("Eine neue Akte wird erstellt")

                # Import-Button
                if st.button("🚀 Import starten", type="primary", use_container_width=True, key="ramicro_import_btn"):
                    _execute_ramicro_import(db, ergebnis, ziel_projekt_id)


def _execute_ramicro_import(db, ergebnis, ziel_projekt_id):
    """Führt den RA-Micro Import durch"""
    from src.models import UnfallProjekt, Dokument, DokumentTyp, KostenPosition, KostenKategorie
    import os
    import uuid

    with st.spinner("Importiere RA-Micro Akte..."):
        try:
            user_id = st.session_state.get("user_id", 1)

            # Projekt erstellen oder laden
            if ziel_projekt_id == "NEU" or ziel_projekt_id == "NEU_MIT_AZ":
                projektnummer = f"RM-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

                projekt = UnfallProjekt(
                    projektnummer=projektnummer,
                    aktenzeichen=ergebnis.aktenzeichen,
                    aktenzeichen_nummer=ergebnis.aktenzeichen_nummer,
                    aktenzeichen_jahr=ergebnis.aktenzeichen_jahr,
                    datum_unfall=datetime.combine(ergebnis.unfalldatum, datetime.min.time()) if ergebnis.unfalldatum else None,
                    ort_unfall=ergebnis.unfallort,
                    status="IN_BEARBEITUNG",
                    angelegt_von_user_id=user_id
                )
                db.add(projekt)
                db.flush()

                st.success(f"Neue Akte erstellt: {projekt.aktenzeichen or projekt.projektnummer}")
            else:
                projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == ziel_projekt_id).first()
                if not projekt:
                    st.error("Ziel-Projekt nicht gefunden")
                    return

            # PDF speichern
            pdf_bytes = st.session_state.get('ramicro_pdf_bytes')
            filename = st.session_state.get('ramicro_filename', 'import.pdf')

            if pdf_bytes:
                upload_dir = f"uploads/{projekt.id}"
                os.makedirs(upload_dir, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dateipfad = os.path.join(upload_dir, f"{timestamp}_{filename}")

                with open(dateipfad, "wb") as f:
                    f.write(pdf_bytes)

                # Haupt-Dokument erstellen
                haupt_dok = Dokument(
                    unfallprojekt_id=projekt.id,
                    hochgeladen_von_user_id=user_id,
                    dokument_typ=DokumentTyp.SONSTIG,
                    original_dateiname=filename,
                    dateipfad=dateipfad,
                    dateigroesse=len(pdf_bytes),
                    storage_provider="local",
                    storage_key=dateipfad,
                    beschreibung="RA-Micro Aktenimport",
                    status="HOCHGELADEN",
                    freigabe_erforderlich=False,
                    freigabe_erteilt=True
                )
                db.add(haupt_dok)

            # Beteiligte als Notizen speichern (können später zu Users werden)
            beteiligte_info = []
            for bet in ergebnis.beteiligte:
                info = {
                    "typ": bet.typ.value,
                    "name": f"{bet.vorname or ''} {bet.name or ''}".strip(),
                    "firma": bet.firma,
                    "adresse": f"{bet.strasse or ''}, {bet.plz or ''} {bet.ort or ''}".strip(", "),
                    "email": bet.email,
                    "telefon": bet.telefon,
                    "kennzeichen": bet.kennzeichen,
                    "versicherungsnummer": bet.versicherungsnummer
                }
                beteiligte_info.append(info)

            # Kostenpositionen importieren (ohne Duplikate)
            importierte_kosten = 0
            kategorie_mapping = {
                "REPARATUR": KostenKategorie.REPARATUR,
                "GUTACHTEN": KostenKategorie.GUTACHTEN,
                "MIETWAGEN": KostenKategorie.ERSATZWAGEN,  # MIETWAGEN -> ERSATZWAGEN
                "NUTZUNGSAUSFALL": KostenKategorie.NUTZUNGSAUSFALL,
                "WERTMINDERUNG": KostenKategorie.WERTMINDERUNG,
                "ABSCHLEPPEN": KostenKategorie.SONSTIG,  # Kein ABSCHLEPPEN-Typ vorhanden
                "KOSTENPAUSCHALE": KostenKategorie.SONSTIG,  # Kein KOSTENPAUSCHALE-Typ
                "RECHTSANWALT": KostenKategorie.RA_GEBUEHREN,
            }

            # Nur eindeutige Beträge importieren (Duplikate vermeiden)
            gesehene_betraege = set()

            for kp in ergebnis.kostenpositionen:
                # Nur Beträge > 10€ und < 100.000€
                if kp.betrag < 10 or kp.betrag > 100000:
                    continue

                # Duplikate vermeiden
                if kp.betrag in gesehene_betraege:
                    continue
                gesehene_betraege.add(kp.betrag)

                kategorie = kategorie_mapping.get(kp.kategorie, KostenKategorie.SONSTIG)

                kosten_pos = KostenPosition(
                    unfallprojekt_id=projekt.id,
                    kategorie=kategorie,
                    beschreibung=kp.beschreibung[:200] if kp.beschreibung else f"Import: {kp.kategorie}",
                    betrag_brutto=kp.betrag,
                    eingetragen_von_user_id=user_id
                )
                db.add(kosten_pos)
                importierte_kosten += 1

            db.commit()

            # Session State leeren
            for key in ['ramicro_ergebnis', 'ramicro_pdf_bytes', 'ramicro_filename']:
                if key in st.session_state:
                    del st.session_state[key]

            st.success(f"""
            ✅ **Import erfolgreich!**

            - Akte: {projekt.aktenzeichen or projekt.projektnummer}
            - {len(ergebnis.beteiligte)} Beteiligte erkannt
            - {importierte_kosten} Kostenpositionen importiert
            - {len(ergebnis.dokument_segmente)} Dokumentsegmente erkannt
            """)

            # Beteiligte anzeigen
            if beteiligte_info:
                with st.expander("📋 Erkannte Beteiligte (zur manuellen Anlage)"):
                    for info in beteiligte_info:
                        st.write(f"**{info['typ']}:** {info['firma'] or info['name']}")
                        if info['email']:
                            st.write(f"  E-Mail: {', '.join(info['email'])}")

        except Exception as e:
            db.rollback()
            st.error(f"Fehler beim Import: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def _render_import_wizard():
    """Wizard für neuen Aktenimport"""
    st.subheader("PDF-Akte importieren")

    with get_session() as db:
        service = AktenImportService(db)

        # Schritt 1: Projekt auswählen oder neu erstellen
        st.markdown("### Schritt 1: Projekt zuordnen")

        from src.models import UnfallProjekt

        col1, col2 = st.columns([2, 1])

        with col1:
            option = st.radio(
                "Projekt",
                ["Bestehendes Projekt", "Neues Projekt erstellen"],
                horizontal=True
            )

        if option == "Bestehendes Projekt":
            projekte = db.query(UnfallProjekt).order_by(
                UnfallProjekt.erstellt_am.desc()
            ).limit(50).all()

            if projekte:
                projekt_options = {
                    p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
                    for p in projekte
                }
                projekt_id = st.selectbox(
                    "Projekt auswählen",
                    list(projekt_options.keys()),
                    format_func=lambda x: projekt_options.get(x, "")
                )
            else:
                st.warning("Keine Projekte vorhanden. Bitte erst ein Projekt anlegen.")
                projekt_id = None
        else:
            # Neues Projekt wird nach Import erstellt
            st.info("Ein neues Projekt wird automatisch mit den extrahierten Daten erstellt.")
            projekt_id = "NEU"

        st.markdown("---")

        # Schritt 2: PDF hochladen
        st.markdown("### Schritt 2: PDF-Akte hochladen")

        uploaded_file = st.file_uploader(
            "PDF-Datei auswählen",
            type=["pdf"],
            help="Laden Sie die komplette Akte als PDF hoch"
        )

        if uploaded_file:
            st.success(f"Datei: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

            # Vorschau und Analyse
            col_preview, col_action = st.columns([3, 1])

            with col_preview:
                if st.button("PDF analysieren (Vorschau)", use_container_width=True):
                    pdf_bytes = uploaded_file.read()
                    uploaded_file.seek(0)  # Reset für späteren Import

                    with st.spinner("Analysiere PDF..."):
                        vorschau = service._analysiere_pdf(pdf_bytes)
                        st.session_state['pdf_vorschau'] = vorschau
                        st.session_state['pdf_bytes'] = pdf_bytes

            # Vorschau anzeigen wenn vorhanden
            if 'pdf_vorschau' in st.session_state:
                vorschau = st.session_state['pdf_vorschau']

                st.markdown("---")
                st.markdown("### Analyse-Ergebnis (Vorschau)")

                # Debug-Info
                debug_info = vorschau.get('debug_info', {})
                methode = debug_info.get('methode', 'unbekannt')

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Seiten", vorschau.get('anzahl_seiten', 0))
                with col2:
                    st.metric("Erkannte Dokumente", len(vorschau.get('inhaltsverzeichnis', [])))
                with col3:
                    st.metric("PDF-Lesezeichen", debug_info.get('lesezeichen_gefunden', 0))
                with col4:
                    methode_label = {
                        'lesezeichen': 'PDF-Lesezeichen',
                        'text_toc': 'Inhaltsverzeichnis',
                        'fallback_gesamt': 'Nicht erkannt'
                    }.get(methode, methode)
                    st.metric("Erkennungsmethode", methode_label)

                # Erkanntes Inhaltsverzeichnis als Baum
                inhaltsverzeichnis = vorschau.get('inhaltsverzeichnis', [])
                if inhaltsverzeichnis:
                    st.markdown("#### Erkannte Dokumentstruktur")
                    _render_inhaltsverzeichnis_baum(
                        inhaltsverzeichnis,
                        vorschau.get('anzahl_seiten', 0)
                    )

                # Wenn nur ein Dokument (Fallback), warnen
                if methode == 'fallback_gesamt':
                    st.warning("""
                    **Hinweis:** Es wurde kein strukturiertes Inhaltsverzeichnis erkannt.
                    Die gesamte PDF wird als ein Dokument importiert.

                    **Mögliche Ursachen:**
                    - Die PDF enthält keine PDF-Lesezeichen (Bookmarks)
                    - Das Inhaltsverzeichnis im Text verwendet ein unbekanntes Format

                    **Tipp:** Zeigen Sie unten den extrahierten Text an, um das Format zu prüfen.
                    """)

                # Aktenzeichen
                if vorschau.get('aktenzeichen'):
                    st.info(f"Erkanntes Aktenzeichen: **{vorschau.get('aktenzeichen')}**")

                # Text-Vorschau (für Debugging)
                with st.expander("Extrahierten Text anzeigen (für Debugging)"):
                    seiten_texte = vorschau.get('seiten_texte', [])
                    if seiten_texte:
                        seite_nr = st.selectbox(
                            "Seite auswählen",
                            range(1, len(seiten_texte) + 1),
                            format_func=lambda x: f"Seite {x}"
                        )
                        if seite_nr and seite_nr <= len(seiten_texte):
                            st.text_area(
                                f"Text von Seite {seite_nr}",
                                seiten_texte[seite_nr - 1].get('text', ''),
                                height=300,
                                disabled=True
                            )
                    else:
                        st.warning("Kein Text extrahiert")

            st.markdown("---")

            # Import starten
            if st.button("Import starten", type="primary", use_container_width=True):
                if not projekt_id:
                    st.error("Bitte wählen Sie ein Projekt aus")
                    return

                # Neues Projekt erstellen falls nötig
                if projekt_id == "NEU":
                    from src.models import UnfallProjekt
                    import uuid

                    # Projektnummer generieren
                    projektnummer = f"P-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

                    neues_projekt = UnfallProjekt(
                        projektnummer=projektnummer
                    )
                    db.add(neues_projekt)
                    db.flush()

                    projekt_id = neues_projekt.id
                    st.info(f"Neues Projekt erstellt: {neues_projekt.projektnummer}")

                with st.spinner("Importiere Akte..."):
                    try:
                        # PDF-Bytes aus Vorschau oder neu lesen
                        if 'pdf_bytes' in st.session_state:
                            pdf_bytes = st.session_state['pdf_bytes']
                        else:
                            pdf_bytes = uploaded_file.read()

                        akten_import = service.importiere_akte(
                            projekt_id=projekt_id,
                            pdf_inhalt=pdf_bytes,
                            dateiname=uploaded_file.name,
                            user_id=st.session_state.get("user_id", 1)
                        )
                        db.commit()

                        # Vorschau-Cache leeren
                        if 'pdf_vorschau' in st.session_state:
                            del st.session_state['pdf_vorschau']
                        if 'pdf_bytes' in st.session_state:
                            del st.session_state['pdf_bytes']

                        if akten_import.import_abgeschlossen:
                            st.success("Import erfolgreich!")

                            # Ergebnis anzeigen
                            _zeige_import_ergebnis(akten_import)
                        else:
                            st.error(f"Import fehlgeschlagen: {akten_import.fehler_meldung}")

                    except Exception as e:
                        st.error(f"Fehler beim Import: {e}")


def _zeige_import_ergebnis(akten_import: AktenImport):
    """Zeigt das Ergebnis eines Imports"""
    st.markdown("---")
    st.markdown("### Import-Ergebnis")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Seiten", akten_import.anzahl_seiten)
    with col2:
        st.metric("Dokumente", akten_import.anzahl_dokumente)
    with col3:
        st.metric("Beteiligte", len(akten_import.beteiligte))
    with col4:
        if akten_import.extrahiertes_aktenzeichen:
            st.metric("Aktenzeichen", akten_import.extrahiertes_aktenzeichen)

    # Inhaltsverzeichnis als Baum
    if akten_import.inhaltsverzeichnis:
        st.markdown("#### Dokumentstruktur")
        _render_inhaltsverzeichnis_baum(
            akten_import.inhaltsverzeichnis,
            akten_import.anzahl_seiten
        )

    # Beteiligte
    if akten_import.beteiligte:
        st.markdown("#### Erkannte Beteiligte")

        for bet in akten_import.beteiligte:
            rolle_name = {
                BeteiligtenRolle.GESCHAEDIGTER: "Geschädigter",
                BeteiligtenRolle.UNFALLVERURSACHER: "Unfallverursacher",
                BeteiligtenRolle.VERSICHERUNG_VERURSACHER: "Gegnerische Versicherung",
                BeteiligtenRolle.VERSICHERUNG_GESCHAEDIGTER: "Eigene Versicherung",
                BeteiligtenRolle.GUTACHTER: "Gutachter",
                BeteiligtenRolle.WERKSTATT: "Werkstatt"
            }.get(bet.rolle, "Sonstiger")

            st.write(f"- **{bet.vorname} {bet.name}** ({rolle_name})")


def _render_importierte_akten():
    """Übersicht importierter Akten"""
    st.subheader("Importierte Akten")

    with get_session() as db:
        importe = db.query(AktenImport).order_by(
            AktenImport.import_datum.desc()
        ).limit(20).all()

        if not importe:
            st.info("Noch keine Akten importiert")
            return

        for imp in importe:
            status_icon = "✅" if imp.import_abgeschlossen else "❌"
            datum = imp.import_datum.strftime('%d.%m.%Y %H:%M') if imp.import_datum else '-'

            with st.expander(f"{status_icon} {imp.original_dateiname} - {datum}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Projekt-ID:** {imp.projekt_id}")
                    st.write(f"**Aktenzeichen:** {imp.extrahiertes_aktenzeichen or '-'}")
                    st.write(f"**Seiten:** {imp.anzahl_seiten}")
                    st.write(f"**Dokumente:** {imp.anzahl_dokumente}")

                with col2:
                    st.write(f"**Beteiligte:** {len(imp.beteiligte)}")
                    if imp.fehler_meldung:
                        st.error(f"Fehler: {imp.fehler_meldung}")

                # Inhaltsverzeichnis als Baum anzeigen
                if imp.inhaltsverzeichnis:
                    st.markdown("**Dokumentstruktur:**")
                    _render_inhaltsverzeichnis_baum(
                        imp.inhaltsverzeichnis,
                        imp.anzahl_seiten
                    )


def _render_beteiligte_einladungen():
    """Beteiligte verwalten und Einladungen versenden"""
    st.subheader("Beteiligte & Einladungen")

    with get_session() as db:
        service = AktenImportService(db)

        # Projekt auswählen
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        projekt_options = {
            p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
            for p in projekte
        }
        projekt_id = st.selectbox(
            "Projekt auswählen",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, ""),
            key="bet_projekt"
        )

        st.markdown("---")

        # Beteiligte des Projekts
        beteiligte = db.query(AktenBeteiligter).filter(
            AktenBeteiligter.projekt_id == projekt_id
        ).all()

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("### Beteiligte")

        with col2:
            if st.button("Beteiligten hinzufügen"):
                st.session_state["show_add_beteiligter"] = True

        # Neuen Beteiligten hinzufügen
        if st.session_state.get("show_add_beteiligter"):
            with st.form("add_beteiligter_form"):
                st.markdown("#### Neuen Beteiligten anlegen")

                col_a, col_b = st.columns(2)

                with col_a:
                    vorname = st.text_input("Vorname")
                    name = st.text_input("Nachname")

                with col_b:
                    email = st.text_input("E-Mail")
                    telefon = st.text_input("Telefon")

                rolle = st.selectbox(
                    "Rolle",
                    [r.value for r in BeteiligtenRolle],
                    format_func=lambda x: {
                        'GESCHAEDIGTER': 'Geschädigter',
                        'UNFALLVERURSACHER': 'Unfallverursacher',
                        'VERSICHERUNG_GESCHAEDIGTER': 'Eigene Versicherung',
                        'VERSICHERUNG_VERURSACHER': 'Gegnerische Versicherung',
                        'GUTACHTER': 'Gutachter',
                        'WERKSTATT': 'Werkstatt',
                        'ZEUGE': 'Zeuge',
                        'GEGNERISCHER_ANWALT': 'Gegnerischer Anwalt',
                        'SONSTIGER': 'Sonstiger'
                    }.get(x, x)
                )

                adresse = st.text_area("Adresse")

                submitted = st.form_submit_button("Speichern")

                if submitted:
                    # Import holen oder erstellen
                    akten_import = db.query(AktenImport).filter(
                        AktenImport.projekt_id == projekt_id
                    ).first()

                    if not akten_import:
                        akten_import = AktenImport(
                            projekt_id=projekt_id,
                            import_datum=datetime.now(),
                            importiert_von_user_id=st.session_state.get("user_id", 1),
                            import_abgeschlossen=True
                        )
                        db.add(akten_import)
                        db.flush()

                    neuer_beteiligter = AktenBeteiligter(
                        akten_import_id=akten_import.id,
                        projekt_id=projekt_id,
                        vorname=vorname,
                        name=name,
                        email=email,
                        telefon=telefon,
                        adresse=adresse,
                        rolle=BeteiligtenRolle(rolle)
                    )
                    db.add(neuer_beteiligter)
                    db.commit()

                    st.success("Beteiligter hinzugefügt!")
                    st.session_state["show_add_beteiligter"] = False
                    st.rerun()

        # Beteiligte auflisten
        if not beteiligte:
            st.info("Keine Beteiligten für dieses Projekt")
        else:
            # Checkboxen für Masseneinladung
            ausgewaehlte = []

            for bet in beteiligte:
                rolle_name = {
                    BeteiligtenRolle.GESCHAEDIGTER: "Geschädigter",
                    BeteiligtenRolle.UNFALLVERURSACHER: "Unfallverursacher",
                    BeteiligtenRolle.VERSICHERUNG_VERURSACHER: "Gegnerische Versicherung",
                    BeteiligtenRolle.VERSICHERUNG_GESCHAEDIGTER: "Eigene Versicherung",
                    BeteiligtenRolle.GUTACHTER: "Gutachter",
                    BeteiligtenRolle.WERKSTATT: "Werkstatt",
                    BeteiligtenRolle.ZEUGE: "Zeuge",
                    BeteiligtenRolle.GEGNERISCHER_ANWALT: "Gegnerischer Anwalt"
                }.get(bet.rolle, "Sonstiger")

                status_icon = "✅" if bet.user_id else "⏳"

                col_check, col_info, col_action = st.columns([0.5, 3, 1.5])

                with col_check:
                    if not bet.user_id and bet.email:
                        if st.checkbox("", key=f"sel_{bet.id}"):
                            ausgewaehlte.append(bet.id)

                with col_info:
                    st.write(f"{status_icon} **{bet.vorname} {bet.name}** - {rolle_name}")
                    if bet.email:
                        st.caption(f"E-Mail: {bet.email}")
                    if bet.user_id:
                        st.caption("Hat bereits Zugang")

                with col_action:
                    if not bet.user_id:
                        # Einzelne Einladung
                        if bet.email:
                            if st.button("Einladen", key=f"inv_{bet.id}"):
                                einladung = service.erstelle_einladung(
                                    beteiligter_id=bet.id,
                                    email=bet.email,
                                    erstellt_von_user_id=st.session_state.get("user_id", 1)
                                )
                                service.versende_einladung(einladung.id)
                                db.commit()

                                st.success(f"Einladung erstellt!")
                                st.info(f"Einmalpasswort: **{einladung.einmalpasswort_klartext}**")
                        else:
                            # E-Mail eingeben
                            email_input = st.text_input(
                                "E-Mail",
                                key=f"email_{bet.id}",
                                placeholder="E-Mail eingeben"
                            )
                            if email_input and st.button("Senden", key=f"send_{bet.id}"):
                                bet.email = email_input
                                einladung = service.erstelle_einladung(
                                    beteiligter_id=bet.id,
                                    email=email_input,
                                    erstellt_von_user_id=st.session_state.get("user_id", 1)
                                )
                                service.versende_einladung(einladung.id)
                                db.commit()

                                st.success(f"Einladung an {email_input} erstellt!")
                                st.info(f"Einmalpasswort: **{einladung.einmalpasswort_klartext}**")

            # Masseneinladung
            if ausgewaehlte:
                st.markdown("---")
                if st.button(f"Ausgewählte ({len(ausgewaehlte)}) einladen", type="primary"):
                    einladungen = service.erstelle_masseneinladung(
                        beteiligter_ids=ausgewaehlte,
                        erstellt_von_user_id=st.session_state.get("user_id", 1)
                    )

                    for einl in einladungen:
                        service.versende_einladung(einl.id)

                    db.commit()

                    st.success(f"{len(einladungen)} Einladungen erstellt!")

                    # Passwörter anzeigen
                    st.markdown("**Einmalpasswörter:**")
                    for einl in einladungen:
                        st.write(f"- {einl.email}: **{einl.einmalpasswort_klartext}**")


def _render_dokumentfreigaben():
    """Dokumente für Beteiligte freigeben"""
    st.subheader("Dokumentfreigaben")

    with get_session() as db:
        service = AktenImportService(db)

        # Projekt auswählen
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        projekt_options = {
            p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
            for p in projekte
        }
        projekt_id = st.selectbox(
            "Projekt auswählen",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, ""),
            key="freigabe_projekt"
        )

        st.markdown("---")

        # Dokumente und Beteiligte laden
        dokumente = db.query(AktenDokument).filter(
            AktenDokument.projekt_id == projekt_id
        ).order_by(AktenDokument.position_im_inhaltsverzeichnis).all()

        beteiligte = db.query(AktenBeteiligter).filter(
            AktenBeteiligter.projekt_id == projekt_id,
            AktenBeteiligter.user_id.isnot(None)  # Nur mit Account
        ).all()

        if not dokumente:
            st.info("Keine Dokumente für dieses Projekt")
            return

        if not beteiligte:
            st.warning("Keine Beteiligten mit Zugang vorhanden")

        # Freigabe-Matrix
        st.markdown("### Freigaben verwalten")

        for dok in dokumente:
            with st.expander(f"{dok.titel} (S. {dok.seite_von}-{dok.seite_bis})"):
                st.markdown("**Freigeben für:**")

                # Aktuelle Freigaben laden
                aktuelle_freigaben = {f.beteiligter_id for f in dok.freigaben}

                neue_freigaben = []

                for bet in beteiligte:
                    rolle_name = bet.rolle.value if bet.rolle else "Sonstiger"
                    ist_freigegeben = bet.id in aktuelle_freigaben

                    col1, col2, col3 = st.columns([0.5, 2, 1])

                    with col1:
                        checked = st.checkbox(
                            "",
                            value=ist_freigegeben,
                            key=f"freig_{dok.id}_{bet.id}"
                        )
                        if checked and not ist_freigegeben:
                            neue_freigaben.append(bet.id)

                    with col2:
                        st.write(f"{bet.vorname} {bet.name} ({rolle_name})")

                    with col3:
                        if ist_freigegeben:
                            freigabe = next(f for f in dok.freigaben if f.beteiligter_id == bet.id)
                            if freigabe.gelesen_am:
                                st.success("Gelesen")
                            else:
                                st.warning("Ungelesen")

                if neue_freigaben:
                    if st.button("Freigaben speichern", key=f"save_freig_{dok.id}"):
                        service.dokument_freigeben(
                            akten_dokument_id=dok.id,
                            beteiligter_ids=neue_freigaben,
                            freigegeben_von_user_id=st.session_state.get("user_id", 1)
                        )
                        db.commit()
                        st.success("Freigaben gespeichert!")
                        st.rerun()


def _render_fortschritt():
    """Fortschritts-Ansicht einer Akte"""
    st.subheader("Aktenfortschritt")

    with get_session() as db:
        service = AktenImportService(db)

        # Projekt auswählen
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        projekt_options = {
            p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
            for p in projekte
        }
        projekt_id = st.selectbox(
            "Projekt auswählen",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, ""),
            key="fortschritt_projekt"
        )

        st.markdown("---")

        # Fortschritt berechnen
        fortschritt_daten = service.berechne_aktenfortschritt(projekt_id)

        # Fortschrittsbalken
        st.markdown("### Gesamtfortschritt")
        st.progress(fortschritt_daten['fortschritt'] / 100)
        st.write(f"**{fortschritt_daten['fortschritt']:.1f}%** abgeschlossen")

        # Meilensteine
        if fortschritt_daten['meilensteine']:
            st.markdown("### Meilensteine")

            for meilenstein in fortschritt_daten['meilensteine']:
                status_icon = "✅" if meilenstein['abgeschlossen'] else "⏳"
                st.write(f"{status_icon} {meilenstein['titel']}")

        # Dokumentübersicht
        st.markdown("### Dokumente")

        dokumente = db.query(AktenDokument).filter(
            AktenDokument.projekt_id == projekt_id
        ).order_by(AktenDokument.position_im_inhaltsverzeichnis).all()

        if dokumente:
            # Timeline-Darstellung
            for i, dok in enumerate(dokumente):
                col_line, col_info = st.columns([0.5, 4])

                with col_line:
                    # Verbindungslinie
                    if dok.ist_meilenstein:
                        st.markdown("🎯")
                    elif dok.dokument_id:
                        st.markdown("●")
                    else:
                        st.markdown("○")

                with col_info:
                    freigaben_count = len(dok.freigaben)
                    st.write(f"**{dok.titel}**")
                    st.caption(f"{dok.dokumenttyp} | {freigaben_count} Freigaben | {dok.fortschritt_prozent:.1f}% Anteil")

                # Vertikale Linie zwischen Einträgen
                if i < len(dokumente) - 1:
                    st.markdown("<div style='border-left: 2px solid #ccc; height: 20px; margin-left: 10px;'></div>", unsafe_allow_html=True)
        else:
            st.info("Keine Dokumente vorhanden")
