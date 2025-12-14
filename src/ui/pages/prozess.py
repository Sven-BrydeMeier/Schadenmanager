"""
Prozessmodul/Klagevorbereitung UI-Seite
Klagen, Schriftsätze und Gerichtskosten
"""
import streamlit as st
from datetime import date
from decimal import Decimal

from src.config.database import get_session
from src.services.prozess import ProzessService, Prozess, Schriftsatz, ProzessStatus, SchriftsatzTyp


def render_prozess():
    """Rendert die Prozess-Seite"""
    st.title("⚖️ Prozessmodul / Klagevorbereitung")

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
        "Prozesse", "Neuer Prozess", "Kostenrechner", "Schriftsätze"
    ])

    with tab1:
        _render_prozesse(projekt_id)

    with tab2:
        _render_neuer_prozess(projekt_id)

    with tab3:
        _render_kostenrechner()

    with tab4:
        _render_schriftsaetze(projekt_id)


def _render_prozesse(projekt_id: int):
    """Zeigt bestehende Prozesse"""
    st.subheader("Laufende Prozesse")

    with get_session() as db:
        service = ProzessService(db)
        prozesse = service.prozesse_fuer_projekt(projekt_id)

        if not prozesse:
            st.info("Keine Prozesse für dieses Projekt")
            return

        for prozess in prozesse:
            with st.expander(
                f"{prozess.status_anzeige} | {prozess.gericht_name} - Az.: {prozess.aktenzeichen or '-'}",
                expanded=prozess.status not in [ProzessStatus.RECHTSKRAEFTIG, ProzessStatus.KLAGE_ZURUECKGENOMMEN]
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Kläger:** {prozess.klaeger}")
                    st.write(f"**Beklagte:** {prozess.beklagter}")
                    st.write(f"**Streitwert:** {prozess.streitwert:,.2f} EUR" if prozess.streitwert else "")

                    if prozess.klage_eingereicht_am:
                        st.write(f"**Eingereicht:** {prozess.klage_eingereicht_am.strftime('%d.%m.%Y')}")

                with col2:
                    if prozess.guetetermin:
                        st.write(f"**Gütetermin:** {prozess.guetetermin.strftime('%d.%m.%Y')}")
                    if prozess.haupttermin:
                        st.write(f"**Haupttermin:** {prozess.haupttermin.strftime('%d.%m.%Y')}")
                    if prozess.erfolgsaussicht_prozent:
                        st.progress(prozess.erfolgsaussicht_prozent / 100)
                        st.write(f"Erfolgsaussicht: {prozess.erfolgsaussicht_prozent}%")

                # Schriftsätze zu diesem Prozess
                if prozess.schriftsaetze:
                    st.markdown("**Schriftsätze:**")
                    for ss in prozess.schriftsaetze:
                        st.write(f"- {ss.typ_anzeige}: {ss.titel}")

                # Urteil anzeigen wenn vorhanden
                if prozess.urteil_zusammenfassung:
                    st.markdown("**Urteil:**")
                    st.write(prozess.urteil_zusammenfassung)

                    if prozess.zugesprochener_betrag:
                        st.success(f"Zugesprochener Betrag: {prozess.zugesprochener_betrag:,.2f} EUR")


def _render_neuer_prozess(projekt_id: int):
    """Formular für neuen Prozess"""
    st.subheader("Neuen Prozess anlegen")

    with st.form("neuer_prozess"):
        col1, col2 = st.columns(2)

        with col1:
            gericht_name = st.text_input("Gericht *", placeholder="z.B. Amtsgericht München")
            gericht_adresse = st.text_area("Gerichtsadresse", height=80)
            aktenzeichen = st.text_input("Aktenzeichen", placeholder="Wird nach Einreichung vergeben")

        with col2:
            streitwert = st.number_input("Streitwert (EUR) *", min_value=0.0, step=100.0)
            klaeger = st.text_input("Kläger *")
            beklagter = st.text_input("Beklagte *")

        col3, col4 = st.columns(2)

        with col3:
            gegnerischer_anwalt = st.text_input("Gegnerischer Anwalt")
            erfolgsaussicht = st.slider("Erfolgsaussicht", 0, 100, 50)

        with col4:
            risikobewertung = st.text_area("Risikobewertung", height=100)

        submitted = st.form_submit_button("Prozess anlegen", type="primary")

        if submitted:
            if not gericht_name or not streitwert or not klaeger or not beklagter:
                st.error("Bitte alle Pflichtfelder ausfüllen")
            else:
                with get_session() as db:
                    service = ProzessService(db)
                    user_id = st.session_state.get("user_id")

                    prozess = service.prozess_erstellen(
                        projekt_id=projekt_id,
                        gericht_name=gericht_name,
                        gericht_adresse=gericht_adresse,
                        aktenzeichen=aktenzeichen,
                        streitwert=Decimal(str(streitwert)),
                        klaeger=klaeger,
                        beklagter=beklagter,
                        gegnerischer_anwalt=gegnerischer_anwalt,
                        erfolgsaussicht_prozent=erfolgsaussicht,
                        risikobewertung=risikobewertung,
                        erstellt_von_user_id=user_id
                    )

                    st.success(f"Prozess angelegt!")

                    # Gerichtskosten berechnen
                    kosten = service.berechne_gerichtskosten(prozess.streitwert)
                    st.info(f"Gerichtskostenvorschuss: {kosten['gerichtskosten_vorschuss']:.2f} EUR")


def _render_kostenrechner():
    """Gerichtskosten- und Risikorechner"""
    st.subheader("Gerichtskosten- und Risikorechner")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Gerichtskostenberechnung")

        streitwert = st.number_input(
            "Streitwert (EUR)",
            min_value=0.0,
            value=10000.0,
            step=500.0,
            key="gk_streitwert"
        )

        if st.button("Kosten berechnen"):
            with get_session() as db:
                service = ProzessService(db)
                kosten = service.berechne_gerichtskosten(Decimal(str(streitwert)))

                st.markdown("#### Ergebnis")
                st.write(f"**Streitwert:** {kosten['streitwert']:,.2f} EUR")
                st.write(f"**Einfache Gebühr:** {kosten['einfache_gebuehr']:.2f} EUR")
                st.write(f"**Gerichtskostenvorschuss (3x):** {kosten['gerichtskosten_vorschuss']:.2f} EUR")
                st.write(f"**Verfahrensgebühr:** {kosten['verfahrensgebuehr']:.2f} EUR")
                st.caption(kosten['hinweis'])

    with col2:
        st.markdown("### Prozessrisiko-Berechnung")

        streitwert_risiko = st.number_input(
            "Streitwert (EUR)",
            min_value=0.0,
            value=10000.0,
            step=500.0,
            key="risiko_streitwert"
        )

        erfolgsaussicht = st.slider(
            "Erfolgsaussicht (%)",
            0, 100, 60
        )

        eigene_anwaltskosten = st.number_input(
            "Eigene Anwaltskosten (EUR)",
            min_value=0.0,
            value=1500.0,
            step=100.0
        )

        gegner_anwaltskosten = st.number_input(
            "Gegnerische Anwaltskosten (EUR)",
            min_value=0.0,
            value=1500.0,
            step=100.0
        )

        if st.button("Risiko berechnen"):
            with get_session() as db:
                service = ProzessService(db)
                risiko = service.berechne_prozessrisiko(
                    streitwert=Decimal(str(streitwert_risiko)),
                    erfolgsaussicht_prozent=erfolgsaussicht,
                    eigene_anwaltskosten=Decimal(str(eigene_anwaltskosten)),
                    gegnerische_anwaltskosten=Decimal(str(gegner_anwaltskosten))
                )

                st.markdown("#### Ergebnis")

                if risiko['ampel'] == 'gruen':
                    st.success(risiko['empfehlung'])
                elif risiko['ampel'] == 'gelb':
                    st.warning(risiko['empfehlung'])
                else:
                    st.error(risiko['empfehlung'])

                col_a, col_b = st.columns(2)

                with col_a:
                    st.metric("Bei Erfolg", f"+{risiko['gewinn_bei_erfolg']:,.2f} EUR")
                with col_b:
                    st.metric("Bei Niederlage", f"-{risiko['verlust_bei_niederlage']:,.2f} EUR")

                st.write(f"**Erwartungswert:** {risiko['erwartungswert']:,.2f} EUR")


def _render_schriftsaetze(projekt_id: int):
    """Schriftsatz-Generator"""
    st.subheader("Schriftsatz-Generator")

    with get_session() as db:
        service = ProzessService(db)
        prozesse = service.prozesse_fuer_projekt(projekt_id)

        if not prozesse:
            st.warning("Bitte erst einen Prozess anlegen")
            return

        prozess_options = {p.id: f"{p.gericht_name} - {p.aktenzeichen or 'Ohne Az.'}" for p in prozesse}
        prozess_id = st.selectbox(
            "Prozess auswählen",
            list(prozess_options.keys()),
            format_func=lambda x: prozess_options.get(x, "")
        )

        prozess = next((p for p in prozesse if p.id == prozess_id), None)

        if not prozess:
            return

        schriftsatz_typ = st.selectbox(
            "Schriftsatz-Typ",
            [t for t in SchriftsatzTyp],
            format_func=lambda t: {
                SchriftsatzTyp.KLAGESCHRIFT: "Klageschrift",
                SchriftsatzTyp.KLAGEERWIDERUNG: "Klageerwiderung",
                SchriftsatzTyp.REPLIK: "Replik",
                SchriftsatzTyp.DUPLIK: "Duplik",
                SchriftsatzTyp.BEWEISANTRAG: "Beweisantrag",
                SchriftsatzTyp.STELLUNGNAHME: "Stellungnahme",
                SchriftsatzTyp.BERUFUNGSSCHRIFT: "Berufungsschrift",
                SchriftsatzTyp.BERUFUNGSERWIDERUNG: "Berufungserwiderung",
                SchriftsatzTyp.VERGLEICHSVORSCHLAG: "Vergleichsvorschlag",
                SchriftsatzTyp.KOSTENANTRAG: "Kostenantrag"
            }.get(t, str(t))
        )

        if schriftsatz_typ == SchriftsatzTyp.KLAGESCHRIFT:
            if st.button("Klageschrift generieren", type="primary"):
                from src.models import UnfallProjekt
                projekt = db.query(UnfallProjekt).get(projekt_id)

                klageschrift = service.generiere_klageschrift(prozess, projekt)

                st.text_area(
                    "Klageschrift-Entwurf",
                    value=klageschrift,
                    height=500,
                    key="klageschrift_text"
                )

                st.download_button(
                    "📥 Als Text herunterladen",
                    data=klageschrift,
                    file_name="klageschrift_entwurf.txt",
                    mime="text/plain"
                )

        elif schriftsatz_typ == SchriftsatzTyp.BEWEISANTRAG:
            st.markdown("**Beweisthemen eingeben:**")

            beweisthemen = []
            for i in range(5):
                thema = st.text_input(f"Beweisthema {i+1}", key=f"beweis_{i}")
                if thema:
                    beweisthemen.append(thema)

            if st.button("Beweisantrag generieren", type="primary"):
                if beweisthemen:
                    antrag = service.generiere_beweisantrag(prozess, beweisthemen)

                    st.text_area(
                        "Beweisantrag-Entwurf",
                        value=antrag,
                        height=400,
                        key="beweisantrag_text"
                    )
                else:
                    st.warning("Bitte mindestens ein Beweisthema eingeben")
