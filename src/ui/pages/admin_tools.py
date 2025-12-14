"""
Admin-Tools - Workflow, Bankabgleich, Klassifizierung
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.workflow import get_workflow_service, WorkflowTyp, WORKFLOW_TEMPLATES
from src.services.bankabgleich import get_bankabgleich_service, ZuordnungsStatus
from src.services.dokumentenklassifizierung import get_klassifizierungs_service
from src.models import UnfallProjekt, Dokument, DokumentTyp
from src.ui.components import badge


def render_admin_tools():
    """Rendert die Admin-Tools Seite"""

    st.markdown("## Admin-Tools")

    rolle = st.session_state.get("user_role", "")

    if rolle not in ["ADMIN", "ANWALT"]:
        st.warning("Diese Seite ist nur für Administratoren und Anwälte zugänglich.")
        return

    # Tabs
    tabs = st.tabs([
        "Workflow-Templates",
        "Bank-Import",
        "Dokumenten-Klassifizierung"
    ])

    with tabs[0]:
        _render_workflow_tab()

    with tabs[1]:
        _render_bankabgleich_tab()

    with tabs[2]:
        _render_klassifizierung_tab()


def _render_workflow_tab():
    """Rendert den Workflow-Tab"""

    st.markdown("### Workflow-Templates")

    with get_session() as db:
        workflow_service = get_workflow_service(db)

        # Projekt auswählen
        aktives_projekt_id = st.session_state.get("aktives_projekt_id")

        if not aktives_projekt_id:
            # Alle Projekte anzeigen
            projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).all()

            if not projekte:
                st.info("Keine Projekte vorhanden.")
                return

            projekt_optionen = {
                f"{p.aktenzeichen or p.projektnummer} - {p.unfalldatum.strftime('%d.%m.%Y') if p.unfalldatum else 'Unbekannt'}": p.id
                for p in projekte
            }

            ausgewaehltes = st.selectbox("Projekt auswählen", list(projekt_optionen.keys()))
            projekt_id = projekt_optionen[ausgewaehltes]
        else:
            projekt_id = aktives_projekt_id
            projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == projekt_id).first()
            st.info(f"Aktives Projekt: {projekt.aktenzeichen or projekt.projektnummer}")

        st.markdown("---")

        # Verfügbare Workflows anzeigen
        st.markdown("#### Verfügbare Workflow-Templates")

        col1, col2 = st.columns(2)

        workflows = workflow_service.get_verfuegbare_workflows()

        for i, (typ, info) in enumerate(workflows.items()):
            with col1 if i % 2 == 0 else col2:
                with st.container():
                    st.markdown(f"**{info['name']}**")
                    st.caption(info['beschreibung'])
                    st.caption(f"Meilensteine: {info['anzahl_meilensteine']}")

                    if st.button("Anwenden", key=f"apply_wf_{typ}"):
                        user_id = st.session_state.get("user_id")
                        erfolg, nachricht, meilensteine = workflow_service.workflow_anwenden(
                            projekt_id=projekt_id,
                            workflow_typ=WorkflowTyp(typ),
                            user_id=user_id
                        )

                        if erfolg:
                            st.success(nachricht)
                        else:
                            st.error(nachricht)

                    st.markdown("---")

        # Aktueller Fortschritt
        st.markdown("#### Projekt-Fortschritt")

        fortschritt = workflow_service.workflow_fortschritt(projekt_id)

        if fortschritt["gesamt"] > 0:
            st.progress(fortschritt["prozent"] / 100)
            st.caption(f"{fortschritt['erledigt']} von {fortschritt['gesamt']} Meilensteinen abgeschlossen ({fortschritt['prozent']}%)")

            if fortschritt["naechster"]:
                st.markdown(f"**Nächster Meilenstein:** {fortschritt['naechster'].titel}")
        else:
            st.info("Noch keine Meilensteine definiert. Wenden Sie einen Workflow an.")


def _render_bankabgleich_tab():
    """Rendert den Bankabgleich-Tab"""

    st.markdown("### Bank-Import & Zahlungsabgleich")

    with get_session() as db:
        bankabgleich = get_bankabgleich_service(db)

        # Statistik
        stats = bankabgleich.get_statistik()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Gesamt gefordert", f"{stats['gesamt_gefordert']:,.2f} EUR")

        with col2:
            st.metric("Erstattet", f"{stats['gesamt_erstattet']:,.2f} EUR")

        with col3:
            st.metric("Offen", f"{stats['offen']:,.2f} EUR")

        st.markdown("---")

        # CSV-Import
        st.markdown("#### Kontoauszug importieren")

        col1, col2 = st.columns(2)

        with col1:
            bank_format = st.selectbox(
                "Bank-Format",
                ["standard", "sparkasse", "volksbank", "deutsche_bank"],
                format_func=lambda x: {
                    "standard": "Standard (CSV)",
                    "sparkasse": "Sparkasse",
                    "volksbank": "Volksbank/Raiffeisenbank",
                    "deutsche_bank": "Deutsche Bank"
                }.get(x, x)
            )

        uploaded_file = st.file_uploader(
            "CSV-Datei hochladen",
            type=["csv"],
            help="Laden Sie den Kontoauszug als CSV-Datei hoch"
        )

        if uploaded_file:
            csv_content = uploaded_file.read().decode('utf-8', errors='replace')

            erfolg, nachricht, transaktionen = bankabgleich.csv_importieren(
                csv_content,
                bank_format
            )

            if erfolg:
                st.success(nachricht)

                # Transaktionen automatisch zuordnen
                transaktionen = bankabgleich.transaktionen_zuordnen(transaktionen)

                # Ergebnisse anzeigen
                st.markdown("#### Importierte Transaktionen")

                for i, trans in enumerate(transaktionen):
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 2, 1, 2])

                        with col1:
                            st.markdown(f"**{trans.datum.strftime('%d.%m.%Y')}**")
                            st.caption(trans.verwendungszweck[:50] + "..." if len(trans.verwendungszweck) > 50 else trans.verwendungszweck)

                        with col2:
                            farbe = "green" if trans.betrag > 0 else "red"
                            st.markdown(f"<span style='color: {farbe}'>{float(trans.betrag):,.2f} EUR</span>", unsafe_allow_html=True)

                        with col3:
                            if trans.zuordnungs_status == ZuordnungsStatus.ZUGEORDNET:
                                st.markdown(badge("Zugeordnet", "success"), unsafe_allow_html=True)
                            elif trans.zuordnungs_status == ZuordnungsStatus.VORGESCHLAGEN:
                                st.markdown(badge("Vorschlag", "warning"), unsafe_allow_html=True)
                            else:
                                st.markdown(badge("Offen", "secondary"), unsafe_allow_html=True)

                        with col4:
                            if trans.projekt:
                                st.caption(f"Projekt: {trans.projekt.aktenzeichen or trans.projekt.projektnummer}")
                                st.caption(f"Konfidenz: {trans.konfidenz:.0%}")

                                if st.button("Bestätigen", key=f"confirm_{i}"):
                                    erfolg, msg = bankabgleich.zuordnung_bestaetigen(
                                        trans,
                                        trans.projekt_id,
                                        als_erstattung=True
                                    )
                                    if erfolg:
                                        st.success(msg)
                                    else:
                                        st.error(msg)

                        st.markdown("---")
            else:
                st.error(nachricht)

        # Offene Zahlungen
        st.markdown("---")
        st.markdown("#### Offene Zahlungen")

        offene = bankabgleich.get_offene_zahlungen()

        if offene:
            for pos in offene[:10]:  # Nur die ersten 10
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.markdown(f"**{pos.beschreibung}**")
                    if pos.projekt:
                        st.caption(f"Projekt: {pos.projekt.aktenzeichen or pos.projekt.projektnummer}")

                with col2:
                    st.markdown(f"{float(pos.betrag):,.2f} EUR")

                with col3:
                    st.markdown(badge("Offen", "warning"), unsafe_allow_html=True)
        else:
            st.success("Keine offenen Zahlungen.")


def _render_klassifizierung_tab():
    """Rendert den Klassifizierungs-Tab"""

    st.markdown("### Automatische Dokumenten-Klassifizierung")

    with get_session() as db:
        klassifizierung = get_klassifizierungs_service(db)

        # Projekt auswählen
        aktives_projekt_id = st.session_state.get("aktives_projekt_id")

        if not aktives_projekt_id:
            st.warning("Bitte wählen Sie zuerst ein Projekt aus.")
            return

        projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == aktives_projekt_id).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        # Dokumente laden
        dokumente = [d for d in projekt.dokumente if not d.geloescht]

        if not dokumente:
            st.info("Keine Dokumente zum Klassifizieren.")
            return

        # Nicht klassifizierte Dokumente
        unklassifiziert = [d for d in dokumente if d.dokument_typ == DokumentTyp.SONSTIG]

        st.markdown(f"#### {len(unklassifiziert)} Dokumente zur Klassifizierung")

        # Batch-Klassifizierung
        if unklassifiziert:
            if st.button("Alle automatisch klassifizieren", type="primary"):
                erfolge = 0
                for dok in unklassifiziert:
                    erfolg, _ = klassifizierung.auto_klassifiziere_und_speichere(dok)
                    if erfolg:
                        erfolge += 1

                st.success(f"{erfolge} von {len(unklassifiziert)} Dokumenten automatisch klassifiziert")
                st.rerun()

        st.markdown("---")

        # Einzelne Dokumente
        for dok in dokumente:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])

                with col1:
                    st.markdown(f"**{dok.original_dateiname}**")

                with col2:
                    st.markdown(f"Aktuell: {dok.dokument_typ_anzeige}")

                with col3:
                    # Klassifizierung durchführen
                    ergebnis = klassifizierung.klassifiziere(dok)

                    konfidenz_farbe = "success" if ergebnis.konfidenz >= 0.7 else "warning" if ergebnis.konfidenz >= 0.4 else "danger"
                    st.markdown(
                        badge(f"{ergebnis.konfidenz:.0%}", konfidenz_farbe),
                        unsafe_allow_html=True
                    )

                with col4:
                    if ergebnis.dokument_typ != dok.dokument_typ:
                        st.caption(f"Vorschlag: {ergebnis.dokument_typ.value}")

                        if st.button("Übernehmen", key=f"class_{dok.id}"):
                            dok.dokument_typ = ergebnis.dokument_typ
                            db.flush()
                            st.success("Klassifizierung übernommen")
                            st.rerun()

                # Erkannte Merkmale anzeigen
                if ergebnis.erkannte_merkmale:
                    with st.expander("Erkannte Merkmale"):
                        for merkmal in ergebnis.erkannte_merkmale[:5]:
                            st.caption(f"- {merkmal}")

                st.markdown("---")
