"""
Serienbriefe UI-Seite
Dokumentenvorlagen und Serienbriefe
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.serienbriefe import (
    SerienbriefeService, VorlageKategorie, VorlageFormat,
    Dokumentvorlage, GeneriertesDokument, STANDARD_VORLAGEN
)


def render_serienbriefe():
    """Rendert die Serienbriefe-Seite"""
    st.title("📝 Serienbriefe & Vorlagen")

    st.info("""
    Erstellen Sie Dokumentvorlagen mit Platzhaltern und generieren Sie
    Serienbriefe für mehrere Projekte.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Dokument erstellen", "Vorlagen verwalten", "Generierte Dokumente"
    ])

    with tab1:
        _render_dokument_erstellen()

    with tab2:
        _render_vorlagen_verwalten()

    with tab3:
        _render_generierte_dokumente()


def _render_dokument_erstellen():
    """Dokument aus Vorlage erstellen"""
    st.subheader("Dokument erstellen")

    with get_session() as db:
        service = SerienbriefeService(db)
        vorlagen = service.alle_vorlagen()

        if not vorlagen:
            st.warning("Keine Vorlagen vorhanden. Bitte zuerst Vorlagen erstellen.")

            if st.button("📥 Standard-Vorlagen importieren"):
                for v in STANDARD_VORLAGEN:
                    service.vorlage_erstellen(
                        bezeichnung=v['bezeichnung'],
                        inhalt_vorlage=v['inhalt'],
                        kategorie=v['kategorie'],
                        betreff_vorlage=v.get('betreff')
                    )
                db.commit()
                st.success("Standard-Vorlagen importiert!")
                st.rerun()
            return

        from src.models import UnfallProjekt
        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        col1, col2 = st.columns(2)

        with col1:
            vorlage_options = {
                v.id: f"{v.bezeichnung} ({v.kategorie.value if v.kategorie else '-'})"
                for v in vorlagen
            }
            vorlage_id = st.selectbox(
                "Vorlage auswählen",
                list(vorlage_options.keys()),
                format_func=lambda x: vorlage_options.get(x, "")
            )

        with col2:
            projekt_options = {
                p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
                for p in projekte
            }
            projekt_id = st.selectbox(
                "Projekt auswählen",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, "")
            )

        # Vorschau laden
        if vorlage_id and projekt_id:
            vorschau = service.generiere_vorschau(vorlage_id, projekt_id)

            st.markdown("### Vorschau")

            if vorschau.get('betreff'):
                st.write(f"**Betreff:** {vorschau['betreff']}")

            st.text_area(
                "Dokumentinhalt",
                value=vorschau.get('inhalt', ''),
                height=300,
                disabled=True
            )

            # Fehlende Platzhalter
            fehlende = vorschau.get('fehlende_platzhalter', [])
            if fehlende:
                st.warning(f"Fehlende Werte für: {', '.join(fehlende)}")

                st.markdown("### Fehlende Werte ergänzen")
                zusaetzliche_werte = {}
                for platzhalter in fehlende:
                    wert = st.text_input(f"{platzhalter}", key=f"ph_{platzhalter}")
                    if wert:
                        zusaetzliche_werte[platzhalter] = wert
            else:
                zusaetzliche_werte = {}

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("📄 Dokument generieren", type="primary"):
                    dokument = service.dokument_generieren(
                        vorlage_id=vorlage_id,
                        projekt_id=projekt_id,
                        werte=zusaetzliche_werte if zusaetzliche_werte else None
                    )
                    db.commit()

                    st.success("Dokument generiert!")

                    # Download anbieten
                    st.download_button(
                        "📥 Herunterladen",
                        data=dokument.inhalt,
                        file_name=f"{dokument.bezeichnung}.txt",
                        mime="text/plain"
                    )

            with col_btn2:
                # Serienbrief für mehrere Projekte
                if st.checkbox("Serienbrief (mehrere Projekte)"):
                    ausgewaehlte_projekte = st.multiselect(
                        "Projekte auswählen",
                        list(projekt_options.keys()),
                        format_func=lambda x: projekt_options.get(x, "")
                    )

                    if st.button("📚 Serienbriefe generieren"):
                        if ausgewaehlte_projekte:
                            dokumente = service.serienbrief_generieren(
                                vorlage_id=vorlage_id,
                                projekt_ids=ausgewaehlte_projekte
                            )
                            db.commit()
                            st.success(f"{len(dokumente)} Dokument(e) generiert!")


