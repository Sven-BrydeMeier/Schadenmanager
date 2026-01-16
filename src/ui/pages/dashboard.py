"""
Dashboard-Seiten für verschiedene Rollen
"""
import streamlit as st
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, User, TimelineMeilenstein, KostenPosition,
    Dokument, Korrespondenz, MeilensteinStatus, KostenAmpel, Rollen
)
from src.ui.components import (
    metric_card, timeline, kosten_uebersicht, projekt_header,
    badge, alert, card_simple
)
from src.config.database import get_session


def render_dashboard():
    """Rendert das rollenspezifische Dashboard"""

    rolle = st.session_state.get("user_rolle", "")
    user_id = st.session_state.get("user_id")

    with get_session() as db:
        # Projekte des Benutzers laden
        projekte = _get_user_projekte(db, user_id, rolle)

        # Aktives Projekt aus Session oder erstes Projekt
        aktives_projekt_id = st.session_state.get("aktives_projekt_id")
        aktives_projekt = None

        if aktives_projekt_id:
            aktives_projekt = db.query(UnfallProjekt).filter(
                UnfallProjekt.id == aktives_projekt_id
            ).first()

        if not aktives_projekt and projekte:
            aktives_projekt = projekte[0]
            st.session_state["aktives_projekt_id"] = aktives_projekt.id

        # Dashboard basierend auf Rolle rendern
        if rolle == "ADMIN":
            _render_admin_dashboard(db, projekte)
        elif rolle == "ANWALT":
            _render_anwalt_dashboard(db, projekte, aktives_projekt)
        elif rolle == "WERKSTATT":
            _render_werkstatt_dashboard(db, projekte, aktives_projekt)
        elif rolle == "GUTACHTER":
            _render_gutachter_dashboard(db, projekte, aktives_projekt)
        elif rolle == "UNFALLOPFER":
            _render_unfallopfer_dashboard(db, projekte, aktives_projekt)
        elif rolle in ["VERSICHERUNG_EIGEN", "VERSICHERUNG_GEGNER"]:
            _render_versicherung_dashboard(db, projekte, aktives_projekt)
        else:
            st.warning(f"Unbekannte Rolle: {rolle}")


def _get_user_projekte(db: Session, user_id: int, rolle: str) -> List[UnfallProjekt]:
    """Lädt die Projekte eines Benutzers basierend auf seiner Rolle"""

    query = db.query(UnfallProjekt)

    if rolle == "ADMIN":
        # Admin sieht alle Projekte
        pass
    elif rolle == "ANWALT":
        query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
    elif rolle == "WERKSTATT":
        query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)
    elif rolle == "GUTACHTER":
        query = query.filter(UnfallProjekt.gutachter_user_id == user_id)
    elif rolle == "UNFALLOPFER":
        query = query.filter(UnfallProjekt.unfallopfer_user_id == user_id)
    elif rolle == "VERSICHERUNG_EIGEN":
        query = query.filter(UnfallProjekt.versicherung_eigen_user_id == user_id)
    elif rolle == "VERSICHERUNG_GEGNER":
        query = query.filter(UnfallProjekt.versicherung_gegner_user_id == user_id)

    return query.order_by(UnfallProjekt.erstellt_am.desc()).all()


def _render_admin_dashboard(db: Session, projekte: List[UnfallProjekt]):
    """Dashboard für Administratoren"""

    st.markdown("## Admin-Dashboard")

    # Übersichtskarten
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card(
            "Offene Projekte",
            str(len([p for p in projekte if p.status == "OFFEN"])),
            "warning"
        )

    with col2:
        metric_card(
            "In Bearbeitung",
            str(len([p for p in projekte if p.status == "IN_BEARBEITUNG"])),
            "info"
        )

    with col3:
        metric_card(
            "Abgeschlossen",
            str(len([p for p in projekte if p.status == "ABGESCHLOSSEN"])),
            "success"
        )

    with col4:
        benutzer_count = db.query(User).filter(User.aktiv == True).count()
        metric_card("Aktive Benutzer", str(benutzer_count))

    st.markdown("---")

    # Letzte Projekte
    st.markdown("### Aktuelle Projekte")

    if projekte:
        for projekt in projekte[:10]:
            with st.expander(f"{projekt.projektnummer} - {projekt.status_anzeige}"):
                projekt_header(projekt)
    else:
        st.info("Keine Projekte vorhanden.")


