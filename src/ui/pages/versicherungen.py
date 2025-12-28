"""
Versicherungsdatenbank UI-Seite
Kontaktdaten aller deutschen Versicherungen
"""
import streamlit as st

from src.config.database import get_session
from src.services.versicherungen import VersicherungService, Versicherung
from src.ui.pages.login import get_current_user_role


def render_versicherungen():
    """Rendert die Versicherungsdatenbank-Seite"""
    st.title("🏢 Versicherungsdatenbank")

    # Rolle prüfen für Zentralruf-Tab
    rolle = get_current_user_role()

    # Tabs - Zentralruf nur für Anwalt/Admin
    if rolle in ["ANWALT", "ADMIN"]:
        tab1, tab2, tab3, tab4 = st.tabs([
            "🔍 Zentralruf", "Suche", "Alle Versicherungen", "Neue Versicherung"
        ])

        with tab1:
            _render_zentralruf()

        with tab2:
            _render_suche()

        with tab3:
            _render_alle_versicherungen()

        with tab4:
            _render_neue_versicherung()
    else:
        tab1, tab2, tab3 = st.tabs([
            "Suche", "Alle Versicherungen", "Neue Versicherung"
        ])

        with tab1:
            _render_suche()

        with tab2:
            _render_alle_versicherungen()

        with tab3:
            _render_neue_versicherung()


def _render_zentralruf():
    """Zentralruf der Autoversicherer - Versicherungsabfrage"""
    st.subheader("🔍 Zentralruf der Autoversicherer")

    st.markdown("""
    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; border-left: 4px solid #0066cc; margin-bottom: 20px;">
        <strong>ℹ️ Über den Zentralruf</strong><br>
        Der Zentralruf der Autoversicherer ermöglicht die Ermittlung der gegnerischen
        Kfz-Haftpflichtversicherung anhand des Kennzeichens und Unfalldatums.<br>
        <strong>Telefon:</strong> 0800 250 260 0 (kostenlos)<br>
        <strong>Online:</strong> www.zentralruf.de
    </div>
    """, unsafe_allow_html=True)

    # Aktives Projekt laden falls vorhanden
    aktives_projekt_id = st.session_state.get("aktives_projekt_id")
    projekt_daten = None

    if aktives_projekt_id:
        try:
            from src.models import UnfallProjekt
            with get_session() as db:
                projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == aktives_projekt_id).first()
                if projekt:
                    projekt_daten = {
                        'kennzeichen': projekt.kfz_gegner or '',
                        'unfalldatum': projekt.datum_unfall.strftime('%d.%m.%Y') if projekt.datum_unfall else '',
                        'unfallort': projekt.ort_unfall or ''
                    }
                    st.info(f"📁 Daten aus Projekt: {projekt.aktenzeichen}")
        except Exception:
            pass

    st.markdown("### Daten für Zentralruf-Anfrage")

    col1, col2 = st.columns(2)

    with col1:
        # Kennzeichen
        default_kz = projekt_daten.get('kennzeichen', '') if projekt_daten else ''
        kennzeichen = st.text_input(
            "🚗 Kennzeichen des Unfallgegners *",
            value=default_kz,
            placeholder="z.B. B-AB 1234",
            help="Das Kennzeichen des gegnerischen Fahrzeugs"
        )

        # Unfalldatum
        default_datum = projekt_daten.get('unfalldatum', '') if projekt_daten else ''
        unfalldatum = st.text_input(
            "📅 Unfalldatum *",
            value=default_datum,
            placeholder="z.B. 28.12.2025",
            help="Datum des Unfalls im Format TT.MM.JJJJ"
        )

    with col2:
        # Unfallort (optional)
        default_ort = projekt_daten.get('unfallort', '') if projekt_daten else ''
        unfallort = st.text_input(
            "📍 Unfallort",
            value=default_ort,
            placeholder="z.B. Berlin, Hauptstraße",
            help="Ort des Unfalls (optional, aber hilfreich)"
        )

        # Unfallland
        unfallland = st.selectbox(
            "🌍 Unfallland",
            ["Deutschland", "Österreich", "Schweiz", "Andere EU-Länder"],
            help="In welchem Land hat sich der Unfall ereignet?"
        )

    st.markdown("---")

    # Kopierbereich
    st.markdown("### 📋 Daten zum Kopieren")

    if kennzeichen or unfalldatum:
        col_copy1, col_copy2, col_copy3 = st.columns(3)

        with col_copy1:
            st.text_input("Kennzeichen:", value=kennzeichen, key="copy_kz", disabled=True)
            if kennzeichen:
                st.caption("📋 Markieren und kopieren (Strg+C)")

        with col_copy2:
            st.text_input("Unfalldatum:", value=unfalldatum, key="copy_datum", disabled=True)
            if unfalldatum:
                st.caption("📋 Markieren und kopieren (Strg+C)")

        with col_copy3:
            st.text_input("Unfallort:", value=unfallort, key="copy_ort", disabled=True)
            if unfallort:
                st.caption("📋 Markieren und kopieren (Strg+C)")

        # Alle Daten zusammen
        alle_daten = f"Kennzeichen: {kennzeichen}\nUnfalldatum: {unfalldatum}\nUnfallort: {unfallort}"
        st.text_area("Alle Daten:", value=alle_daten, height=100, key="copy_alle")

    st.markdown("---")

    # Buttons
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        # Zentralruf Website öffnen
        st.markdown("""
        <a href="https://www.zentralruf.de/online-anfrage/anfrageformular" target="_blank"
           style="display: inline-block; background-color: #0066cc; color: white;
                  padding: 12px 24px; border-radius: 8px; text-decoration: none;
                  font-weight: bold; width: 100%; text-align: center;">
            🔍 Zentralruf.de öffnen
        </a>
        """, unsafe_allow_html=True)

    with col_btn2:
        # Telefonische Anfrage
        st.markdown("""
        <a href="tel:08002502600"
           style="display: inline-block; background-color: #28a745; color: white;
                  padding: 12px 24px; border-radius: 8px; text-decoration: none;
                  font-weight: bold; width: 100%; text-align: center;">
            📞 0800 250 260 0 anrufen
        </a>
        """, unsafe_allow_html=True)

    # Anleitung
    with st.expander("📖 Anleitung zur Nutzung"):
        st.markdown("""
        **So nutzen Sie den Zentralruf:**

        1. **Daten oben eingeben** oder aus dem aktiven Projekt übernehmen
        2. **"Zentralruf.de öffnen"** klicken - die Website öffnet sich in einem neuen Tab
        3. **Daten kopieren** und in das Online-Formular einfügen:
           - Kennzeichen
           - Unfalldatum
           - Ggf. Unfallort und -land
        4. **Anfrage absenden** - Sie erhalten die Versicherungsdaten

        **Alternative: Telefonische Anfrage**
        - Rufen Sie **0800 250 260 0** an (kostenlos)
        - Halten Sie Kennzeichen und Unfalldatum bereit
        - Die Auskunft erfolgt sofort

        **Hinweis:**
        - Der Zentralruf ist Mo-Fr 8-20 Uhr erreichbar
        - Die Online-Anfrage ist 24/7 möglich
        - Die Auskunft ist kostenlos
        """)

    # Ergebnis speichern
    st.markdown("---")
    st.markdown("### 💾 Ergebnis eintragen")

    with st.form("zentralruf_ergebnis"):
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            vers_name = st.text_input("Versicherungsname", placeholder="z.B. Allianz Versicherungs-AG")
            vers_vunr = st.text_input("VUNR", placeholder="z.B. 1001")

        with col_e2:
            vers_schadennr = st.text_input("Schadennummer (falls bekannt)", placeholder="")
            vers_telefon = st.text_input("Schaden-Hotline", placeholder="")

        if st.form_submit_button("✓ Im Projekt speichern", type="primary"):
            if vers_name and aktives_projekt_id:
                try:
                    from src.models import UnfallProjekt
                    with get_session() as db:
                        projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == aktives_projekt_id).first()
                        if projekt:
                            projekt.versicherung_gegner = vers_name
                            if vers_schadennr:
                                projekt.schadennummer_gegner = vers_schadennr
                            db.commit()
                            st.success(f"✓ Versicherungsdaten im Projekt gespeichert!")
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
            elif not aktives_projekt_id:
                st.warning("Kein aktives Projekt ausgewählt. Bitte wählen Sie zuerst ein Projekt.")
            else:
                st.warning("Bitte mindestens den Versicherungsnamen eingeben.")


