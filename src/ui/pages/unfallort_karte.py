"""
Unfallort-Karte UI-Seite
Geolocation und Kartenvisualisierung
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.unfallort_karte import (
    UnfallortService, StrassenTyp, UnfallortTyp, Unfallort
)


def render_unfallort_karte():
    """Rendert die Unfallort-Karte-Seite"""
    st.title("🗺️ Unfallort-Karte")

    st.info("""
    Erfassen Sie den genauen Unfallort mit Koordinaten und Kartenansicht.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Unfallort erfassen", "Karte anzeigen", "Statistik"
    ])

    with tab1:
        _render_unfallort_erfassen()

    with tab2:
        _render_karte()

    with tab3:
        _render_statistik()


def _render_unfallort_erfassen():
    """Unfallort erfassen"""
    st.subheader("Unfallort erfassen")

    with get_session() as db:
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        projekt_options = {
            p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
            for p in projekte
        }
        projekt_id = st.selectbox(
            "Projekt auswählen",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, "")
        )

        # Prüfen ob bereits Unfallort vorhanden
        service = UnfallortService(db)
        existierend = service.unfallort_fuer_projekt(projekt_id)

        if existierend:
            st.info(f"Unfallort bereits erfasst: {existierend.vollstaendige_adresse}")

        st.markdown("### Adresse")

        col1, col2 = st.columns(2)

        with col1:
            strasse = st.text_input(
                "Straße",
                value=existierend.strasse if existierend else ""
            )
            hausnummer = st.text_input(
                "Hausnummer",
                value=existierend.hausnummer if existierend else ""
            )
            plz = st.text_input(
                "PLZ",
                value=existierend.plz if existierend else ""
            )
            ort = st.text_input(
                "Ort",
                value=existierend.ort if existierend else ""
            )

        with col2:
            strassen_typ = st.selectbox(
                "Straßentyp",
                [t.value for t in StrassenTyp],
                index=list(StrassenTyp).index(existierend.strassen_typ) if existierend and existierend.strassen_typ else 0,
                format_func=lambda x: {
                    'AUTOBAHN': '🛣️ Autobahn',
                    'BUNDESSTRASSE': '🚗 Bundesstraße',
                    'LANDESSTRASSE': '🚙 Landesstraße',
                    'KREISSTRASSE': '🚐 Kreisstraße',
                    'INNERORTS': '🏘️ Innerorts',
                    'PARKPLATZ': '🅿️ Parkplatz',
                    'PRIVATGELAENDE': '🏠 Privatgelände',
                    'SONSTIGE': '📍 Sonstige'
                }.get(x, x)
            )

            unfallort_typ = st.selectbox(
                "Unfallorttyp",
                [t.value for t in UnfallortTyp],
                index=list(UnfallortTyp).index(existierend.unfallort_typ) if existierend and existierend.unfallort_typ else 0,
                format_func=lambda x: {
                    'KREUZUNG': '✚ Kreuzung',
                    'EINMUENDUNG': '⤴️ Einmündung',
                    'GERADE': '➡️ Gerade Strecke',
                    'KURVE': '↩️ Kurve',
                    'KREISVERKEHR': '🔄 Kreisverkehr',
                    'AUFFAHRT': '⬆️ Auffahrt',
                    'ABFAHRT': '⬇️ Abfahrt',
                    'BAUSTELLE': '🚧 Baustelle',
                    'SONSTIGE': '📍 Sonstige'
                }.get(x, x)
            )

            kreuzende_strasse = st.text_input(
                "Kreuzende Straße (falls Kreuzung)",
                value=existierend.kreuzende_strasse if existierend else ""
            )

        st.markdown("### Koordinaten")

        col_k1, col_k2 = st.columns(2)

        with col_k1:
            latitude = st.number_input(
                "Breitengrad (Latitude)",
                value=float(existierend.latitude) if existierend and existierend.latitude else 52.520,
                format="%.6f"
            )

        with col_k2:
            longitude = st.number_input(
                "Längengrad (Longitude)",
                value=float(existierend.longitude) if existierend and existierend.longitude else 13.405,
                format="%.6f"
            )

        # Geocoding-Button
        adresse_komplett = f"{strasse} {hausnummer}, {plz} {ort}"
        if st.button("🔍 Koordinaten aus Adresse ermitteln"):
            coords = service.koordinaten_aus_adresse(adresse_komplett)
            if coords:
                st.success(f"Koordinaten gefunden: {coords[0]}, {coords[1]}")
                st.info("Bitte die Koordinaten oben manuell eintragen.")
            else:
                st.warning("Keine Koordinaten gefunden. Bitte manuell eingeben.")

        st.markdown("### Bedingungen zum Unfallzeitpunkt")

        col_b1, col_b2 = st.columns(2)

        with col_b1:
            wetter_optionen = service.WETTER_OPTIONEN
            wetter = st.multiselect(
                "Wetterbedingungen",
                wetter_optionen,
                default=existierend.wetterbedingungen if existierend else []
            )

        with col_b2:
            strassen_optionen = service.STRASSEN_OPTIONEN
            strassenzustand = st.multiselect(
                "Straßenzustand",
                strassen_optionen,
                default=existierend.strassenzustand if existierend else []
            )

        beleuchtung = st.selectbox(
            "Beleuchtung",
            ["Tageslicht", "Dämmerung", "Dunkelheit (beleuchtet)", "Dunkelheit (unbeleuchtet)"],
            index=0
        )

        beschreibung = st.text_area(
            "Zusätzliche Beschreibung",
            value=existierend.beschreibung if existierend else ""
        )

        if st.button("💾 Unfallort speichern", type="primary"):
            unfallort = service.unfallort_erfassen(
                projekt_id=projekt_id,
                latitude=latitude,
                longitude=longitude,
                strasse=strasse,
                hausnummer=hausnummer,
                plz=plz,
                ort=ort,
                strassen_typ=StrassenTyp(strassen_typ),
                unfallort_typ=UnfallortTyp(unfallort_typ),
                kreuzende_strasse=kreuzende_strasse if kreuzende_strasse else None,
                beleuchtung=beleuchtung,
                beschreibung=beschreibung if beschreibung else None
            )

            unfallort.wetterbedingungen = wetter
            unfallort.strassenzustand = strassenzustand

            db.commit()

            st.success("Unfallort gespeichert!")


