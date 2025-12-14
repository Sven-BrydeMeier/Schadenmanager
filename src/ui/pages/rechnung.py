"""
Rechnungsstellung/Fakturierung UI-Seite
Erstellung und Verwaltung von Rechnungen
"""
import streamlit as st
from datetime import date
from decimal import Decimal

from src.config.database import get_session
from src.services.rechnung import RechnungService, Rechnung, RechnungsStatus, RechnungsTyp


def render_rechnungen():
    """Rendert die Rechnungs-Seite"""
    st.title("💶 Rechnungsstellung")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Übersicht", "Neue Rechnung", "Offene Posten", "Bankverbindung"
    ])

    with tab1:
        _render_uebersicht()

    with tab2:
        _render_neue_rechnung()

    with tab3:
        _render_offene_posten()

    with tab4:
        _render_bankverbindung()


def _render_uebersicht():
    """Rechnungsübersicht"""
    st.subheader("Rechnungsübersicht")

    with get_session() as db:
        # Statistiken
        alle_rechnungen = db.query(Rechnung).order_by(Rechnung.rechnungsdatum.desc()).limit(100).all()

        if not alle_rechnungen:
            st.info("Noch keine Rechnungen erstellt")
            return

        # Kennzahlen
        col1, col2, col3, col4 = st.columns(4)

        offen = [r for r in alle_rechnungen if r.status in [
            RechnungsStatus.ERSTELLT, RechnungsStatus.VERSENDET,
            RechnungsStatus.TEILBEZAHLT, RechnungsStatus.MAHNUNG
        ]]
        bezahlt = [r for r in alle_rechnungen if r.status == RechnungsStatus.BEZAHLT]
        ueberfaellig = [r for r in offen if r.ist_ueberfaellig]

        with col1:
            st.metric("Gesamt", len(alle_rechnungen))

        with col2:
            summe_offen = sum(r.offener_betrag for r in offen)
            st.metric("Offen", f"{summe_offen:,.2f} €")

        with col3:
            st.metric("Überfällig", len(ueberfaellig))

        with col4:
            summe_bezahlt = sum(r.brutto_summe for r in bezahlt)
            st.metric("Bezahlt (Summe)", f"{summe_bezahlt:,.2f} €")

        st.markdown("---")

        # Filter
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            status_filter = st.multiselect(
                "Status filtern",
                [s for s in RechnungsStatus],
                format_func=lambda s: {
                    RechnungsStatus.ENTWURF: "Entwurf",
                    RechnungsStatus.ERSTELLT: "Erstellt",
                    RechnungsStatus.VERSENDET: "Versendet",
                    RechnungsStatus.BEZAHLT: "Bezahlt",
                    RechnungsStatus.TEILBEZAHLT: "Teilbezahlt",
                    RechnungsStatus.MAHNUNG: "Mahnung",
                    RechnungsStatus.STORNIERT: "Storniert"
                }.get(s, str(s))
            )

        # Rechnungsliste
        gefiltert = alle_rechnungen
        if status_filter:
            gefiltert = [r for r in alle_rechnungen if r.status in status_filter]

        for rechnung in gefiltert:
            with st.expander(
                f"{rechnung.status_anzeige} | {rechnung.rechnungsnummer} - {rechnung.empfaenger_name}",
                expanded=rechnung.ist_ueberfaellig
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Datum:** {rechnung.rechnungsdatum.strftime('%d.%m.%Y')}")
                    st.write(f"**Fällig:** {rechnung.faellig_am.strftime('%d.%m.%Y') if rechnung.faellig_am else '-'}")
                    st.write(f"**Typ:** {rechnung.rechnungs_typ.value}")

                    if rechnung.ist_ueberfaellig:
                        tage_ueber = (date.today() - rechnung.faellig_am).days
                        st.error(f"⚠️ {tage_ueber} Tage überfällig!")

                with col2:
                    st.write(f"**Netto:** {rechnung.netto_summe:,.2f} EUR")
                    st.write(f"**MwSt. ({rechnung.mwst_satz}%):** {rechnung.mwst_betrag:,.2f} EUR")
                    st.write(f"**Brutto:** {rechnung.brutto_summe:,.2f} EUR")

                    if rechnung.bereits_bezahlt and rechnung.bereits_bezahlt > 0:
                        st.write(f"**Bezahlt:** {rechnung.bereits_bezahlt:,.2f} EUR")
                        st.write(f"**Offen:** {rechnung.offener_betrag:,.2f} EUR")

                # Positionen
                if rechnung.positionen:
                    st.markdown("**Positionen:**")
                    for pos in rechnung.positionen:
                        menge = pos.get('menge', 1)
                        einzelpreis = pos.get('einzelpreis', 0)
                        gesamt = menge * einzelpreis
                        st.write(f"- {pos.get('beschreibung', 'Position')}: {gesamt:.2f} EUR")

                # Aktionen
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)

                with col_a1:
                    if rechnung.status == RechnungsStatus.ENTWURF:
                        if st.button("✅ Finalisieren", key=f"fin_{rechnung.id}"):
                            rechnung.status = RechnungsStatus.ERSTELLT
                            db.commit()
                            st.rerun()

                with col_a2:
                    if rechnung.status == RechnungsStatus.ERSTELLT:
                        if st.button("📤 Als versendet", key=f"send_{rechnung.id}"):
                            rechnung.status = RechnungsStatus.VERSENDET
                            db.commit()
                            st.rerun()

                with col_a3:
                    if rechnung.status not in [RechnungsStatus.BEZAHLT, RechnungsStatus.STORNIERT]:
                        if st.button("💰 Zahlung", key=f"pay_{rechnung.id}"):
                            st.session_state[f"zahlung_{rechnung.id}"] = True

                with col_a4:
                    # PDF-Text
                    service = RechnungService(db)
                    pdf_text = service.generiere_rechnungs_pdf_text(rechnung)
                    st.download_button(
                        "📄 Text",
                        data=pdf_text,
                        file_name=f"Rechnung_{rechnung.rechnungsnummer}.txt",
                        mime="text/plain",
                        key=f"pdf_{rechnung.id}"
                    )

                # Zahlung erfassen
                if st.session_state.get(f"zahlung_{rechnung.id}"):
                    with st.form(f"zahlung_form_{rechnung.id}"):
                        betrag = st.number_input(
                            "Betrag",
                            min_value=0.01,
                            value=float(rechnung.offener_betrag),
                            step=0.01
                        )
                        zahlungsdatum = st.date_input("Zahlungsdatum", value=date.today())

                        if st.form_submit_button("Zahlung erfassen"):
                            service = RechnungService(db)
                            service.zahlung_erfassen(
                                rechnung.id,
                                Decimal(str(betrag)),
                                zahlungsdatum
                            )
                            del st.session_state[f"zahlung_{rechnung.id}"]
                            st.success("Zahlung erfasst!")
                            st.rerun()


