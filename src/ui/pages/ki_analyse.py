"""
KI-Textanalyse UI-Seite
Analyse von Gutachten und Kürzungsschreiben
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.ki_analyse import KIAnalyseService, AnalyseTyp, DokumentAnalyse


def render_ki_analyse():
    """Rendert die KI-Analyse-Seite"""
    st.title("🤖 KI-Textanalyse")

    st.info("""
    Analysieren Sie Gutachten, Kürzungsschreiben und andere Dokumente mit
    KI-Unterstützung. Automatische Extraktion von Beträgen, Argumenten und
    wichtigen Informationen.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Neue Analyse", "Analysen-Übersicht", "Textanalyse"
    ])

    with tab1:
        _render_neue_analyse()

    with tab2:
        _render_analysen_uebersicht()

    with tab3:
        _render_text_analyse()


def _render_neue_analyse():
    """Neue Dokumentenanalyse"""
    st.subheader("Dokument analysieren")

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
                "Projekt auswählen",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, "")
            )

        with col2:
            analyse_typ = st.selectbox(
                "Dokumententyp",
                [t.value for t in AnalyseTyp],
                format_func=lambda x: {
                    'GUTACHTEN': '📋 Gutachten',
                    'KUERZUNGSSCHREIBEN': '✂️ Kürzungsschreiben',
                    'RECHNUNG': '🧾 Rechnung',
                    'ANWALTSSCHREIBEN': '⚖️ Anwaltsschreiben',
                    'VERSICHERUNGSSCHREIBEN': '🏢 Versicherungsschreiben',
                    'URTEIL': '⚖️ Urteil/Beschluss',
                    'SONSTIGE': '📄 Sonstiges'
                }.get(x, x)
            )

        st.markdown("### Dokumenttext eingeben")

        dokument_text = st.text_area(
            "Text des Dokuments",
            height=300,
            placeholder="Fügen Sie hier den Text des zu analysierenden Dokuments ein..."
        )

        if st.button("🔍 Analysieren", type="primary"):
            if not dokument_text:
                st.error("Bitte geben Sie einen Text ein")
                return

            service = KIAnalyseService(db)

            with st.spinner("Analysiere Dokument..."):
                analyse = service.dokument_analysieren(
                    projekt_id=projekt_id,
                    dokument_text=dokument_text,
                    analyse_typ=AnalyseTyp(analyse_typ)
                )

            st.success("Analyse abgeschlossen!")

            # Ergebnisse anzeigen
            _zeige_analyse_ergebnis(analyse)


def _zeige_analyse_ergebnis(analyse: DokumentAnalyse):
    """Zeigt Analyseergebnis an"""
    st.markdown("---")
    st.markdown("### 📊 Analyseergebnis")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Konfidenz", f"{analyse.konfidenz_score or 0}%")
    with col2:
        st.metric("Extrahierte Beträge", len(analyse.extrahierte_betraege))
    with col3:
        st.metric("Keywords", len(analyse.keywords))

    # Zusammenfassung
    if analyse.zusammenfassung:
        st.markdown("#### Zusammenfassung")
        st.write(analyse.zusammenfassung)

    # Extrahierte Beträge
    if analyse.extrahierte_betraege:
        st.markdown("#### 💶 Extrahierte Beträge")
        for betrag in analyse.extrahierte_betraege:
            st.write(f"- **{betrag.get('beschreibung', 'Betrag')}**: {betrag.get('betrag', 0):,.2f} EUR")

    # Keywords
    if analyse.keywords:
        st.markdown("#### 🏷️ Erkannte Keywords")
        st.write(", ".join(analyse.keywords))

    # Strukturierte Daten
    if analyse.strukturierte_daten:
        st.markdown("#### 📋 Strukturierte Daten")
        st.json(analyse.strukturierte_daten)


def _render_analysen_uebersicht():
    """Übersicht aller Analysen"""
    st.subheader("Durchgeführte Analysen")

    with get_session() as db:
        analysen = db.query(DokumentAnalyse).order_by(
            DokumentAnalyse.analysiert_am.desc()
        ).limit(50).all()

        if not analysen:
            st.info("Noch keine Analysen durchgeführt")
            return

        for analyse in analysen:
            with st.expander(
                f"{analyse.analysiert_am.strftime('%d.%m.%Y %H:%M')} - "
                f"{analyse.analyse_typ.value if analyse.analyse_typ else 'Unbekannt'}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Projekt:** {analyse.projekt_id}")
                    st.write(f"**Typ:** {analyse.analyse_typ.value if analyse.analyse_typ else '-'}")
                    st.write(f"**Konfidenz:** {analyse.konfidenz_score or 0}%")

                with col2:
                    if analyse.zusammenfassung:
                        st.write("**Zusammenfassung:**")
                        st.write(analyse.zusammenfassung[:200] + "..." if len(analyse.zusammenfassung or "") > 200 else analyse.zusammenfassung)

                if analyse.extrahierte_betraege:
                    st.write("**Beträge:**")
                    for betrag in analyse.extrahierte_betraege:
                        st.write(f"- {betrag.get('beschreibung')}: {betrag.get('betrag', 0):,.2f} EUR")


def _render_text_analyse():
    """Direkte Textanalyse ohne Speicherung"""
    st.subheader("Schnelle Textanalyse")

    st.caption("Analysieren Sie Text ohne Zuordnung zu einem Projekt")

    text = st.text_area(
        "Text eingeben",
        height=200,
        placeholder="Text hier einfügen..."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💶 Beträge extrahieren"):
            if text:
                with get_session() as db:
                    service = KIAnalyseService(db)
                    betraege = service.extrahiere_betraege(text)

                    if betraege:
                        st.markdown("#### Gefundene Beträge:")
                        for b in betraege:
                            st.write(f"- **{b.get('beschreibung', 'Betrag')}**: {b.get('betrag', 0):,.2f} EUR")
                    else:
                        st.info("Keine Beträge gefunden")

    with col2:
        if st.button("🏷️ Keywords extrahieren"):
            if text:
                with get_session() as db:
                    service = KIAnalyseService(db)
                    keywords = service.extrahiere_keywords(text)

                    if keywords:
                        st.markdown("#### Gefundene Keywords:")
                        st.write(", ".join(keywords))
                    else:
                        st.info("Keine Keywords gefunden")