def _render_anwalt_dashboard(db: Session, projekte: List[UnfallProjekt], aktives_projekt: Optional[UnfallProjekt]):
    """Dashboard für Rechtsanwälte"""

    st.markdown("## Anwalt-Dashboard")

    if not projekte:
        st.info("Sie haben noch keine zugewiesenen Akten.")
        return

    # Aktenauswahl - mit Aktenzeichen im Format NNN/YY
    def get_aktenzeichen_label(p):
        if p.aktenzeichen:
            return p.aktenzeichen
        elif p.aktenzeichen_nummer and p.aktenzeichen_jahr:
            return f"{p.aktenzeichen_nummer}/{str(p.aktenzeichen_jahr)[-2:]}"
        else:
            return p.projektnummer

    akte_optionen = {get_aktenzeichen_label(p): p for p in projekte}
    ausgewaehlte = st.selectbox(
        "📁 Akte auswählen",
        list(akte_optionen.keys()),
        index=0 if aktives_projekt else None
    )

    if ausgewaehlte:
        projekt = akte_optionen[ausgewaehlte]
        st.session_state["aktives_projekt_id"] = projekt.id

        # Akten-Header
        projekt_header(projekt)

        # Letzter Dokumenteneingang anzeigen
        _render_letzter_dokumenteneingang(db, projekt)

        st.markdown("---")

        # Timeline
        st.markdown("### Status-Timeline")
        meilensteine = [
            {
                "code": m.code,
                "beschreibung": m.beschreibung,
                "status": m.status
            }
            for m in sorted(projekt.timeline_meilensteine, key=lambda x: x.reihenfolge)
        ]
        timeline(meilensteine[:8])  # Maximal 8 anzeigen

        st.markdown("---")

        # Tabs für Details
        tab1, tab2, tab3, tab4 = st.tabs(["Kosten", "Dokumente", "Korrespondenz", "Gebühren"])

        with tab1:
            _render_kosten_tab(projekt)

        with tab2:
            _render_dokumente_tab(projekt)

        with tab3:
            _render_korrespondenz_tab(projekt)

        with tab4:
            _render_gebuehren_tab(projekt)


def _render_werkstatt_dashboard(db: Session, projekte: List[UnfallProjekt], aktives_projekt: Optional[UnfallProjekt]):
    """Dashboard für Werkstätten"""

    st.markdown("## Werkstatt-Dashboard")

    if not projekte:
        st.info("Sie haben noch keine zugewiesenen Projekte.")
        if st.button("Neues Projekt anlegen"):
            st.session_state["show_new_project"] = True
            st.rerun()
        return

    # Übersichtskarten
    col1, col2, col3 = st.columns(3)

    with col1:
        reparatur_offen = sum(
            1 for p in projekte
            for kp in p.kostenpositionen
            if kp.kategorie and kp.kategorie.value == "REPARATUR" and kp.status_ampel != KostenAmpel.GRUEN
        )
        metric_card("Offene Reparaturen", str(reparatur_offen), "warning")

    with col2:
        ersatzwagen_aktiv = len([
            p for p in projekte
            if p.ersatzwagenanbieter_id and not p.abgeschlossen
        ])
        metric_card("Aktive Ersatzwagen", str(ersatzwagen_aktiv), "info")

    with col3:
        metric_card("Projekte gesamt", str(len(projekte)))

    st.markdown("---")

    # Projektliste mit Schnellaktionen
    st.markdown("### Aktuelle Projekte")

    for projekt in projekte[:10]:
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"**{projekt.projektnummer}**")
            if projekt.kfz_eigen:
                st.caption(f"{projekt.kfz_eigen.kennzeichen} - {projekt.kfz_eigen.fahrzeug_bezeichnung}")

        with col2:
            st.markdown(badge(projekt.status_anzeige, "info"), unsafe_allow_html=True)

        with col3:
            if st.button("Öffnen", key=f"open_{projekt.id}"):
                st.session_state["aktives_projekt_id"] = projekt.id
                st.rerun()


