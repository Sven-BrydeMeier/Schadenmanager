"""
Restwertbörse-Integration UI-Seite
Verwaltung von Restwertanfragen bei Totalschäden
"""
import streamlit as st
from datetime import date
from decimal import Decimal

from src.config.database import get_session
from src.services.restwert import RestwertService, RestwertAnfrage, RestwertAngebot, RestwertStatus


def render_restwert():
    """Rendert die Restwertbörse-Seite"""
    st.title("🚗 Restwertbörse")

    st.info("""
    Bei einem Totalschaden können Sie hier Restwertanfragen erstellen,
    Angebote vergleichen und die Abwicklung dokumentieren.
    """)

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
        "Übersicht", "Neue Anfrage", "Angebote", "Restwertbörsen"
    ])

    with tab1:
        _render_uebersicht(projekt_id)

    with tab2:
        _render_neue_anfrage(projekt_id)

    with tab3:
        _render_angebote(projekt_id)

    with tab4:
        _render_boersen()


def _render_uebersicht(projekt_id: int):
    """Zeigt Übersicht der Restwertanfragen"""
    st.subheader("Restwertanfragen")

    with get_session() as db:
        service = RestwertService(db)
        anfragen = service.anfragen_fuer_projekt(projekt_id)

        if not anfragen:
            st.info("Keine Restwertanfragen für dieses Projekt")
            return

        for anfrage in anfragen:
            with st.expander(
                f"{anfrage.status_anzeige} | {anfrage.hersteller} {anfrage.modell} - {anfrage.kennzeichen}",
                expanded=anfrage.status not in [RestwertStatus.ABGESCHLOSSEN, RestwertStatus.ABGEBROCHEN]
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Fahrzeug:** {anfrage.hersteller} {anfrage.modell}")
                    st.write(f"**Kennzeichen:** {anfrage.kennzeichen}")
                    st.write(f"**Baujahr:** {anfrage.baujahr or '-'}")
                    st.write(f"**km-Stand:** {anfrage.kilometerstand:,} km" if anfrage.kilometerstand else "")

                with col2:
                    if anfrage.wiederbeschaffungswert:
                        st.write(f"**WBW:** {anfrage.wiederbeschaffungswert:,.2f} EUR")
                    if anfrage.restwert_gutachter:
                        st.write(f"**Restwert lt. Gutachter:** {anfrage.restwert_gutachter:,.2f} EUR")

                    # Angebote
                    angebote = service.angebote_fuer_anfrage(anfrage.id)
                    if angebote:
                        hoechstes = max(float(a.gebotener_preis) for a in angebote)
                        st.success(f"**Höchstes Angebot:** {hoechstes:,.2f} EUR")

                # Aktionen je nach Status
                col_a1, col_a2, col_a3 = st.columns(3)

                with col_a1:
                    if anfrage.status == RestwertStatus.ENTWURF:
                        if st.button("📤 Anfrage versenden", key=f"send_{anfrage.id}"):
                            anfrage.status = RestwertStatus.ANFRAGE_GESENDET
                            anfrage.anfrage_gesendet_am = datetime.now()
                            db.commit()
                            st.rerun()

                with col_a2:
                    # Anfragetext generieren
                    anfrage_text = service.generiere_anfrage_text(anfrage)
                    st.download_button(
                        "📄 Anfragetext",
                        data=anfrage_text,
                        file_name=f"restwertanfrage_{anfrage.id}.txt",
                        mime="text/plain",
                        key=f"txt_{anfrage.id}"
                    )

                with col_a3:
                    if st.button("➕ Angebot hinzufügen", key=f"add_{anfrage.id}"):
                        st.session_state["add_angebot_anfrage_id"] = anfrage.id

                # Angebot hinzufügen Formular
                if st.session_state.get("add_angebot_anfrage_id") == anfrage.id:
                    _render_angebot_hinzufuegen(anfrage.id)


def _render_neue_anfrage(projekt_id: int):
    """Formular für neue Restwertanfrage"""
    st.subheader("Neue Restwertanfrage erstellen")

    with get_session() as db:
        # Fahrzeug aus Projekt laden
        from src.models import UnfallProjekt, Fahrzeug

        projekt = db.query(UnfallProjekt).get(projekt_id)

        if projekt and projekt.fahrzeug_eigen_id:
            fahrzeug = db.query(Fahrzeug).get(projekt.fahrzeug_eigen_id)
            st.info(f"Fahrzeugdaten aus Projekt übernehmen: {fahrzeug.hersteller} {fahrzeug.modell}")

            fahrzeug_id = projekt.fahrzeug_eigen_id
        else:
            fahrzeug = None
            fahrzeug_id = None

    with st.form("neue_anfrage"):
        st.markdown("### Fahrzeugdaten")

        col1, col2 = st.columns(2)

        with col1:
            kennzeichen = st.text_input("Kennzeichen *", value=fahrzeug.kennzeichen if fahrzeug else "")
            hersteller = st.text_input("Hersteller *", value=fahrzeug.hersteller if fahrzeug else "")
            modell = st.text_input("Modell *", value=fahrzeug.modell if fahrzeug else "")
            baujahr = st.number_input("Baujahr", min_value=1990, max_value=2025, value=2020)
            erstzulassung = st.date_input("Erstzulassung", value=fahrzeug.erstzulassung if fahrzeug and fahrzeug.erstzulassung else None)

        with col2:
            kilometerstand = st.number_input("Kilometerstand", min_value=0, value=50000)
            hubraum = st.number_input("Hubraum (ccm)", min_value=0, value=fahrzeug.hubraum if fahrzeug else 0)
            leistung_kw = st.number_input("Leistung (kW)", min_value=0, value=fahrzeug.leistung_kw if fahrzeug else 0)
            kraftstoff = st.selectbox("Kraftstoff", ["Benzin", "Diesel", "Elektro", "Hybrid", "Gas"])
            getriebe = st.selectbox("Getriebe", ["Schaltung", "Automatik"])
            farbe = st.text_input("Farbe", value=fahrzeug.farbe if fahrzeug else "")

        st.markdown("### Zustand")

        col3, col4 = st.columns(2)

        with col3:
            unfallschaden = st.text_area("Unfallschaden-Beschreibung *", height=100)
            vorschaeden = st.checkbox("Vorschäden vorhanden")
            if vorschaeden:
                vorschaeden_beschr = st.text_input("Vorschäden-Beschreibung")
            else:
                vorschaeden_beschr = None

        with col4:
            tuev_bis = st.date_input("TÜV bis", value=None)
            fahrbereit = st.checkbox("Fahrzeug ist fahrbereit")
            schluessel = st.checkbox("Schlüssel vorhanden", value=True)
            brief = st.checkbox("Fahrzeugbrief vorhanden", value=True)

        st.markdown("### Gutachterwerte")

        col5, col6 = st.columns(2)

        with col5:
            wiederbeschaffungswert = st.number_input("Wiederbeschaffungswert (EUR)", min_value=0.0, step=100.0)
            reparaturkosten = st.number_input("Reparaturkosten (EUR)", min_value=0.0, step=100.0)

        with col6:
            restwert_gutachter = st.number_input("Restwert lt. Gutachter (EUR)", min_value=0.0, step=100.0)
            mindestgebot = st.number_input("Mindestgebot (EUR, optional)", min_value=0.0, step=100.0)

        st.markdown("### Standort")

        col7, col8 = st.columns(2)

        with col7:
            standort_adresse = st.text_input("Adresse")
            standort_plz = st.text_input("PLZ")
            standort_ort = st.text_input("Ort")

        with col8:
            standort_kontakt = st.text_input("Ansprechpartner")
            standort_telefon = st.text_input("Telefon")

        besichtigung_von = st.date_input("Besichtigung möglich ab")
        besichtigung_bis = st.date_input("Besichtigung möglich bis")
        besichtigung_zeiten = st.text_input("Besichtigungszeiten", value="Mo-Fr 8-17 Uhr")

        anfrage_gueltig_bis = st.date_input("Angebotsfrist")

        submitted = st.form_submit_button("Anfrage erstellen", type="primary")

        if submitted:
            if not kennzeichen or not hersteller or not modell or not unfallschaden:
                st.error("Bitte alle Pflichtfelder ausfüllen")
            else:
                with get_session() as db:
                    service = RestwertService(db)
                    user_id = st.session_state.get("user_id")

                    anfrage = service.anfrage_erstellen(
                        projekt_id=projekt_id,
                        fahrzeug_id=fahrzeug_id,
                        kennzeichen=kennzeichen,
                        hersteller=hersteller,
                        modell=modell,
                        baujahr=baujahr,
                        erstzulassung=erstzulassung,
                        kilometerstand=kilometerstand,
                        hubraum=hubraum,
                        leistung_kw=leistung_kw,
                        kraftstoff=kraftstoff,
                        getriebe=getriebe,
                        farbe=farbe,
                        unfallschaden_beschreibung=unfallschaden,
                        vorschaeden=vorschaeden,
                        vorschaeden_beschreibung=vorschaeden_beschr,
                        tuev_bis=tuev_bis,
                        fahrbereit=fahrbereit,
                        schluessel_vorhanden=schluessel,
                        fahrzeugbrief_vorhanden=brief,
                        wiederbeschaffungswert=Decimal(str(wiederbeschaffungswert)) if wiederbeschaffungswert else None,
                        reparaturkosten=Decimal(str(reparaturkosten)) if reparaturkosten else None,
                        restwert_gutachter=Decimal(str(restwert_gutachter)) if restwert_gutachter else None,
                        mindestgebot=Decimal(str(mindestgebot)) if mindestgebot else None,
                        standort_adresse=standort_adresse,
                        standort_plz=standort_plz,
                        standort_ort=standort_ort,
                        standort_kontakt=standort_kontakt,
                        standort_telefon=standort_telefon,
                        besichtigung_moeglich_ab=besichtigung_von,
                        besichtigung_moeglich_bis=besichtigung_bis,
                        besichtigung_zeiten=besichtigung_zeiten,
                        anfrage_gueltig_bis=anfrage_gueltig_bis,
                        erstellt_von_user_id=user_id
                    )

                    st.success(f"Restwertanfrage erstellt!")


def _render_angebote(projekt_id: int):
    """Zeigt Angebotsvergleich"""
    st.subheader("Angebotsvergleich")

    with get_session() as db:
        service = RestwertService(db)
        anfragen = service.anfragen_fuer_projekt(projekt_id)

        if not anfragen:
            st.info("Keine Anfragen vorhanden")
            return

        anfrage_options = {
            a.id: f"{a.hersteller} {a.modell} - {a.kennzeichen}"
            for a in anfragen
        }

        anfrage_id = st.selectbox(
            "Anfrage auswählen",
            list(anfrage_options.keys()),
            format_func=lambda x: anfrage_options.get(x, "")
        )

        vergleich = service.vergleiche_angebote(anfrage_id)

        if vergleich['anzahl_angebote'] == 0:
            st.warning("Noch keine Angebote eingegangen")
            return

        # Kennzahlen
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Anzahl Angebote", vergleich['anzahl_angebote'])

        with col2:
            if vergleich['hoechstes_angebot']:
                st.metric(
                    "Höchstes Angebot",
                    f"{vergleich['hoechstes_angebot']['preis']:,.2f} €"
                )

        with col3:
            if vergleich['differenz_zum_gutachter'] is not None:
                diff = vergleich['differenz_zum_gutachter']
                st.metric(
                    "Differenz zum Gutachter",
                    f"{diff:+,.2f} €",
                    delta_color="normal" if diff >= 0 else "inverse"
                )

        # Empfehlung
        if vergleich['empfehlung']:
            st.info(vergleich['empfehlung'])

        # Angebotsliste
        st.markdown("### Alle Angebote")

        for angebot in vergleich['angebote']:
            ist_hoechstes = (
                vergleich['hoechstes_angebot'] and
                angebot.id == vergleich['hoechstes_angebot']['angebot'].id
            )

            with st.expander(
                f"{'⭐ ' if ist_hoechstes else ''}{angebot.anbieter_name} - {angebot.gebotener_preis:,.2f} EUR",
                expanded=ist_hoechstes
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Anbieter:** {angebot.anbieter_name}")
                    if angebot.anbieter_firma:
                        st.write(f"**Firma:** {angebot.anbieter_firma}")
                    st.write(f"**Ort:** {angebot.anbieter_plz} {angebot.anbieter_ort}")
                    st.write(f"**Telefon:** {angebot.anbieter_telefon or '-'}")
                    st.write(f"**E-Mail:** {angebot.anbieter_email or '-'}")

                with col2:
                    st.write(f"**Gebotener Preis:** {angebot.gebotener_preis:,.2f} EUR")
                    st.write(f"**Gültig bis:** {angebot.angebot_gueltig_bis.strftime('%d.%m.%Y') if angebot.angebot_gueltig_bis else '-'}")
                    st.write(f"**Abholung inklusive:** {'Ja' if angebot.abholung_inklusive else 'Nein'}")
                    st.write(f"**Zahlung bei Abholung:** {'Ja' if angebot.zahlung_bei_abholung else 'Nein'}")

                if angebot.bemerkungen:
                    st.write(f"**Bemerkungen:** {angebot.bemerkungen}")

                # Aktionen
                if not angebot.ist_akzeptiert and not angebot.abgelehnt:
                    col_a1, col_a2 = st.columns(2)

                    with col_a1:
                        if st.button("✅ Akzeptieren", key=f"accept_{angebot.id}", type="primary"):
                            service.angebot_akzeptieren(angebot.id)
                            st.success("Angebot akzeptiert!")
                            st.rerun()

                    with col_a2:
                        if st.button("❌ Ablehnen", key=f"reject_{angebot.id}"):
                            service.angebot_ablehnen(angebot.id)
                            st.rerun()

                elif angebot.ist_akzeptiert:
                    st.success("✅ Dieses Angebot wurde akzeptiert")


def _render_angebot_hinzufuegen(anfrage_id: int):
    """Formular zum Hinzufügen eines Angebots"""
    st.markdown("---")
    st.markdown("### Neues Angebot erfassen")

    with st.form(f"neues_angebot_{anfrage_id}"):
        col1, col2 = st.columns(2)

        with col1:
            anbieter_name = st.text_input("Anbieter/Kontakt *")
            anbieter_firma = st.text_input("Firma")
            anbieter_telefon = st.text_input("Telefon")
            anbieter_email = st.text_input("E-Mail")

        with col2:
            gebotener_preis = st.number_input("Gebotener Preis (EUR) *", min_value=0.0, step=100.0)
            angebot_gueltig_bis = st.date_input("Angebot gültig bis")
            abholung_inklusive = st.checkbox("Abholung inklusive", value=True)
            zahlung_bei_abholung = st.checkbox("Zahlung bei Abholung", value=True)

        bemerkungen = st.text_area("Bemerkungen")

        if st.form_submit_button("Angebot speichern"):
            if not anbieter_name or not gebotener_preis:
                st.error("Bitte Anbieter und Preis eingeben")
            else:
                with get_session() as db:
                    service = RestwertService(db)

                    angebot = service.angebot_hinzufuegen(
                        anfrage_id=anfrage_id,
                        anbieter_name=anbieter_name,
                        gebotener_preis=Decimal(str(gebotener_preis)),
                        anbieter_firma=anbieter_firma,
                        anbieter_telefon=anbieter_telefon,
                        anbieter_email=anbieter_email,
                        angebot_gueltig_bis=angebot_gueltig_bis,
                        abholung_inklusive=abholung_inklusive,
                        zahlung_bei_abholung=zahlung_bei_abholung,
                        bemerkungen=bemerkungen
                    )

                    del st.session_state["add_angebot_anfrage_id"]
                    st.success("Angebot hinzugefügt!")
                    st.rerun()


def _render_boersen():
    """Zeigt verfügbare Restwertbörsen"""
    st.subheader("Restwertbörsen")

    st.info("Nutzen Sie diese Plattformen, um Restwertangebote einzuholen.")

    with get_session() as db:
        service = RestwertService(db)

        for boerse in service.RESTWERBOERSEN:
            with st.expander(f"🌐 {boerse['name']}"):
                st.write(f"**Beschreibung:** {boerse['beschreibung']}")
                st.write(f"**Website:** [{boerse['url']}]({boerse['url']})")

                st.markdown("""
                **Typischer Ablauf:**
                1. Registrierung auf der Plattform
                2. Fahrzeugdaten eingeben (aus Ihrer Anfrage übernehmen)
                3. Fotos hochladen
                4. Angebote abwarten (meist 24-48 Stunden)
                5. Angebote hier erfassen und vergleichen
                """)


# Import für datetime
from datetime import datetime
