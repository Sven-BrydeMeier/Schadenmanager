"""
Werkzeuge-Seite mit Vorlagen, Checklisten, Notizen und weiteren Tools
"""
import streamlit as st
from datetime import datetime
from decimal import Decimal

from src.services.dokumentenvorlagen import get_dokumentenvorlagen_service
from src.services.schmerzensgeld import get_schmerzensgeld_rechner
from src.services.checklisten import get_checklisten_service, CHECKLISTEN, ChecklistenItem
from src.services.fahrzeugdatenbank import get_fahrzeugdatenbank
from src.models import UnfallProjekt, Notiz
from src.config.database import get_session


def render_werkzeuge():
    """Rendert die Werkzeuge-Seite"""

    st.markdown("## Werkzeuge")

    tabs = st.tabs([
        "Dokumentenvorlagen",
        "Schmerzensgeldrechner",
        "Checklisten",
        "Notizen",
        "Fahrzeugdatenbank"
    ])

    with tabs[0]:
        _render_dokumentenvorlagen()

    with tabs[1]:
        _render_schmerzensgeldrechner()

    with tabs[2]:
        _render_checklisten()

    with tabs[3]:
        _render_notizen()

    with tabs[4]:
        _render_fahrzeugdatenbank()


def _render_dokumentenvorlagen():
    """Rendert die Dokumentenvorlagen"""

    st.markdown("### Dokumentenvorlagen")
    st.caption("Erstellen Sie Dokumente aus Vorlagen für das aktive Projekt")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Bitte wählen Sie zuerst ein Projekt aus.")
        return

    with get_session() as db:
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == aktives_projekt_id
        ).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        st.info(f"**Aktives Projekt:** {projekt.aktenzeichen or projekt.projektnummer}")

        vorlagen_service = get_dokumentenvorlagen_service()
        vorlagen = vorlagen_service.get_verfuegbare_vorlagen()

        # Vorlage auswählen
        col1, col2 = st.columns([2, 1])

        with col1:
            auswahl = st.selectbox(
                "Vorlage auswählen",
                options=list(vorlagen.keys()),
                format_func=lambda x: vorlagen[x]
            )

        with col2:
            st.markdown("")
            st.markdown("")

        # Zusätzliche Daten je nach Vorlage
        zusatz_daten = {}

        if auswahl == "widerspruch":
            st.markdown("#### Zusätzliche Angaben für Widerspruch")
            zusatz_daten["kuerzung_datum"] = st.date_input("Datum des Kürzungsschreibens").strftime("%d.%m.%Y")
            zusatz_daten["kuerzungen"] = st.text_area("Gekürzte Positionen")
            zusatz_daten["kuerzung_begruendung"] = st.text_area("Begründung des Widerspruchs")
            zusatz_daten["offener_betrag"] = st.text_input("Offener Betrag (EUR)")

        elif auswahl == "mahnung":
            st.markdown("#### Zusätzliche Angaben für Mahnung")
            zusatz_daten["offener_betrag"] = st.text_input("Offener Betrag (EUR)")
            zusatz_daten["zahlungsfrist"] = st.date_input("Zahlungsfrist").strftime("%d.%m.%Y")

        elif auswahl == "abrechnung_fiktiv":
            st.markdown("#### Zusätzliche Angaben für fiktive Abrechnung")
            zusatz_daten["reparaturkosten_netto"] = st.text_input("Reparaturkosten netto (EUR)")
            zusatz_daten["wertminderung"] = st.text_input("Wertminderung (EUR)", value="0")
            zusatz_daten["ausfall_tage"] = st.number_input("Ausfalltage", min_value=0, value=7)
            zusatz_daten["nutzungsausfall"] = st.text_input("Nutzungsausfall (EUR)")
            zusatz_daten["gutachterkosten"] = st.text_input("Gutachterkosten (EUR)")
            zusatz_daten["kostenpauschale"] = st.text_input("Kostenpauschale (EUR)", value="25")
            zusatz_daten["gesamtforderung"] = st.text_input("Gesamtforderung (EUR)")

        elif auswahl == "abtretung":
            st.markdown("#### Zusätzliche Angaben für Abtretung")
            zusatz_daten["abtretung_empfaenger"] = st.text_input("Abtretungsempfänger (Werkstatt/Autovermietung)")

        elif auswahl == "schweigepflicht":
            st.markdown("#### Zusätzliche Angaben")
            zusatz_daten["geburtsdatum"] = st.date_input("Geburtsdatum des Mandanten").strftime("%d.%m.%Y")

        # Schadenspositionen für Anspruchsschreiben
        if auswahl == "anspruchsschreiben":
            positionen_text = []
            for kp in projekt.kostenpositionen:
                positionen_text.append(f"- {kp.bezeichnung}: {float(kp.betrag_gefordert or 0):,.2f} EUR")
            zusatz_daten["schadenspositionen"] = "\n".join(positionen_text) if positionen_text else "- Noch keine Positionen erfasst"

        # Dokument generieren
        if st.button("Dokument generieren", type="primary", use_container_width=True):
            try:
                dokument = vorlagen_service.generiere_dokument(auswahl, projekt, zusatz_daten)

                st.markdown("---")
                st.markdown("### Generiertes Dokument")

                st.text_area("", dokument, height=500)

                # Download-Button
                st.download_button(
                    "📥 Als Textdatei herunterladen",
                    data=dokument,
                    file_name=f"{auswahl}_{projekt.aktenzeichen or projekt.projektnummer}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Fehler beim Generieren: {e}")


