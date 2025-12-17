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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Neue Akte importieren",
        "Importierte Akten",
        "Beteiligte & Einladungen",
        "Dokumentfreigaben",
        "Fortschritt"
    ])

    with tab1:
        _render_import_wizard()

    with tab2:
        _render_importierte_akten()

    with tab3:
        _render_beteiligte_einladungen()

    with tab4:
        _render_dokumentfreigaben()

    with tab5:
        _render_fortschritt()


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

                # Erkanntes Inhaltsverzeichnis
                inhaltsverzeichnis = vorschau.get('inhaltsverzeichnis', [])
                if inhaltsverzeichnis:
                    st.markdown("#### Erkanntes Inhaltsverzeichnis")

                    for i, eintrag in enumerate(inhaltsverzeichnis):
                        seiten = f"Seite {eintrag.get('seite_von', '?')}"
                        if eintrag.get('seite_bis') != eintrag.get('seite_von'):
                            seiten += f" - {eintrag.get('seite_bis', '?')}"
                        st.write(f"{i+1}. **{eintrag.get('titel', 'Unbenannt')}** ({seiten}) - Typ: {eintrag.get('typ', 'SONSTIGES')}")

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

    # Inhaltsverzeichnis
    if akten_import.inhaltsverzeichnis:
        st.markdown("#### Erkanntes Inhaltsverzeichnis")

        for eintrag in akten_import.inhaltsverzeichnis:
            st.write(f"- **{eintrag.get('titel', 'Dokument')}** (Seite {eintrag.get('seite_von', '?')} - {eintrag.get('seite_bis', '?')})")

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

                # Dokumente auflisten
                if imp.dokumente:
                    st.markdown("**Dokumente:**")
                    for dok in imp.dokumente:
                        meilenstein = "🎯 " if dok.ist_meilenstein else ""
                        st.write(f"- {meilenstein}{dok.titel} (S. {dok.seite_von}-{dok.seite_bis})")


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
