"""
Statistik-Dashboard für Auswertungen und Übersichten
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import UnfallProjekt, KostenPosition, Dokument, User, Wiedervorlage
from src.config.database import get_session


def render_statistik():
    """Rendert das Statistik-Dashboard"""

    st.markdown("## Statistik & Auswertungen")

    rolle = st.session_state.get("user_rolle")
    user_id = st.session_state.get("user_id")

    tabs = st.tabs(["Übersicht", "Projekte", "Finanzen", "Aktivitäten"])

    with tabs[0]:
        _render_uebersicht(user_id, rolle)

    with tabs[1]:
        _render_projekt_statistik(user_id, rolle)

    with tabs[2]:
        _render_finanz_statistik(user_id, rolle)

    with tabs[3]:
        _render_aktivitaets_statistik(user_id, rolle)


def _render_uebersicht(user_id: int, rolle: str):
    """Rendert die Übersicht mit KPIs"""

    with get_session() as db:
        # Projekte Query basierend auf Rolle
        query = db.query(UnfallProjekt)
        if rolle == "ANWALT":
            query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
        elif rolle == "WERKSTATT":
            query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)
        elif rolle == "GUTACHTER":
            query = query.filter(UnfallProjekt.gutachter_user_id == user_id)

        projekte = query.all()

        # KPIs berechnen
        gesamt = len(projekte)
        offen = len([p for p in projekte if p.status == "OFFEN"])
        in_bearbeitung = len([p for p in projekte if p.status == "IN_BEARBEITUNG"])
        abgeschlossen = len([p for p in projekte if p.status == "ABGESCHLOSSEN"])

        # Diesen Monat
        heute = datetime.now()
        monatsanfang = heute.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        diesen_monat = len([p for p in projekte if p.erstellt_am and p.erstellt_am >= monatsanfang])

        # KPI Cards
        st.markdown("### Kennzahlen")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Projekte gesamt", gesamt)

        with col2:
            st.metric("Offen", offen)

        with col3:
            st.metric("In Bearbeitung", in_bearbeitung)

        with col4:
            st.metric("Abgeschlossen", abgeschlossen)

        with col5:
            st.metric("Diesen Monat", diesen_monat, delta=f"+{diesen_monat}")

        st.markdown("---")

        # Forderungen
        st.markdown("### Forderungen")

        summe_gefordert = Decimal("0")
        summe_erstattet = Decimal("0")

        for projekt in projekte:
            for kp in projekt.kostenpositionen:
                summe_gefordert += kp.betrag_gefordert or Decimal("0")
                summe_erstattet += kp.betrag_erstattet or Decimal("0")

        offen_betrag = summe_gefordert - summe_erstattet
        quote = (float(summe_erstattet) / float(summe_gefordert) * 100) if summe_gefordert > 0 else 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Gefordert", f"{float(summe_gefordert):,.2f} €")

        with col2:
            st.metric("Erstattet", f"{float(summe_erstattet):,.2f} €")

        with col3:
            st.metric("Offen", f"{float(offen_betrag):,.2f} €")

        with col4:
            st.metric("Erstattungsquote", f"{quote:.1f}%")

        st.markdown("---")

        # Wiedervorlagen
        st.markdown("### Wiedervorlagen")

        wv_query = db.query(Wiedervorlage).join(UnfallProjekt)
        if rolle == "ANWALT":
            wv_query = wv_query.filter(UnfallProjekt.anwalt_user_id == user_id)
        elif rolle == "WERKSTATT":
            wv_query = wv_query.filter(UnfallProjekt.werkstatt_user_id == user_id)

        wiedervorlagen = wv_query.filter(Wiedervorlage.erledigt == False).all()

        ueberfaellig = len([w for w in wiedervorlagen if w.ist_ueberfaellig])
        heute_faellig = len([w for w in wiedervorlagen if w.tage_bis_faellig == 0])
        diese_woche = len([w for w in wiedervorlagen if 0 < w.tage_bis_faellig <= 7])

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Offen", len(wiedervorlagen))

        with col2:
            st.metric("Überfällig", ueberfaellig, delta=f"-{ueberfaellig}" if ueberfaellig > 0 else None, delta_color="inverse")

        with col3:
            st.metric("Heute fällig", heute_faellig)

        with col4:
            st.metric("Diese Woche", diese_woche)


def _render_projekt_statistik(user_id: int, rolle: str):
    """Rendert Projektstatistiken"""

    with get_session() as db:
        query = db.query(UnfallProjekt)
        if rolle == "ANWALT":
            query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
        elif rolle == "WERKSTATT":
            query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)

        projekte = query.all()

        if not projekte:
            st.info("Keine Projekte vorhanden.")
            return

        # Status-Verteilung
        st.markdown("### Projektverteilung nach Status")

        status_counts = {}
        for p in projekte:
            status = p.status_anzeige
            status_counts[status] = status_counts.get(status, 0) + 1

        fig = px.pie(
            names=list(status_counts.keys()),
            values=list(status_counts.values()),
            title="Projekte nach Status",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig, use_container_width=True)

        # Projekte pro Monat
        st.markdown("### Projekte pro Monat")

        # Daten für die letzten 12 Monate
        monate = []
        heute = datetime.now()
        for i in range(11, -1, -1):
            monat = (heute.replace(day=1) - timedelta(days=i*30)).strftime("%Y-%m")
            monate.append(monat)

        projekte_pro_monat = {m: 0 for m in monate}
        for p in projekte:
            if p.erstellt_am:
                monat = p.erstellt_am.strftime("%Y-%m")
                if monat in projekte_pro_monat:
                    projekte_pro_monat[monat] += 1

        fig = px.bar(
            x=list(projekte_pro_monat.keys()),
            y=list(projekte_pro_monat.values()),
            labels={"x": "Monat", "y": "Anzahl Projekte"},
            title="Neue Projekte pro Monat"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Durchschnittliche Bearbeitungszeit
        st.markdown("### Bearbeitungszeiten")

        abgeschlossene = [p for p in projekte if p.abgeschlossen and p.erstellt_am and p.abgeschlossen_am]

        if abgeschlossene:
            bearbeitungszeiten = [
                (p.abgeschlossen_am - p.erstellt_am).days
                for p in abgeschlossene
            ]
            durchschnitt = sum(bearbeitungszeiten) / len(bearbeitungszeiten)
            minimum = min(bearbeitungszeiten)
            maximum = max(bearbeitungszeiten)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Durchschnitt", f"{durchschnitt:.0f} Tage")

            with col2:
                st.metric("Minimum", f"{minimum} Tage")

            with col3:
                st.metric("Maximum", f"{maximum} Tage")
        else:
            st.info("Noch keine abgeschlossenen Projekte für Bearbeitungszeit-Analyse.")


def _render_finanz_statistik(user_id: int, rolle: str):
    """Rendert Finanzstatistiken"""

    with get_session() as db:
        query = db.query(UnfallProjekt)
        if rolle == "ANWALT":
            query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
        elif rolle == "WERKSTATT":
            query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)

        projekte = query.all()

        if not projekte:
            st.info("Keine Projekte vorhanden.")
            return

        # Kosten nach Kategorie
        st.markdown("### Kosten nach Kategorie")

        kategorien = {}
        for projekt in projekte:
            for kp in projekt.kostenpositionen:
                if kp.kategorie:
                    kat = kp.kategorie.value
                    if kat not in kategorien:
                        kategorien[kat] = {"gefordert": Decimal("0"), "erstattet": Decimal("0")}
                    kategorien[kat]["gefordert"] += kp.betrag_gefordert or Decimal("0")
                    kategorien[kat]["erstattet"] += kp.betrag_erstattet or Decimal("0")

        if kategorien:
            df = pd.DataFrame([
                {
                    "Kategorie": k,
                    "Gefordert": float(v["gefordert"]),
                    "Erstattet": float(v["erstattet"])
                }
                for k, v in kategorien.items()
            ])

            fig = px.bar(
                df,
                x="Kategorie",
                y=["Gefordert", "Erstattet"],
                barmode="group",
                title="Kosten nach Kategorie"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Top 10 Projekte nach Forderungshöhe
        st.markdown("### Top 10 Projekte nach Forderungshöhe")

        projekt_summen = []
        for projekt in projekte:
            summe = sum(kp.betrag_gefordert or Decimal("0") for kp in projekt.kostenpositionen)
            projekt_summen.append({
                "Aktenzeichen": projekt.aktenzeichen or projekt.projektnummer,
                "Forderung": float(summe)
            })

        projekt_summen.sort(key=lambda x: x["Forderung"], reverse=True)
        top_10 = projekt_summen[:10]

        if top_10:
            df = pd.DataFrame(top_10)
            fig = px.bar(
                df,
                x="Aktenzeichen",
                y="Forderung",
                title="Top 10 Projekte nach Forderungshöhe"
            )
            st.plotly_chart(fig, use_container_width=True)


def _render_aktivitaets_statistik(user_id: int, rolle: str):
    """Rendert Aktivitätsstatistiken"""

    with get_session() as db:
        query = db.query(UnfallProjekt)
        if rolle == "ANWALT":
            query = query.filter(UnfallProjekt.anwalt_user_id == user_id)
        elif rolle == "WERKSTATT":
            query = query.filter(UnfallProjekt.werkstatt_user_id == user_id)

        projekte = query.all()
        projekt_ids = [p.id for p in projekte]

        # Dokumente pro Monat
        st.markdown("### Hochgeladene Dokumente")

        dokumente = db.query(Dokument).filter(
            Dokument.unfallprojekt_id.in_(projekt_ids)
        ).all()

        # Dokumente nach Typ
        dok_typen = {}
        for dok in dokumente:
            typ = dok.dokument_typ_anzeige if dok.dokument_typ else "Sonstig"
            dok_typen[typ] = dok_typen.get(typ, 0) + 1

        if dok_typen:
            fig = px.pie(
                names=list(dok_typen.keys()),
                values=list(dok_typen.values()),
                title="Dokumente nach Typ"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Gesamtstatistik
        st.markdown("### Gesamtstatistik")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Dokumente gesamt", len(dokumente))

        with col2:
            freigegeben = len([d for d in dokumente if d.freigabe_erteilt])
            st.metric("Freigegeben", freigegeben)

        with col3:
            mit_ocr = len([d for d in dokumente if d.ocr_verarbeitet])
            st.metric("Mit OCR verarbeitet", mit_ocr)