def _render_schmerzensgeldrechner():
    """Rendert den Schmerzensgeldrechner"""

    st.markdown("### Schmerzensgeldrechner")
    st.caption("Berechnung basierend auf Verletzungsart und Heilungsdauer")

    rechner = get_schmerzensgeld_rechner()
    kategorien = rechner.get_verletzungskategorien()

    # Verletzungen auswählen
    st.markdown("#### Verletzungen auswählen")

    verletzungen = st.multiselect(
        "Verletzungen",
        options=list(kategorien.keys()),
        format_func=lambda x: f"{kategorien[x]['name']} ({kategorien[x]['min_betrag']}-{kategorien[x]['max_betrag']} €)"
    )

    if verletzungen:
        for v in verletzungen:
            st.caption(f"• {kategorien[v]['beschreibung']}")

    st.markdown("---")

    # Parameter
    col1, col2 = st.columns(2)

    with col1:
        heilungsdauer = st.selectbox(
            "Heilungsdauer",
            options=[
                "bis_1_woche",
                "1_bis_4_wochen",
                "1_bis_3_monate",
                "3_bis_6_monate",
                "6_bis_12_monate",
                "ueber_12_monate",
                "dauerhaft"
            ],
            format_func=lambda x: {
                "bis_1_woche": "Bis 1 Woche",
                "1_bis_4_wochen": "1-4 Wochen",
                "1_bis_3_monate": "1-3 Monate",
                "3_bis_6_monate": "3-6 Monate",
                "6_bis_12_monate": "6-12 Monate",
                "ueber_12_monate": "Über 12 Monate",
                "dauerhaft": "Dauerhaft",
            }.get(x, x),
            index=2
        )

        alter = st.selectbox(
            "Alter des Geschädigten",
            options=["kind", "jung", "mittel", "aelter"],
            format_func=lambda x: {
                "kind": "Kind (unter 18)",
                "jung": "Jung (18-30)",
                "mittel": "Mittel (30-60)",
                "aelter": "Älter (über 60)"
            }.get(x, x),
            index=2
        )

    with col2:
        beruf = st.selectbox(
            "Berufliche Beeinträchtigung",
            options=["keine", "leicht", "mittel", "schwer", "berufsunfaehig"],
            format_func=lambda x: {
                "keine": "Keine",
                "leicht": "Leicht",
                "mittel": "Mittel",
                "schwer": "Schwer",
                "berufsunfaehig": "Berufsunfähig"
            }.get(x, x)
        )

        mitverschulden = st.slider("Mitverschulden (%)", 0, 50, 0, step=10)

    col1, col2 = st.columns(2)

    with col1:
        krankenhaus_tage = st.number_input("Krankenhaustage", min_value=0, value=0)

    with col2:
        operationen = st.number_input("Anzahl Operationen", min_value=0, value=0)

    dauerfolgen = st.checkbox("Dauerhafte Folgen / Behinderung")

    # Berechnung
    if st.button("Schmerzensgeld berechnen", type="primary", use_container_width=True):
        ergebnis = rechner.berechne_schmerzensgeld(
            verletzungen=verletzungen,
            heilungsdauer=heilungsdauer,
            alter_kategorie=alter,
            beruf_beeintraechtigung=beruf,
            mitverschulden_prozent=mitverschulden,
            krankenhausaufenthalt_tage=krankenhaus_tage,
            operationen=operationen,
            dauerfolgen=dauerfolgen
        )

        st.session_state["schmerzensgeld_ergebnis"] = ergebnis

    # Ergebnis anzeigen
    if "schmerzensgeld_ergebnis" in st.session_state:
        ergebnis = st.session_state["schmerzensgeld_ergebnis"]

        st.markdown("---")
        st.markdown("### Ergebnis")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Minimum", f"{float(ergebnis['empfehlung_min']):,.0f} €")

        with col2:
            st.markdown(
                f"""
                <div style="background-color: #dcfce7; border-radius: 10px; padding: 15px; text-align: center;">
                    <h4 style="color: #16a34a; margin: 0;">Empfehlung</h4>
                    <h2 style="color: #16a34a; margin: 5px 0;">{float(ergebnis['empfehlung']):,.0f} €</h2>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:
            st.metric("Maximum", f"{float(ergebnis['empfehlung_max']):,.0f} €")

        # Hinweise
        if ergebnis["hinweise"]:
            st.markdown("#### Hinweise")
            for hinweis in ergebnis["hinweise"]:
                st.info(hinweis)

        # Details
        with st.expander("Berechnungsdetails"):
            st.markdown(f"**Basisbetrag:** {float(ergebnis['basis_betrag']):,.0f} €")
            st.markdown(f"**Gesamtfaktor:** {ergebnis['gesamtfaktor']}")

            for key, faktor in ergebnis["faktoren"].items():
                st.markdown(f"• {faktor['beschreibung']}: {faktor['wert']}")


def _render_checklisten():
    """Rendert die Checklisten"""

    st.markdown("### Checklisten")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Bitte wählen Sie zuerst ein Projekt aus.")

        # Verfügbare Checklisten anzeigen
        st.markdown("#### Verfügbare Checklistentypen")
        for key, daten in CHECKLISTEN.items():
            with st.expander(daten["name"]):
                st.caption(daten["beschreibung"])
                for kat_key, kategorie in daten["kategorien"].items():
                    st.markdown(f"**{kategorie['name']}**")
                    for item in kategorie["items"]:
                        st.markdown(f"- {item['titel']}")
        return

    with get_session() as db:
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == aktives_projekt_id
        ).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        st.info(f"**Aktives Projekt:** {projekt.aktenzeichen or projekt.projektnummer}")

        checklisten_service = get_checklisten_service(db)

        # Bestehende Checkliste laden
        items = db.query(ChecklistenItem).filter(
            ChecklistenItem.unfallprojekt_id == aktives_projekt_id
        ).order_by(ChecklistenItem.reihenfolge).all()

        if items:
            # Fortschritt anzeigen
            fortschritt = checklisten_service.get_fortschritt(aktives_projekt_id)
            st.progress(fortschritt["prozent"] / 100, text=f"Fortschritt: {fortschritt['erledigt']}/{fortschritt['gesamt']} ({fortschritt['prozent']}%)")

            # Nach Kategorie gruppieren
            kategorien = {}
            for item in items:
                if item.kategorie not in kategorien:
                    kategorien[item.kategorie] = []
                kategorien[item.kategorie].append(item)

            # Items anzeigen
            for kategorie, kat_items in kategorien.items():
                with st.expander(f"**{kategorie}** ({len([i for i in kat_items if i.erledigt])}/{len(kat_items)})"):
                    for item in kat_items:
                        col1, col2 = st.columns([4, 1])

                        with col1:
                            if item.erledigt:
                                st.markdown(f"✅ ~~{item.titel}~~")
                            else:
                                st.markdown(f"⬜ {item.titel}")

                            if item.beschreibung:
                                st.caption(item.beschreibung)

                        with col2:
                            if not item.erledigt:
                                if st.button("Erledigt", key=f"check_{item.id}"):
                                    checklisten_service.item_erledigen(
                                        item.id,
                                        st.session_state.get("user_id")
                                    )
                                    st.rerun()

        else:
            # Neue Checkliste anlegen
            st.markdown("#### Checkliste anlegen")

            verfuegbar = checklisten_service.get_verfuegbare_checklisten()

            auswahl = st.selectbox(
                "Checklistentyp",
                options=list(verfuegbar.keys()),
                format_func=lambda x: verfuegbar[x]["name"]
            )

            st.caption(verfuegbar[auswahl]["beschreibung"])

            if st.button("Checkliste anlegen", type="primary"):
                checklisten_service.initialisiere_checkliste(aktives_projekt_id, auswahl)
                st.success("Checkliste wurde angelegt!")
                st.rerun()


def _render_notizen():
    """Rendert das Notizen-System"""

    st.markdown("### Projekt-Notizen")

    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Bitte wählen Sie zuerst ein Projekt aus.")
        return

    with get_session() as db:
        projekt = db.query(UnfallProjekt).filter(
            UnfallProjekt.id == aktives_projekt_id
        ).first()

        if not projekt:
            st.error("Projekt nicht gefunden.")
            return

        st.info(f"**Aktives Projekt:** {projekt.aktenzeichen or projekt.projektnummer}")

        # Neue Notiz erstellen
        with st.expander("➕ Neue Notiz erstellen", expanded=False):
            with st.form("neue_notiz"):
                titel = st.text_input("Titel (optional)")

                kategorie = st.selectbox(
                    "Kategorie",
                    ["intern", "telefonat", "email", "wichtig", "erinnerung", "mandant"],
                    format_func=lambda x: {
                        "intern": "Interne Notiz",
                        "telefonat": "Telefonat",
                        "email": "E-Mail",
                        "wichtig": "Wichtig",
                        "erinnerung": "Erinnerung",
                        "mandant": "Mandantengespräch"
                    }.get(x, x)
                )

                inhalt = st.text_area("Inhalt*", height=150)

                col1, col2 = st.columns(2)
                with col1:
                    wichtig = st.checkbox("Als wichtig markieren")
                with col2:
                    angeheftet = st.checkbox("Oben anpinnen")

                if st.form_submit_button("Notiz speichern", use_container_width=True):
                    if not inhalt:
                        st.error("Bitte Inhalt eingeben.")
                    else:
                        notiz = Notiz(
                            unfallprojekt_id=aktives_projekt_id,
                            erstellt_von_user_id=st.session_state.get("user_id"),
                            titel=titel,
                            inhalt=inhalt,
                            kategorie=kategorie,
                            wichtig=wichtig,
                            angeheftet=angeheftet
                        )
                        db.add(notiz)
                        db.flush()
                        st.success("Notiz wurde gespeichert!")
                        st.rerun()

        st.markdown("---")

        # Notizen anzeigen
        notizen = db.query(Notiz).filter(
            Notiz.unfallprojekt_id == aktives_projekt_id
        ).order_by(Notiz.angeheftet.desc(), Notiz.erstellt_am.desc()).all()

        if not notizen:
            st.info("Noch keine Notizen vorhanden.")
            return

        for notiz in notizen:
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    # Icon basierend auf Kategorie
                    icons = {
                        "intern": "📝",
                        "telefonat": "📞",
                        "email": "📧",
                        "wichtig": "⚠️",
                        "erinnerung": "🔔",
                        "mandant": "👤"
                    }
                    icon = icons.get(notiz.kategorie, "📝")

                    titel_text = notiz.titel if notiz.titel else notiz.kategorie_anzeige
                    if notiz.angeheftet:
                        titel_text = f"📌 {titel_text}"
                    if notiz.wichtig:
                        titel_text = f"🔴 {titel_text}"

                    st.markdown(f"**{icon} {titel_text}**")
                    st.caption(f"{notiz.erstellt_am.strftime('%d.%m.%Y %H:%M')} - {notiz.erstellt_von.voller_name if notiz.erstellt_von else 'Unbekannt'}")
                    st.text(notiz.inhalt[:200] + "..." if len(notiz.inhalt) > 200 else notiz.inhalt)

                with col2:
                    if st.button("🗑️", key=f"del_notiz_{notiz.id}"):
                        db.delete(notiz)
                        db.flush()
                        st.rerun()

                st.markdown("---")


def _render_fahrzeugdatenbank():
    """Rendert die Fahrzeugdatenbank"""

    st.markdown("### Fahrzeugdatenbank")
    st.caption("Neupreise und Zeitwertberechnung")

    fzdb = get_fahrzeugdatenbank()

    tabs = st.tabs(["Fahrzeugsuche", "Zeitwertrechner"])

    with tabs[0]:
        st.markdown("#### Fahrzeug suchen")

        col1, col2, col3 = st.columns(3)

        with col1:
            hersteller = st.selectbox("Hersteller", [""] + fzdb.get_hersteller())

        with col2:
            if hersteller:
                modelle = fzdb.get_modelle(hersteller)
                modell = st.selectbox("Modell", [""] + modelle)
            else:
                modell = ""
                st.selectbox("Modell", ["Bitte Hersteller wählen"], disabled=True)

        with col3:
            if hersteller and modell:
                varianten = fzdb.get_varianten(hersteller, modell)
                variante = st.selectbox(
                    "Variante",
                    [""] + list(varianten.keys()),
                    format_func=lambda x: f"{x} ({varianten[x]:,} €)" if x else "Alle anzeigen"
                )
            else:
                variante = ""
                st.selectbox("Variante", ["Bitte Modell wählen"], disabled=True)

        if hersteller and modell:
            daten = fzdb.get_fahrzeugdaten(hersteller, modell)
            if daten:
                st.markdown("---")
                st.markdown(f"**{hersteller} {modell}**")
                st.markdown(f"Segment: {daten['segment']}")
                st.markdown(f"Nutzungsausfall-Gruppe: {daten['nutzungsausfall_gruppe']}")
                st.markdown(f"Basispreis: {daten['neupreis_basis']:,} €")

                if variante and variante in daten["varianten"]:
                    st.metric(f"Neupreis {variante}", f"{daten['varianten'][variante]:,} €")

    with tabs[1]:
        st.markdown("#### Zeitwert berechnen")

        col1, col2 = st.columns(2)

        with col1:
            neupreis = st.number_input("Neupreis (€)", min_value=5000, max_value=500000, value=30000, step=1000)
            alter_jahre = st.number_input("Alter (Jahre)", min_value=0, max_value=20, value=3)

        with col2:
            laufleistung = st.number_input("Laufleistung (km)", min_value=0, max_value=500000, value=45000, step=5000)
            zustand = st.selectbox(
                "Zustand",
                ["sehr_gut", "gut", "normal", "schlecht", "sehr_schlecht"],
                index=2,
                format_func=lambda x: {
                    "sehr_gut": "Sehr gut",
                    "gut": "Gut",
                    "normal": "Normal",
                    "schlecht": "Schlecht",
                    "sehr_schlecht": "Sehr schlecht"
                }.get(x, x)
            )

        if st.button("Zeitwert berechnen", type="primary"):
            ergebnis = fzdb.berechne_zeitwert(
                Decimal(str(neupreis)),
                alter_jahre,
                laufleistung,
                zustand
            )

            st.markdown("---")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Neupreis", f"{neupreis:,} €")

            with col2:
                st.metric("Zeitwert", f"{float(ergebnis['zeitwert']):,.0f} €")

            with col3:
                st.metric("Wertverlust", f"{ergebnis['wertverlust_prozent']}%")

            with st.expander("Berechnungsdetails"):
                st.markdown(f"**Basisfaktor (Alter):** {ergebnis['basis_faktor']}")
                st.markdown(f"**KM-Faktor:** {ergebnis['km_faktor']}")
                st.markdown(f"**Zustandsfaktor:** {ergebnis['zustand_faktor']}")