def _render_gutachter_dashboard(db: Session, projekte: List[UnfallProjekt], aktives_projekt: Optional[UnfallProjekt]):
    """Dashboard für Gutachter"""

    st.markdown("## Gutachter-Dashboard")

    if not projekte:
        st.info("Sie haben noch keine zugewiesenen Aufträge.")
        return

    # Übersicht
    col1, col2 = st.columns(2)

    with col1:
        ohne_gutachten = len([
            p for p in projekte
            if not any(d.dokument_typ and d.dokument_typ.value == "GUTACHTEN" for d in p.dokumente)
        ])
        metric_card("Gutachten ausstehend", str(ohne_gutachten), "warning")

    with col2:
        metric_card("Aufträge gesamt", str(len(projekte)))

    st.markdown("---")

    # Auftragsliste
    st.markdown("### Aufträge")

    for projekt in projekte:
        hat_gutachten = any(
            d.dokument_typ and d.dokument_typ.value == "GUTACHTEN"
            for d in projekt.dokumente
        )

        with st.expander(f"{projekt.projektnummer} - {'Gutachten vorhanden' if hat_gutachten else 'Ausstehend'}"):
            projekt_header(projekt)

            if not hat_gutachten:
                st.warning("Gutachten noch nicht hochgeladen.")
                if st.button("Gutachten hochladen", key=f"upload_{projekt.id}"):
                    st.session_state["upload_projekt_id"] = projekt.id
                    st.session_state["show_upload"] = True


def _render_unfallopfer_dashboard(db: Session, projekte: List[UnfallProjekt], aktives_projekt: Optional[UnfallProjekt]):
    """Dashboard für Unfallopfer (Mandanten)"""

    st.markdown("## Mein Schadensfall")

    if not projekte:
        st.info("Sie sind noch keinem Schadensfall zugeordnet.")
        return

    # Nur ein Projekt für Unfallopfer anzeigen
    projekt = projekte[0]

    # Status-Übersicht in einfacher Sprache
    st.markdown("### Aktueller Status")

    # Einfache Fortschrittsanzeige - prüfe beide Status-Varianten (GRUEN oder ERLEDIGT)
    meilensteine_erledigt = sum(
        1 for m in projekt.timeline_meilensteine
        if m.status in [MeilensteinStatus.GRUEN, MeilensteinStatus.ERLEDIGT]
    )
    meilensteine_gesamt = len(projekt.timeline_meilensteine)

    if meilensteine_gesamt > 0:
        fortschritt = int((meilensteine_erledigt / meilensteine_gesamt) * 100)
        st.progress(fortschritt / 100, text=f"Fortschritt: {fortschritt}%")

    st.markdown("---")

    # Regulierungsstand und letzter Dokumenteneingang
    st.markdown("### Regulierung")

    col1, col2 = st.columns(2)

    with col1:
        # Status der Regulierung
        gesamt_gefordert = sum(kp.betrag_brutto or 0 for kp in projekt.kostenpositionen)
        gesamt_erstattet = sum(kp.bezahlt_betrag or 0 for kp in projekt.kostenpositionen)
        noch_offen = gesamt_gefordert - gesamt_erstattet

        if gesamt_gefordert > 0:
            regulierung_prozent = int((gesamt_erstattet / gesamt_gefordert) * 100)
            st.metric("Regulierungsstand", f"{regulierung_prozent}%")
        else:
            st.metric("Regulierungsstand", "Ausstehend")

    with col2:
        # Letzter Dokumenteneingang
        letztes_dokument = db.query(Dokument).filter(
            Dokument.unfallprojekt_id == projekt.id,
            Dokument.geloescht == False
        ).order_by(Dokument.erstellt_am.desc()).first()

        if letztes_dokument and letztes_dokument.erstellt_am:
            st.metric(
                "Letzter Dokumenteneingang",
                letztes_dokument.erstellt_am.strftime('%d.%m.%Y'),
                letztes_dokument.dokument_typ_anzeige
            )
        else:
            st.metric("Letzter Dokumenteneingang", "Keine Dokumente")

    st.markdown("---")

    # Kosten-Übersicht in einfacher Form
    st.markdown("### Kosten-Übersicht")

    gesamt_gefordert = sum(kp.betrag_brutto or 0 for kp in projekt.kostenpositionen)
    gesamt_freigegeben = sum(kp.von_versicherung_freigegeben_betrag or 0 for kp in projekt.kostenpositionen)
    noch_offen = gesamt_gefordert - gesamt_freigegeben

    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card("Gesamtschaden", f"{gesamt_gefordert:,.2f} €")

    with col2:
        metric_card("Von Versicherung übernommen", f"{gesamt_freigegeben:,.2f} €", "success")

    with col3:
        if noch_offen > 0:
            metric_card("Noch offen", f"{noch_offen:,.2f} €", "warning")
        else:
            metric_card("Noch offen", "0,00 €", "success")

    # Details in Expandern
    with st.expander("Details zu den Kostenpositionen"):
        kosten_daten = [
            {
                "kategorie_anzeige": kp.kategorie_anzeige,
                "beschreibung": kp.beschreibung,
                "betrag_brutto": kp.betrag_brutto,
                "status_ampel": kp.status_ampel,
                "von_versicherung_freigegeben_betrag": kp.von_versicherung_freigegeben_betrag,
                "gekuerzt": kp.gekuerzt
            }
            for kp in projekt.kostenpositionen
        ]
        kosten_uebersicht(kosten_daten)


