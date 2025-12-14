"""
Schadensbilder-Galerie UI-Seite
Organisierte Bildverwaltung für Unfallfotos
"""
import streamlit as st

from src.config.database import get_session
from src.services.schadensbilder import SchadensbilderService, Schadensbild, BildKategorie


def render_schadensbilder():
    """Rendert die Schadensbilder-Galerie"""
    st.title("📷 Schadensbilder-Galerie")

    # Projekt-Auswahl
    projekt_id = st.session_state.get("aktives_projekt_id")

    if not projekt_id:
        with get_session() as db:
            from src.models import UnfallProjekt
            projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).limit(50).all()

            if not projekte:
                st.warning("Keine Projekte vorhanden")
                return

            projekt_options = {p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}" for p in projekte}
            projekt_id = st.selectbox(
                "Projekt auswählen",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, "")
            )

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Galerie", "Nach Kategorie", "Upload", "Statistik"
    ])

    with tab1:
        _render_galerie(projekt_id)

    with tab2:
        _render_nach_kategorie(projekt_id)

    with tab3:
        _render_upload(projekt_id)

    with tab4:
        _render_statistik(projekt_id)


def _render_galerie(projekt_id: int):
    """Zeigt alle Bilder in einer Galerie"""
    st.subheader("Alle Schadensbilder")

    with get_session() as db:
        service = SchadensbilderService(db)
        bilder = service.bilder_fuer_projekt(projekt_id)

        if not bilder:
            st.info("Noch keine Schadensbilder für dieses Projekt")
            return

        # Anzeigeoptionen
        col_opt1, col_opt2 = st.columns(2)

        with col_opt1:
            ansicht = st.radio("Ansicht", ["Raster", "Liste"], horizontal=True)

        with col_opt2:
            sortierung = st.selectbox(
                "Sortierung",
                ["Nach Kategorie", "Nach Datum", "Nach Name"]
            )

        st.markdown("---")

        if ansicht == "Raster":
            # Raster-Ansicht (3 Spalten)
            cols = st.columns(3)

            for i, bild in enumerate(bilder):
                with cols[i % 3]:
                    _render_bild_card(bild, service)
        else:
            # Listen-Ansicht
            for bild in bilder:
                with st.expander(f"{bild.kategorie_anzeige} - {bild.original_dateiname}"):
                    _render_bild_details(bild, service)


def _render_bild_card(bild: Schadensbild, service: SchadensbilderService):
    """Zeigt eine Bild-Karte"""
    st.markdown(f"**{bild.kategorie_anzeige}**")
    st.caption(bild.original_dateiname or bild.dateiname)

    # Bildvorschau (falls vorhanden)
    if bild.dateipfad:
        try:
            st.image(bild.dateipfad, use_container_width=True)
        except Exception:
            st.info("📷 Bild nicht verfügbar")

    if bild.beschreibung:
        st.write(bild.beschreibung)

    st.caption(f"📁 {bild.dateigroesse_anzeige}")