def _render_neue_rechnung():
    """Formular für neue Rechnung"""
    st.subheader("Neue Rechnung erstellen")

    with st.form("neue_rechnung"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Empfänger**")
            empfaenger_name = st.text_input("Name *")
            empfaenger_adresse = st.text_input("Straße")
            col_plz, col_ort = st.columns([1, 2])
            with col_plz:
                empfaenger_plz = st.text_input("PLZ")
            with col_ort:
                empfaenger_ort = st.text_input("Ort")

        with col2:
            st.markdown("**Rechnungsdaten**")
            rechnungs_typ = st.selectbox(
                "Rechnungstyp",
                [t for t in RechnungsTyp],
                format_func=lambda t: {
                    RechnungsTyp.HONORAR: "Honorar",
                    RechnungsTyp.AUSLAGEN: "Auslagen",
                    RechnungsTyp.GEBUEHREN: "Gebühren (RVG)",
                    RechnungsTyp.GUTSCHRIFT: "Gutschrift",
                    RechnungsTyp.ABSCHLAG: "Abschlagsrechnung",
                    RechnungsTyp.SCHLUSSRECHNUNG: "Schlussrechnung"
                }.get(t, str(t))
            )

            zahlungsziel = st.number_input("Zahlungsziel (Tage)", min_value=1, value=14)
            mwst_satz = st.number_input("MwSt.-Satz (%)", min_value=0.0, max_value=100.0, value=19.0)

        # Projekt zuordnen
        with get_session() as db:
            from src.models import UnfallProjekt
            projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).limit(50).all()

            projekt_options = {p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}" for p in projekte}
            projekt_id = st.selectbox(
                "Projekt zuordnen (optional)",
                [None] + list(projekt_options.keys()),
                format_func=lambda x: "-- Kein Projekt --" if x is None else projekt_options.get(x, "")
            )

        # Positionen
        st.markdown("**Positionen**")

        positionen = []
        for i in range(5):
            col_p1, col_p2, col_p3, col_p4 = st.columns([4, 1, 2, 2])

            with col_p1:
                beschreibung = st.text_input(f"Beschreibung", key=f"pos_beschr_{i}")
            with col_p2:
                menge = st.number_input("Menge", min_value=0.0, value=1.0, key=f"pos_menge_{i}")
            with col_p3:
                einheit = st.selectbox("Einheit", ["pauschal", "Stunden", "Stück", "km"], key=f"pos_einheit_{i}")
            with col_p4:
                einzelpreis = st.number_input("Einzelpreis", min_value=0.0, step=10.0, key=f"pos_preis_{i}")

            if beschreibung and einzelpreis > 0:
                positionen.append({
                    "beschreibung": beschreibung,
                    "menge": menge,
                    "einheit": einheit,
                    "einzelpreis": einzelpreis
                })

        # Texte
        betreff = st.text_input("Betreff")
        einleitungstext = st.text_area("Einleitungstext", height=80)
        schlusstext = st.text_area("Schlusstext", height=80, value="Bitte überweisen Sie den Betrag bis zum Zahlungsziel auf unser Konto.")

        submitted = st.form_submit_button("Rechnung erstellen", type="primary")

        if submitted:
            if not empfaenger_name:
                st.error("Bitte Empfängername eingeben")
            elif not positionen:
                st.error("Bitte mindestens eine Position eingeben")
            else:
                with get_session() as db:
                    service = RechnungService(db)
                    user_id = st.session_state.get("user_id")

                    rechnung = service.rechnung_erstellen(
                        empfaenger_name=empfaenger_name,
                        positionen=positionen,
                        projekt_id=projekt_id,
                        rechnungs_typ=rechnungs_typ,
                        zahlungsziel_tage=zahlungsziel,
                        mwst_satz=Decimal(str(mwst_satz)),
                        empfaenger_adresse=empfaenger_adresse,
                        empfaenger_plz=empfaenger_plz,
                        empfaenger_ort=empfaenger_ort,
                        betreff=betreff,
                        einleitungstext=einleitungstext,
                        schlusstext=schlusstext,
                        erstellt_von_user_id=user_id
                    )

                    st.success(f"Rechnung {rechnung.rechnungsnummer} erstellt!")
                    st.info(f"Bruttobetrag: {rechnung.brutto_summe:,.2f} EUR")