def _render_versicherung_dashboard(db: Session, projekte: List[UnfallProjekt], aktives_projekt: Optional[UnfallProjekt]):
    """Dashboard für Versicherungen"""

    rolle = st.session_state.get("user_rolle", "")
    titel = "Eigene Versicherung" if "EIGEN" in rolle else "Schadensregulierung"

    st.markdown(f"## {titel}")

    if not projekte:
        st.info("Keine zugewiesenen Schadensfälle.")
        return

    # Übersicht
    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card("Offene Fälle", str(len([p for p in projekte if not p.abgeschlossen])), "warning")

    with col2:
        summe_offen = sum(
            kp.betrag_brutto or 0
            for p in projekte
            for kp in p.kostenpositionen
            if kp.status_ampel != KostenAmpel.GRUEN
        )
        metric_card("Offene Forderungen", f"{summe_offen:,.2f} €", "info")

    with col3:
        metric_card("Abgeschlossen", str(len([p for p in projekte if p.abgeschlossen])), "success")

    st.markdown("---")

    # Schadensfälle
    st.markdown("### Schadensfälle")

    for projekt in projekte:
        with st.expander(f"{projekt.projektnummer}"):
            projekt_header(projekt)

            # Kostenpositionen zur Freigabe
            st.markdown("#### Kostenpositionen")

            for kp in projekt.kostenpositionen:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                with col1:
                    st.write(f"{kp.kategorie_anzeige}: {kp.beschreibung or ''}")

                with col2:
                    st.write(f"{kp.betrag_brutto:,.2f} €")

                with col3:
                    st.markdown(badge(kp.status_ampel.value, "info"), unsafe_allow_html=True)

                with col4:
                    if kp.status_ampel == KostenAmpel.ROT:
                        if st.button("Prüfen", key=f"check_{kp.id}"):
                            # Zur Kosten-Seite navigieren mit aktivem Projekt
                            st.session_state["aktives_projekt_id"] = projekt.id
                            st.session_state["page"] = "Kosten"
                            st.rerun()


