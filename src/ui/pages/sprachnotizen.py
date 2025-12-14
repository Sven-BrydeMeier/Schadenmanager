"""
Sprachnotizen UI-Seite
Audio-Aufnahme und Transkription
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.sprachnotizen import (
    SprachnotizService, SprachnotizKategorie, SprachnotizStatus,
    Sprachnotiz, DIKTAT_VORLAGEN
)


def render_sprachnotizen():
    """Rendert die Sprachnotizen-Seite"""
    st.title("🎤 Sprachnotizen")

    st.info("""
    Erstellen Sie Sprachnotizen für Telefonate, Besprechungen und Diktate.
    Die Notizen können transkribiert und durchsucht werden.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Neue Notiz", "Alle Notizen", "Suche"
    ])

    with tab1:
        _render_neue_notiz()

    with tab2:
        _render_alle_notizen()

    with tab3:
        _render_suche()


def _render_neue_notiz():
    """Neue Sprachnotiz erstellen"""
    st.subheader("Neue Notiz erstellen")

    with get_session() as db:
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        col1, col2 = st.columns(2)

        with col1:
            projekt_options = {
                p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
                for p in projekte
            }
            projekt_id = st.selectbox(
                "Projekt",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, "")
            )

            titel = st.text_input("Titel", placeholder="z.B. Telefonat mit Versicherung")

        with col2:
            kategorie = st.selectbox(
                "Kategorie",
                [k.value for k in SprachnotizKategorie],
                format_func=lambda x: {
                    'TELEFONAT': '📞 Telefonat',
                    'BESPRECHUNG': '👥 Besprechung',
                    'DIKTAT': '📝 Diktat',
                    'NOTIZ': '📌 Notiz',
                    'ZEUGENBEFRAGUNG': '🎤 Zeugenbefragung',
                    'ORTSTERMIN': '📍 Ortstermin',
                    'SONSTIGE': '📋 Sonstige'
                }.get(x, x)
            )

            tags_input = st.text_input(
                "Tags (kommagetrennt)",
                placeholder="wichtig, nachfassen, dringend"
            )

        # Audio-Aufnahme (Web-Browser API)
        st.markdown("### 🎙️ Audio-Aufnahme")

        st.warning("""
        **Hinweis:** Die Audio-Aufnahme im Browser erfordert Mikrofon-Zugriff.
        In der aktuellen Version können Sie stattdessen Text direkt eingeben.
        """)

        # Text-Eingabe als Alternative
        st.markdown("### 📝 Text-Eingabe")

        # Vorlage auswählen
        vorlage_option = st.selectbox(
            "Vorlage verwenden",
            ["Keine Vorlage"] + list(DIKTAT_VORLAGEN.keys()),
            format_func=lambda x: {
                'telefonat_eingang': '📞 Telefonat',
                'zeugenbefragung': '🎤 Zeugenbefragung',
                'ortstermin': '📍 Ortstermin',
                'besprechung': '👥 Besprechung'
            }.get(x, x)
        )

        default_text = ""
        if vorlage_option != "Keine Vorlage":
            default_text = DIKTAT_VORLAGEN.get(vorlage_option, "")

        notiz_text = st.text_area(
            "Notiztext",
            value=default_text,
            height=300,
            placeholder="Geben Sie hier Ihre Notiz ein..."
        )

        if st.button("💾 Notiz speichern", type="primary"):
            if not titel:
                st.error("Bitte Titel eingeben")
                return

            if not notiz_text:
                st.error("Bitte Text eingeben")
                return

            service = SprachnotizService(db)

            tags = []
            if tags_input:
                tags = [t.strip() for t in tags_input.split(",")]

            notiz = service.text_zu_notiz_konvertieren(
                projekt_id=projekt_id,
                titel=titel,
                text=notiz_text,
                kategorie=SprachnotizKategorie(kategorie)
            )

            if tags:
                notiz.tags = tags

            db.commit()

            st.success(f"Notiz '{titel}' gespeichert!")


