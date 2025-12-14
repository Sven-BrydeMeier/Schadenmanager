"""
Versicherungsdatenbank UI-Seite
Kontaktdaten aller deutschen Versicherungen
"""
import streamlit as st

from src.config.database import get_session
from src.services.versicherungen import VersicherungService, Versicherung


def render_versicherungen():
    """Rendert die Versicherungsdatenbank-Seite"""
    st.title("🏢 Versicherungsdatenbank")

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Suche", "Alle Versicherungen", "Neue Versicherung"
    ])

    with tab1:
        _render_suche()

    with tab2:
        _render_alle_versicherungen()

    with tab3:
        _render_neue_versicherung()


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