def _render_suche():
    """Versicherungssuche"""
    st.subheader("Versicherung suchen")

    suchbegriff = st.text_input(
        "Suche nach Name, Kurzname oder VUNR",
        placeholder="z.B. Allianz, HUK, 1000..."
    )

    if suchbegriff:
        with get_session() as db:
            service = VersicherungService(db)
            ergebnisse = service.suche_versicherung(suchbegriff)

            if ergebnisse:
                st.write(f"**{len(ergebnisse)} Ergebnis(se):**")

                for vs in ergebnisse:
                    _render_versicherung_card(vs)
            else:
                st.info("Keine Versicherung gefunden")

                # Standard-Daten initialisieren anbieten
                if st.button("Standard-Versicherungen laden"):
                    service.initialisiere_standard_versicherungen()
                    st.success("Standard-Versicherungen wurden geladen")
                    st.rerun()


def _render_alle_versicherungen():
    """Liste aller Versicherungen"""
    st.subheader("Alle Versicherungen")

    with get_session() as db:
        service = VersicherungService(db)
        versicherungen = service.alle_versicherungen()

        if not versicherungen:
            st.info("Keine Versicherungen in der Datenbank")

            if st.button("Standard-Versicherungen laden", type="primary"):
                service.initialisiere_standard_versicherungen()
                st.success("20+ Standard-Versicherungen wurden geladen!")
                st.rerun()
            return

        # Filter
        col1, col2 = st.columns(2)

        with col1:
            filter_text = st.text_input("Filter", placeholder="Name filtern...")

        with col2:
            sortierung = st.selectbox(
                "Sortierung",
                ["Name A-Z", "Name Z-A", "VUNR"]
            )

        # Filtern
        if filter_text:
            versicherungen = [
                v for v in versicherungen
                if filter_text.lower() in v.name.lower()
            ]

        # Sortieren
        if sortierung == "Name Z-A":
            versicherungen = sorted(versicherungen, key=lambda x: x.name, reverse=True)
        elif sortierung == "VUNR":
            versicherungen = sorted(versicherungen, key=lambda x: x.vunr or "9999")

        st.write(f"**{len(versicherungen)} Versicherungen**")

        for vs in versicherungen:
            _render_versicherung_card(vs)