def _render_offene_posten():
    """Übersicht offener Posten"""
    st.subheader("Offene Posten (OP-Liste)")

    with get_session() as db:
        service = RechnungService(db)
        offene = service.offene_rechnungen()
        ueberfaellige = service.ueberfaellige_rechnungen()

        if not offene:
            st.success("Keine offenen Rechnungen!")
            return

        # Warnung bei überfälligen
        if ueberfaellige:
            st.error(f"⚠️ {len(ueberfaellige)} überfällige Rechnung(en)!")

        # Summen
        summe_offen = sum(r.offener_betrag for r in offene)
        summe_ueberfaellig = sum(r.offener_betrag for r in ueberfaellige)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Gesamt offen", f"{summe_offen:,.2f} EUR")
        with col2:
            st.metric("Davon überfällig", f"{summe_ueberfaellig:,.2f} EUR")

        # Tabelle
        st.markdown("---")

        for rechnung in offene:
            ist_ueberfaellig = rechnung in ueberfaellige
            icon = "🔴" if ist_ueberfaellig else "🟡"

            st.write(
                f"{icon} **{rechnung.rechnungsnummer}** | "
                f"{rechnung.empfaenger_name} | "
                f"Fällig: {rechnung.faellig_am.strftime('%d.%m.%Y') if rechnung.faellig_am else '-'} | "
                f"**{rechnung.offener_betrag:,.2f} EUR**"
            )


def _render_bankverbindung():
    """Bankverbindung für Rechnungen konfigurieren"""
    st.subheader("Bankverbindung konfigurieren")

    st.info("Diese Daten werden auf zukünftigen Rechnungen verwendet.")

    bank_iban = st.text_input("IBAN", value=st.session_state.get("bank_iban", ""))
    bank_bic = st.text_input("BIC", value=st.session_state.get("bank_bic", ""))
    bank_name = st.text_input("Bank", value=st.session_state.get("bank_name", ""))
    kontoinhaber = st.text_input("Kontoinhaber", value=st.session_state.get("kontoinhaber", ""))

    if st.button("Speichern"):
        st.session_state["bank_iban"] = bank_iban
        st.session_state["bank_bic"] = bank_bic
        st.session_state["bank_name"] = bank_name
        st.session_state["kontoinhaber"] = kontoinhaber
        st.success("Bankverbindung gespeichert!")