def _render_vorlagen_verwalten():
    """Vorlagen verwalten"""
    st.subheader("Vorlagen verwalten")

    with get_session() as db:
        service = SerienbriefeService(db)

        # Neue Vorlage erstellen
        with st.expander("➕ Neue Vorlage erstellen"):
            bezeichnung = st.text_input("Bezeichnung", key="new_bez")

            kategorie = st.selectbox(
                "Kategorie",
                [k.value for k in VorlageKategorie],
                format_func=lambda x: {
                    'ANSCHREIBEN': '📨 Anschreiben',
                    'MAHNUNG': '⚠️ Mahnung',
                    'ANFRAGE': '❓ Anfrage',
                    'MITTEILUNG': '📢 Mitteilung',
                    'VOLLMACHT': '✍️ Vollmacht',
                    'RECHNUNG': '🧾 Rechnung',
                    'KLAGE': '⚖️ Klage',
                    'VERGLEICH': '🤝 Vergleich',
                    'SONSTIGE': '📄 Sonstige'
                }.get(x, x)
            )

            betreff = st.text_input(
                "Betreff-Vorlage",
                placeholder="Schadenmeldung - Az. {{aktenzeichen}}"
            )

            inhalt = st.text_area(
                "Inhalt-Vorlage",
                height=300,
                placeholder="Verwenden Sie {{platzhalter}} für dynamische Inhalte"
            )

            st.markdown("### Verfügbare Platzhalter")
            platzhalter_text = ""
            for ph, beschr in service.STANDARD_PLATZHALTER.items():
                platzhalter_text += f"- `{ph}` - {beschr}\n"
            st.markdown(platzhalter_text)

            if st.button("💾 Vorlage speichern"):
                if bezeichnung and inhalt:
                    vorlage = service.vorlage_erstellen(
                        bezeichnung=bezeichnung,
                        inhalt_vorlage=inhalt,
                        kategorie=VorlageKategorie(kategorie),
                        betreff_vorlage=betreff if betreff else None
                    )
                    db.commit()
                    st.success("Vorlage erstellt!")
                    st.rerun()
                else:
                    st.error("Bitte Bezeichnung und Inhalt eingeben")

        st.markdown("---")

        # Vorhandene Vorlagen
        vorlagen = service.alle_vorlagen()

        if not vorlagen:
            st.info("Noch keine Vorlagen vorhanden")
            return

        for vorlage in vorlagen:
            kategorie_icon = {
                VorlageKategorie.ANSCHREIBEN: "📨",
                VorlageKategorie.MAHNUNG: "⚠️",
                VorlageKategorie.ANFRAGE: "❓",
                VorlageKategorie.VOLLMACHT: "✍️",
                VorlageKategorie.RECHNUNG: "🧾",
                VorlageKategorie.KLAGE: "⚖️",
                VorlageKategorie.VERGLEICH: "🤝",
                VorlageKategorie.SONSTIGE: "📄"
            }.get(vorlage.kategorie, "📄")

            with st.expander(f"{kategorie_icon} {vorlage.bezeichnung}"):
                st.write(f"**Kategorie:** {vorlage.kategorie.value if vorlage.kategorie else '-'}")
                st.write(f"**Betreff:** {vorlage.betreff_vorlage or '-'}")

                st.text_area(
                    "Inhalt",
                    value=vorlage.inhalt_vorlage,
                    height=200,
                    disabled=True,
                    key=f"vorl_{vorlage.id}"
                )

                if vorlage.platzhalter:
                    st.caption(f"Platzhalter: {', '.join(vorlage.platzhalter)}")

                col_a1, col_a2 = st.columns(2)

                with col_a1:
                    if st.button("🗑️ Löschen", key=f"del_{vorlage.id}"):
                        vorlage.aktiv = False
                        db.commit()
                        st.rerun()


def _render_generierte_dokumente():
    """Generierte Dokumente"""
    st.subheader("Generierte Dokumente")

    with get_session() as db:
        dokumente = db.query(GeneriertesDokument).order_by(
            GeneriertesDokument.erstellt_am.desc()
        ).limit(50).all()

        if not dokumente:
            st.info("Noch keine Dokumente generiert")
            return

        for dok in dokumente:
            versendet_icon = "✅" if dok.versendet else "📤"

            with st.expander(
                f"{versendet_icon} {dok.bezeichnung} - "
                f"{dok.erstellt_am.strftime('%d.%m.%Y %H:%M') if dok.erstellt_am else '-'}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Projekt:** {dok.projekt_id}")
                    st.write(f"**Betreff:** {dok.betreff or '-'}")

                with col2:
                    st.write(f"**Versendet:** {'Ja' if dok.versendet else 'Nein'}")
                    if dok.versendet:
                        st.write(f"**An:** {dok.versendet_an}")
                        st.write(f"**Am:** {dok.versendet_am.strftime('%d.%m.%Y') if dok.versendet_am else '-'}")

                st.text_area(
                    "Inhalt",
                    value=dok.inhalt or "",
                    height=200,
                    disabled=True,
                    key=f"dok_{dok.id}"
                )

                col_a1, col_a2 = st.columns(2)

                with col_a1:
                    st.download_button(
                        "📥 Herunterladen",
                        data=dok.inhalt or "",
                        file_name=f"{dok.bezeichnung}.txt",
                        mime="text/plain",
                        key=f"dl_{dok.id}"
                    )

                with col_a2:
                    if not dok.versendet:
                        empfaenger = st.text_input("Empfänger", key=f"emp_{dok.id}")
                        if st.button("📧 Als versendet markieren", key=f"send_{dok.id}"):
                            service = SerienbriefeService(db)
                            service.als_versendet_markieren(dok.id, empfaenger)
                            db.commit()
                            st.rerun()