def _render_versicherung_card(vs: Versicherung):
    """Zeigt eine Versicherungs-Karte"""
    with st.expander(f"🏢 {vs.name} ({vs.kurzname or '-'})", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Kontaktdaten**")
            st.write(f"**VUNR:** {vs.vunr or '-'}")
            st.write(f"**Adresse:**")
            st.write(vs.vollstaendige_adresse)

            if vs.telefon:
                st.write(f"**Telefon:** {vs.telefon}")
            if vs.fax:
                st.write(f"**Fax:** {vs.fax}")
            if vs.email:
                st.write(f"**E-Mail:** {vs.email}")
            if vs.website:
                st.write(f"**Website:** {vs.website}")

        with col2:
            st.markdown("**Schadenhotline**")
            if vs.schaden_hotline:
                st.write(f"📞 **Hotline:** {vs.schaden_hotline}")
            if vs.schaden_email:
                st.write(f"📧 **E-Mail:** {vs.schaden_email}")
            if vs.schaden_fax:
                st.write(f"📠 **Fax:** {vs.schaden_fax}")
            if vs.schaden_portal:
                st.write(f"🌐 **Portal:** {vs.schaden_portal}")

            if vs.regulierer_name:
                st.markdown("**Regulierungsbeauftragter**")
                st.write(vs.regulierer_name)
                if vs.regulierer_telefon:
                    st.write(f"📞 {vs.regulierer_telefon}")
                if vs.regulierer_email:
                    st.write(f"📧 {vs.regulierer_email}")

        # Aktionen
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            # Adresse für Anschreiben kopieren
            anschreiben = f"{vs.name}\n{vs.adresse}\n{vs.plz} {vs.ort}"
            st.text_area("Für Anschreiben:", value=anschreiben, height=100, key=f"addr_{vs.id}")

        with col_b:
            # Schaden-Kontakt
            if vs.schaden_hotline or vs.schaden_email:
                st.markdown("**Schnellkontakt Schaden:**")
                if vs.schaden_hotline:
                    st.code(vs.schaden_hotline)
                if vs.schaden_email:
                    st.code(vs.schaden_email)

        with col_c:
            if st.button("✏️ Bearbeiten", key=f"edit_{vs.id}"):
                st.session_state["edit_versicherung_id"] = vs.id

            if vs.notizen:
                st.info(vs.notizen)


def _render_neue_versicherung():
    """Formular für neue Versicherung"""
    st.subheader("Neue Versicherung hinzufügen")

    with st.form("neue_versicherung"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Stammdaten**")
            name = st.text_input("Name *", placeholder="z.B. Muster Versicherung AG")
            kurzname = st.text_input("Kurzname", placeholder="z.B. Muster")
            vunr = st.text_input("VUNR", placeholder="z.B. 1234")

            st.markdown("**Adresse**")
            adresse = st.text_input("Straße", placeholder="Musterstraße 1")
            col_plz, col_ort = st.columns([1, 2])
            with col_plz:
                plz = st.text_input("PLZ", placeholder="12345")
            with col_ort:
                ort = st.text_input("Ort", placeholder="Musterstadt")

        with col2:
            st.markdown("**Kontakt**")
            telefon = st.text_input("Telefon", placeholder="+49 123 456-0")
            fax = st.text_input("Fax")
            email = st.text_input("E-Mail")
            website = st.text_input("Website")

            st.markdown("**Schadenhotline**")
            schaden_hotline = st.text_input("Schaden-Hotline")
            schaden_email = st.text_input("Schaden-E-Mail")
            schaden_portal = st.text_input("Schaden-Portal (URL)")

        notizen = st.text_area("Notizen", height=100)

        submitted = st.form_submit_button("Versicherung speichern", type="primary")

        if submitted:
            if not name:
                st.error("Bitte Name eingeben")
            else:
                with get_session() as db:
                    service = VersicherungService(db)

                    vs = service.versicherung_erstellen(
                        name=name,
                        kurzname=kurzname,
                        vunr=vunr,
                        adresse=adresse,
                        plz=plz,
                        ort=ort,
                        telefon=telefon,
                        fax=fax,
                        email=email,
                        website=website,
                        schaden_hotline=schaden_hotline,
                        schaden_email=schaden_email,
                        schaden_portal=schaden_portal,
                        notizen=notizen
                    )

                    st.success(f"Versicherung '{vs.name}' wurde angelegt!")