def _render_karte():
    """Karte anzeigen"""
    st.subheader("Unfallort auf Karte")

    with get_session() as db:
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        projekt_options = {
            p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
            for p in projekte
        }
        projekt_id = st.selectbox(
            "Projekt auswählen",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, ""),
            key="karte_projekt"
        )

        service = UnfallortService(db)
        unfallort = service.unfallort_fuer_projekt(projekt_id)

        if not unfallort:
            st.warning("Für dieses Projekt wurde noch kein Unfallort erfasst")
            return

        # Infos anzeigen
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Adresse:** {unfallort.vollstaendige_adresse}")
            st.write(f"**Koordinaten:** {unfallort.koordinaten_string}")

        with col2:
            st.write(f"**Straßentyp:** {unfallort.strassen_typ.value if unfallort.strassen_typ else '-'}")
            st.write(f"**Unfallorttyp:** {unfallort.unfallort_typ.value if unfallort.unfallort_typ else '-'}")

        # Karten-Links
        st.markdown("### Karte öffnen")

        col_l1, col_l2, col_l3 = st.columns(3)

        with col_l1:
            osm_url = service.generiere_karten_url(unfallort, "openstreetmap")
            if osm_url:
                st.markdown(f"[🗺️ OpenStreetMap öffnen]({osm_url})")

        with col_l2:
            google_url = service.generiere_karten_url(unfallort, "google")
            if google_url:
                st.markdown(f"[🗺️ Google Maps öffnen]({google_url})")

        with col_l3:
            bing_url = service.generiere_karten_url(unfallort, "bing")
            if bing_url:
                st.markdown(f"[🗺️ Bing Maps öffnen]({bing_url})")

        # Eingebettete Karte
        st.markdown("### Kartenvorschau")

        if unfallort.latitude and unfallort.longitude:
            # Streamlit Map
            import pandas as pd
            df = pd.DataFrame({
                'lat': [unfallort.latitude],
                'lon': [unfallort.longitude]
            })
            st.map(df, zoom=15)

            # Oder OpenStreetMap Embed
            embed_html = service.generiere_embed_html(unfallort)
            st.components.v1.html(embed_html, height=450)
        else:
            st.warning("Keine Koordinaten verfügbar")


def _render_statistik():
    """Unfallort-Statistik"""
    st.subheader("Statistik")

    with get_session() as db:
        service = UnfallortService(db)
        statistik = service.unfallort_statistik()

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Erfasste Unfallorte", statistik['gesamt'])
            st.metric("Mit Koordinaten", statistik['mit_koordinaten'])

        with col2:
            st.markdown("**Nach Straßentyp:**")
            for typ, anzahl in statistik.get('nach_strassen_typ', {}).items():
                st.write(f"- {typ}: {anzahl}")

        st.markdown("---")

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("**Nach Unfallorttyp:**")
            for typ, anzahl in statistik.get('nach_unfallort_typ', {}).items():
                st.write(f"- {typ}: {anzahl}")

        with col4:
            st.markdown("**Wetterbedingungen:**")
            for wetter, anzahl in statistik.get('nach_wetter', {}).items():
                st.write(f"- {wetter}: {anzahl}")