def _render_alle_notizen():
    """Alle Sprachnotizen anzeigen"""
    st.subheader("Alle Notizen")

    with get_session() as db:
        # Filter
        col1, col2 = st.columns(2)

        with col1:
            kategorie_filter = st.selectbox(
                "Kategorie filtern",
                ["Alle"] + [k.value for k in SprachnotizKategorie],
                key="filter_kat"
            )

        with col2:
            from src.models import UnfallProjekt
            projekte = db.query(UnfallProjekt).order_by(
                UnfallProjekt.erstellt_am.desc()
            ).limit(50).all()

            projekt_options = {0: "Alle Projekte"}
            projekt_options.update({
                p.id: f"{p.projektnummer}"
                for p in projekte
            })

            projekt_filter = st.selectbox(
                "Projekt filtern",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, ""),
                key="filter_proj"
            )

        # Notizen laden
        query = db.query(Sprachnotiz)

        if kategorie_filter != "Alle":
            query = query.filter(Sprachnotiz.kategorie == kategorie_filter)

        if projekt_filter > 0:
            query = query.filter(Sprachnotiz.projekt_id == projekt_filter)

        notizen = query.order_by(Sprachnotiz.aufgenommen_am.desc()).limit(50).all()

        if not notizen:
            st.info("Keine Notizen gefunden")
            return

        # Statistik
        service = SprachnotizService(db)
        statistik = service.statistik()

        col_s1, col_s2, col_s3 = st.columns(3)

        with col_s1:
            st.metric("Gesamt", statistik['gesamt'])
        with col_s2:
            st.metric("Transkribiert", statistik['transkribiert'])
        with col_s3:
            st.metric("Gesamtdauer", f"{statistik['gesamt_dauer_minuten']} Min.")

        st.markdown("---")

        for notiz in notizen:
            kategorie_icon = {
                SprachnotizKategorie.TELEFONAT: "📞",
                SprachnotizKategorie.BESPRECHUNG: "👥",
                SprachnotizKategorie.DIKTAT: "📝",
                SprachnotizKategorie.NOTIZ: "📌",
                SprachnotizKategorie.ZEUGENBEFRAGUNG: "🎤",
                SprachnotizKategorie.ORTSTERMIN: "📍",
                SprachnotizKategorie.SONSTIGE: "📋"
            }.get(notiz.kategorie, "📌")

            with st.expander(
                f"{kategorie_icon} {notiz.titel} - "
                f"{notiz.aufgenommen_am.strftime('%d.%m.%Y %H:%M') if notiz.aufgenommen_am else '-'}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Projekt:** {notiz.projekt_id}")
                    st.write(f"**Kategorie:** {notiz.kategorie.value if notiz.kategorie else '-'}")
                    st.write(f"**Status:** {notiz.status.value if notiz.status else '-'}")

                with col2:
                    if notiz.dauer_sekunden:
                        st.write(f"**Dauer:** {notiz.dauer_anzeige}")
                    if notiz.tags:
                        st.write(f"**Tags:** {', '.join(notiz.tags)}")

                st.markdown("**Text:**")
                st.text_area(
                    "Inhalt",
                    value=notiz.finaler_text,
                    height=150,
                    disabled=True,
                    key=f"text_{notiz.id}"
                )

                # Bearbeiten
                if st.checkbox("Bearbeiten", key=f"edit_{notiz.id}"):
                    neuer_text = st.text_area(
                        "Text bearbeiten",
                        value=notiz.finaler_text,
                        height=150,
                        key=f"edit_text_{notiz.id}"
                    )

                    if st.button("💾 Speichern", key=f"save_{notiz.id}"):
                        service.text_bearbeiten(notiz.id, neuer_text, 1)
                        db.commit()
                        st.success("Gespeichert!")
                        st.rerun()


def _render_suche():
    """Suche in Notizen"""
    st.subheader("Suche in Notizen")

    suchbegriff = st.text_input("Suchbegriff", placeholder="Nach Text suchen...")

    if suchbegriff:
        with get_session() as db:
            service = SprachnotizService(db)
            ergebnisse = service.suche_in_transkriptionen(suchbegriff)

            if ergebnisse:
                st.success(f"{len(ergebnisse)} Ergebnis(se) gefunden")

                for notiz in ergebnisse:
                    with st.expander(f"📝 {notiz.titel}"):
                        st.write(f"**Projekt:** {notiz.projekt_id}")
                        st.write(f"**Datum:** {notiz.aufgenommen_am.strftime('%d.%m.%Y') if notiz.aufgenommen_am else '-'}")

                        # Text mit Hervorhebung
                        text = notiz.finaler_text
                        if text:
                            # Einfache Hervorhebung
                            highlighted = text.replace(
                                suchbegriff,
                                f"**{suchbegriff}**"
                            )
                            st.markdown(highlighted[:500] + "..." if len(highlighted) > 500 else highlighted)
            else:
                st.info("Keine Ergebnisse gefunden")
