"""
PDF-Fallbericht Generator UI-Seite
Generierung von umfassenden Fallberichten
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.fallbericht import FallberichtService, BerichtTyp, BerichtFormat, Fallbericht


def render_fallbericht():
    """Rendert die Fallbericht-Seite"""
    st.title("📄 Fallbericht Generator")

    st.info("""
    Generieren Sie umfassende Berichte für Ihre Schadensfälle.
    Wählen Sie den Berichtstyp und die gewünschten Abschnitte.
    """)

    # Tabs
    tab1, tab2 = st.tabs(["Neuer Bericht", "Generierte Berichte"])

    with tab1:
        _render_neuer_bericht()

    with tab2:
        _render_generierte_berichte()


def _render_neuer_bericht():
    """Neuen Bericht erstellen"""
    st.subheader("Neuen Bericht generieren")

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

            bericht_typ = st.selectbox(
                "Berichtstyp",
                [t.value for t in BerichtTyp],
                format_func=lambda x: {
                    'VOLLSTAENDIG': '📚 Vollständiger Bericht',
                    'ZUSAMMENFASSUNG': '📋 Zusammenfassung',
                    'KOSTENAUFSTELLUNG': '💶 Kostenaufstellung',
                    'TIMELINE': '📅 Timeline/Verlauf',
                    'VERSICHERUNG': '🏢 Versicherungsbericht',
                    'GERICHT': '⚖️ Gerichtsbericht',
                    'MANDANT': '👤 Mandanteninformation'
                }.get(x, x)
            )

        with col2:
            format_typ = st.selectbox(
                "Ausgabeformat",
                [f.value for f in BerichtFormat],
                format_func=lambda x: {
                    'PDF': '📄 PDF',
                    'HTML': '🌐 HTML',
                    'DOCX': '📝 Word (DOCX)'
                }.get(x, x)
            )

        # Abschnitte auswählen
        st.markdown("### Abschnitte auswählen")

        service = FallberichtService(db)

        col_a1, col_a2, col_a3 = st.columns(3)

        abschnitte = []

        with col_a1:
            if st.checkbox("Stammdaten", value=True):
                abschnitte.append('stammdaten')
            if st.checkbox("Unfallhergang", value=True):
                abschnitte.append('unfallhergang')
            if st.checkbox("Beteiligte", value=True):
                abschnitte.append('beteiligte')
            if st.checkbox("Fahrzeugdaten"):
                abschnitte.append('fahrzeuge')
            if st.checkbox("Schäden"):
                abschnitte.append('schaeden')

        with col_a2:
            if st.checkbox("Kostenaufstellung", value=True):
                abschnitte.append('kosten')
            if st.checkbox("Forderungen", value=True):
                abschnitte.append('forderungen')
            if st.checkbox("Zahlungen"):
                abschnitte.append('zahlungen')
            if st.checkbox("Dokumentenliste"):
                abschnitte.append('dokumente')

        with col_a3:
            if st.checkbox("Timeline/Verlauf"):
                abschnitte.append('timeline')
            if st.checkbox("Korrespondenz"):
                abschnitte.append('korrespondenz')
            if st.checkbox("Fristen"):
                abschnitte.append('fristen')
            if st.checkbox("Notizen"):
                abschnitte.append('notizen')

        if st.button("📊 Bericht generieren", type="primary"):
            if not abschnitte:
                st.error("Bitte mindestens einen Abschnitt auswählen")
                return

            with st.spinner("Generiere Bericht..."):
                bericht = service.bericht_generieren(
                    projekt_id=projekt_id,
                    bericht_typ=BerichtTyp(bericht_typ),
                    abschnitte=abschnitte,
                    format=BerichtFormat(format_typ)
                )

                db.commit()

            st.success(f"Bericht '{bericht.dateiname}' generiert!")

            # HTML-Vorschau anzeigen
            if format_typ == 'HTML':
                html_content = service.generiere_html(bericht.id)

                st.markdown("### Vorschau")
                st.components.v1.html(html_content, height=600, scrolling=True)

                # Download
                st.download_button(
                    "📥 HTML herunterladen",
                    data=html_content,
                    file_name=bericht.dateiname.replace('.pdf', '.html'),
                    mime="text/html"
                )

            elif format_typ == 'PDF':
                st.info("PDF-Export: In der Vollversion würde hier eine PDF-Datei generiert werden.")

                # HTML als Fallback
                html_content = service.generiere_html(bericht.id)
                st.download_button(
                    "📥 Als HTML herunterladen",
                    data=html_content,
                    file_name=bericht.dateiname.replace('.pdf', '.html'),
                    mime="text/html"
                )


def _render_generierte_berichte():
    """Liste generierter Berichte"""
    st.subheader("Generierte Berichte")

    with get_session() as db:
        berichte = db.query(Fallbericht).order_by(
            Fallbericht.generiert_am.desc()
        ).limit(50).all()

        if not berichte:
            st.info("Noch keine Berichte generiert")
            return

        for bericht in berichte:
            typ_icon = {
                BerichtTyp.VOLLSTAENDIG: "📚",
                BerichtTyp.ZUSAMMENFASSUNG: "📋",
                BerichtTyp.KOSTENAUFSTELLUNG: "💶",
                BerichtTyp.TIMELINE: "📅",
                BerichtTyp.VERSICHERUNG: "🏢",
                BerichtTyp.GERICHT: "⚖️",
                BerichtTyp.MANDANT: "👤"
            }.get(bericht.bericht_typ, "📄")

            with st.expander(
                f"{typ_icon} {bericht.bezeichnung} - "
                f"{bericht.generiert_am.strftime('%d.%m.%Y %H:%M') if bericht.generiert_am else '-'}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Typ:** {bericht.bericht_typ.value if bericht.bericht_typ else '-'}")
                    st.write(f"**Format:** {bericht.format.value if bericht.format else '-'}")
                    st.write(f"**Projekt:** {bericht.projekt_id}")

                with col2:
                    st.write(f"**Dateiname:** {bericht.dateiname}")
                    st.write(f"**Abschnitte:** {len(bericht.enthaltene_abschnitte)}")

                # Abschnitte anzeigen
                if bericht.enthaltene_abschnitte:
                    st.caption(f"Enthält: {', '.join(bericht.enthaltene_abschnitte)}")

                # Erneut generieren
                service = FallberichtService(db)

                if st.button("🔄 Erneut generieren", key=f"regen_{bericht.id}"):
                    html_content = service.generiere_html(bericht.id)
                    st.download_button(
                        "📥 Herunterladen",
                        data=html_content,
                        file_name=bericht.dateiname.replace('.pdf', '.html'),
                        mime="text/html",
                        key=f"dl_{bericht.id}"
                    )