def _render_letzter_dokumenteneingang(db: Session, projekt: UnfallProjekt):
    """Zeigt den letzten Dokumenteneingang für eine Akte an"""
    # Letztes Dokument laden
    letztes_dokument = db.query(Dokument).filter(
        Dokument.unfallprojekt_id == projekt.id,
        Dokument.geloescht == False
    ).order_by(Dokument.erstellt_am.desc()).first()

    if letztes_dokument:
        st.markdown("### 📥 Letzter Dokumenteneingang")
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown(f"**{letztes_dokument.dokument_typ_anzeige}**: {letztes_dokument.original_dateiname}")

        with col2:
            if letztes_dokument.erstellt_am:
                st.caption(f"📅 {letztes_dokument.erstellt_am.strftime('%d.%m.%Y %H:%M')}")

        with col3:
            status_label = "✅ Verarbeitet" if letztes_dokument.ki_verarbeitet else "⏳ Hochgeladen"
            st.caption(status_label)


def _render_kosten_tab(projekt: UnfallProjekt):
    """Rendert den Kosten-Tab"""

    st.markdown("#### Kostenpositionen")

    kosten_daten = [
        {
            "kategorie_anzeige": kp.kategorie_anzeige,
            "beschreibung": kp.beschreibung,
            "betrag_brutto": kp.betrag_brutto,
            "status_ampel": kp.status_ampel,
            "von_versicherung_freigegeben_betrag": kp.von_versicherung_freigegeben_betrag,
            "gekuerzt": kp.gekuerzt
        }
        for kp in projekt.kostenpositionen
    ]
    kosten_uebersicht(kosten_daten)


def _render_dokumente_tab(projekt: UnfallProjekt):
    """Rendert den Dokumente-Tab"""

    st.markdown("#### Dokumente")

    if not projekt.dokumente:
        st.info("Keine Dokumente vorhanden.")
    else:
        for dok in projekt.dokumente:
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"**{dok.dokument_typ_anzeige}**: {dok.original_dateiname}")

            with col2:
                status = "Verarbeitet" if dok.ki_verarbeitet else "Hochgeladen"
                st.write(status)

            with col3:
                if dok.erstellt_am:
                    st.caption(dok.erstellt_am.strftime("%d.%m.%Y"))


def _render_korrespondenz_tab(projekt: UnfallProjekt):
    """Rendert den Korrespondenz-Tab"""

    st.markdown("#### Korrespondenz")

    if not projekt.korrespondenzen:
        st.info("Keine Korrespondenz vorhanden.")
    else:
        for korr in sorted(projekt.korrespondenzen, key=lambda x: x.erstellt_am or datetime.min, reverse=True):
            with st.expander(f"{korr.richtung_anzeige} - {korr.betreff or 'Ohne Betreff'}"):
                st.markdown(f"**Status:** {korr.status_anzeige}")
                st.markdown(f"**Erstellt:** {korr.erstellt_am.strftime('%d.%m.%Y %H:%M') if korr.erstellt_am else '-'}")
                if korr.aktueller_text:
                    st.text_area("Inhalt", korr.aktueller_text, height=200, disabled=True)


def _render_gebuehren_tab(projekt: UnfallProjekt):
    """Rendert den Gebühren-Tab"""

    st.markdown("#### Rechtsanwaltsgebühren")

    if not projekt.gebuehrenberechnungen:
        st.info("Noch keine Gebührenberechnung erstellt.")

        if st.button("Gebühren berechnen"):
            st.session_state["show_gebuehren_berechnung"] = True
    else:
        # Letzte Berechnung anzeigen
        berechnung = sorted(projekt.gebuehrenberechnungen, key=lambda x: x.stand_datum or datetime.min.date())[-1]

        st.markdown(f"**Streitwert:** {berechnung.streitwert:,.2f} €")
        st.markdown("---")

        for label, wert in berechnung.aufstellung:
            if label and wert:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(label)
                with col2:
                    st.write(wert)