def _render_bild_details(bild: Schadensbild, service: SchadensbilderService):
    """Zeigt Bild-Details"""
    col1, col2 = st.columns([2, 1])

    with col1:
        if bild.dateipfad:
            try:
                st.image(bild.dateipfad, use_container_width=True)
            except Exception:
                st.info("📷 Bild nicht verfügbar")

    with col2:
        st.write(f"**Kategorie:** {bild.kategorie_anzeige}")
        st.write(f"**Dateiname:** {bild.original_dateiname}")
        st.write(f"**Größe:** {bild.dateigroesse_anzeige}")
        st.write(f"**Typ:** {bild.dateityp or '-'}")

        if bild.aufnahme_datum:
            st.write(f"**Aufnahme:** {bild.aufnahme_datum.strftime('%d.%m.%Y %H:%M')}")

        if bild.aufnahme_ort:
            st.write(f"**Ort:** {bild.aufnahme_ort}")

        if bild.tags:
            st.write(f"**Tags:** {bild.tags}")

        # Beschreibung bearbeiten
        neue_beschreibung = st.text_area(
            "Beschreibung",
            value=bild.beschreibung or "",
            height=80,
            key=f"beschr_{bild.id}"
        )

        # Kategorie ändern
        neue_kategorie = st.selectbox(
            "Kategorie ändern",
            [k for k in BildKategorie],
            index=[k for k in BildKategorie].index(bild.kategorie),
            format_func=lambda k: _kategorie_anzeige(k),
            key=f"kat_{bild.id}"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("💾 Speichern", key=f"save_{bild.id}"):
                with get_session() as db:
                    svc = SchadensbilderService(db)
                    svc.bild_kategorisieren(bild.id, neue_kategorie, neue_beschreibung)
                    st.success("Gespeichert!")
                    st.rerun()

        with col_b:
            if st.button("🗑️ Löschen", key=f"del_{bild.id}"):
                with get_session() as db:
                    svc = SchadensbilderService(db)
                    svc.bild_loeschen(bild.id)
                    st.success("Bild gelöscht")
                    st.rerun()

    # Markierungen
    if bild.markierungen:
        st.markdown("**Markierungen:**")
        for mark in bild.markierungen:
            st.write(f"- {mark.get('text', '')} @ ({mark.get('x')}, {mark.get('y')})")


def _render_nach_kategorie(projekt_id: int):
    """Zeigt Bilder nach Kategorie gruppiert"""
    st.subheader("Bilder nach Kategorie")

    with get_session() as db:
        service = SchadensbilderService(db)
        gruppiert = service.bilder_nach_kategorie(projekt_id)

        if not gruppiert:
            st.info("Keine Bilder vorhanden")
            return

        for kategorie, bilder in gruppiert.items():
            with st.expander(f"{_kategorie_anzeige(kategorie)} ({len(bilder)})", expanded=True):
                cols = st.columns(4)

                for i, bild in enumerate(bilder):
                    with cols[i % 4]:
                        if bild.dateipfad:
                            try:
                                st.image(bild.dateipfad, use_container_width=True)
                            except Exception:
                                st.info("📷")

                        st.caption(bild.original_dateiname or bild.dateiname)

                        if bild.beschreibung:
                            st.caption(bild.beschreibung[:50])


def _render_upload(projekt_id: int):
    """Bild-Upload"""
    st.subheader("Bilder hochladen")

    uploaded_files = st.file_uploader(
        "Bilder auswählen",
        type=["jpg", "jpeg", "png", "gif", "webp", "bmp"],
        accept_multiple_files=True
    )

    if uploaded_files:
        kategorie = st.selectbox(
            "Kategorie für alle Bilder",
            [k for k in BildKategorie],
            format_func=lambda k: _kategorie_anzeige(k)
        )

        beschreibung = st.text_input("Beschreibung (optional)")

        if st.button("Bilder hochladen", type="primary"):
            import os
            from src.config.settings import get_settings

            settings = get_settings()
            upload_dir = os.path.join(settings.upload_folder, str(projekt_id), "schadensbilder")
            os.makedirs(upload_dir, exist_ok=True)

            with get_session() as db:
                service = SchadensbilderService(db)
                user_id = st.session_state.get("user_id")

                for uploaded_file in uploaded_files:
                    # Datei speichern
                    dateipfad = os.path.join(upload_dir, uploaded_file.name)

                    with open(dateipfad, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # In DB eintragen
                    bild = service.bild_hinzufuegen(
                        projekt_id=projekt_id,
                        dateiname=uploaded_file.name,
                        dateipfad=dateipfad,
                        kategorie=kategorie,
                        beschreibung=beschreibung,
                        hochgeladen_von_user_id=user_id
                    )

                st.success(f"{len(uploaded_files)} Bild(er) hochgeladen!")
                st.rerun()

    # Import aus Dokumenten
    st.markdown("---")
    st.markdown("### Aus Dokumenten importieren")

    with get_session() as db:
        from src.models import Dokument

        dokumente = db.query(Dokument).filter(
            Dokument.projekt_id == projekt_id,
            Dokument.dateipfad.ilike("%.jpg") | Dokument.dateipfad.ilike("%.jpeg") |
            Dokument.dateipfad.ilike("%.png") | Dokument.dateipfad.ilike("%.gif")
        ).all()

        if dokumente:
            for dok in dokumente[:10]:
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"📷 {dok.original_dateiname}")

                with col2:
                    if st.button("Importieren", key=f"imp_{dok.id}"):
                        service = SchadensbilderService(db)
                        bild = service.importiere_von_dokument(dok.id)
                        if bild:
                            st.success("Bild importiert!")
                            st.rerun()
        else:
            st.info("Keine Bilddokumente gefunden")


def _render_statistik(projekt_id: int):
    """Galerie-Statistik"""
    st.subheader("Galerie-Statistik")

    with get_session() as db:
        service = SchadensbilderService(db)
        stats = service.galerie_statistik(projekt_id)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Anzahl Bilder", stats['anzahl_bilder'])

        with col2:
            st.metric("Gesamtgröße", stats['gesamt_groesse_anzeige'])

        with col3:
            st.metric("Vorher/Nachher-Paare", stats['vorher_nachher_paare'])

        if stats['nach_kategorie']:
            st.markdown("### Bilder pro Kategorie")

            for kat, anzahl in stats['nach_kategorie'].items():
                st.write(f"- {_kategorie_anzeige(BildKategorie(kat))}: {anzahl}")


def _kategorie_anzeige(kategorie: BildKategorie) -> str:
    """Gibt den Anzeigetext für eine Kategorie zurück"""
    return {
        BildKategorie.UNFALLORT: "📍 Unfallort",
        BildKategorie.FAHRZEUG_VORNE: "🚗 Fahrzeug vorne",
        BildKategorie.FAHRZEUG_HINTEN: "🚗 Fahrzeug hinten",
        BildKategorie.FAHRZEUG_LINKS: "🚗 Fahrzeug links",
        BildKategorie.FAHRZEUG_RECHTS: "🚗 Fahrzeug rechts",
        BildKategorie.SCHADEN_DETAIL: "🔍 Schadensdetail",
        BildKategorie.INNENRAUM: "🪑 Innenraum",
        BildKategorie.MOTORRAUM: "⚙️ Motorraum",
        BildKategorie.VORHER: "⬅️ Vorher",
        BildKategorie.NACHHER: "➡️ Nachher",
        BildKategorie.REPARATUR: "🔧 Reparatur",
        BildKategorie.GUTACHTEN: "📋 Gutachten",
        BildKategorie.SONSTIGES: "📷 Sonstiges"
    }.get(kategorie, "📷 Bild")
