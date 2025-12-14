"""
DATEV-Export UI-Seite
Export für Buchhaltung im DATEV-Format
"""
import streamlit as st
from datetime import date, timedelta

from src.config.database import get_session
from src.services.datev import DATEVService, DATEVExport


def render_datev():
    """Rendert die DATEV-Export-Seite"""
    st.title("📤 DATEV-Export")

    st.info("""
    Exportieren Sie Ihre Buchungsdaten im DATEV-Format für die Übergabe
    an Ihren Steuerberater oder Ihre Buchhaltungssoftware.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Neuer Export", "Projekt-Export", "Export-Verlauf"
    ])

    with tab1:
        _render_neuer_export()

    with tab2:
        _render_projekt_export()

    with tab3:
        _render_export_verlauf()


def _render_neuer_export():
    """Neuen DATEV-Export erstellen"""
    st.subheader("Rechnungen exportieren")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Zeitraum")

        zeitraum_option = st.selectbox(
            "Zeitraum wählen",
            ["Letzter Monat", "Letztes Quartal", "Letztes Jahr", "Benutzerdefiniert"]
        )

        heute = date.today()

        if zeitraum_option == "Letzter Monat":
            erster_des_monats = heute.replace(day=1)
            letzter_des_vormonats = erster_des_monats - timedelta(days=1)
            zeitraum_von = letzter_des_vormonats.replace(day=1)
            zeitraum_bis = letzter_des_vormonats
        elif zeitraum_option == "Letztes Quartal":
            quartal = (heute.month - 1) // 3
            if quartal == 0:
                zeitraum_von = date(heute.year - 1, 10, 1)
                zeitraum_bis = date(heute.year - 1, 12, 31)
            else:
                start_monat = (quartal - 1) * 3 + 1
                zeitraum_von = date(heute.year, start_monat, 1)
                end_monat = start_monat + 2
                if end_monat == 12:
                    zeitraum_bis = date(heute.year, 12, 31)
                else:
                    zeitraum_bis = date(heute.year, end_monat + 1, 1) - timedelta(days=1)
        elif zeitraum_option == "Letztes Jahr":
            zeitraum_von = date(heute.year - 1, 1, 1)
            zeitraum_bis = date(heute.year - 1, 12, 31)
        else:
            zeitraum_von = st.date_input("Von", value=heute.replace(day=1))
            zeitraum_bis = st.date_input("Bis", value=heute)

        if zeitraum_option != "Benutzerdefiniert":
            st.write(f"**Von:** {zeitraum_von.strftime('%d.%m.%Y')}")
            st.write(f"**Bis:** {zeitraum_bis.strftime('%d.%m.%Y')}")

    with col2:
        st.markdown("### DATEV-Einstellungen")

        beraternummer = st.text_input("Beraternummer", value="12345", max_chars=10)
        mandantennummer = st.text_input("Mandantennummer", value="10001", max_chars=10)

        st.markdown("### Kontenrahmen")
        st.selectbox("Kontenrahmen", ["SKR03 (Standard)", "SKR04"], disabled=True)

        st.caption("Aktuell wird nur SKR03 unterstützt")

    st.markdown("---")

    if st.button("Export erstellen", type="primary"):
        with get_session() as db:
            service = DATEVService(db)
            user_id = st.session_state.get("user_id")

            try:
                export = service.exportiere_rechnungen(
                    zeitraum_von=zeitraum_von,
                    zeitraum_bis=zeitraum_bis,
                    beraternummer=beraternummer,
                    mandantennummer=mandantennummer,
                    erstellt_von_user_id=user_id
                )

                st.success(f"Export erstellt: {export.dateiname}")

                col_s1, col_s2, col_s3 = st.columns(3)

                with col_s1:
                    st.metric("Buchungen", export.anzahl_buchungen)
                with col_s2:
                    st.metric("Summe Soll", f"{float(export.summe_soll):,.2f} €")
                with col_s3:
                    st.metric("Summe Haben", f"{float(export.summe_haben):,.2f} €")

                # Download-Button
                st.download_button(
                    "📥 CSV herunterladen",
                    data=export.dateiinhalt,
                    file_name=export.dateiname,
                    mime="text/csv"
                )

            except Exception as e:
                st.error(f"Fehler beim Export: {e}")


def _render_projekt_export():
    """Kosten eines Projekts exportieren"""
    st.subheader("Projekt-Kosten exportieren")

    with get_session() as db:
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).limit(50).all()

        if not projekte:
            st.info("Keine Projekte vorhanden")
            return

        projekt_options = {p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}" for p in projekte}
        projekt_id = st.selectbox(
            "Projekt auswählen",
            list(projekt_options.keys()),
            format_func=lambda x: projekt_options.get(x, "")
        )

        col1, col2 = st.columns(2)

        with col1:
            beraternummer = st.text_input("Beraternummer", value="12345", key="proj_berater")
        with col2:
            mandantennummer = st.text_input("Mandantennummer", value="10001", key="proj_mandant")

        if st.button("Projekt-Export erstellen", type="primary"):
            service = DATEVService(db)
            user_id = st.session_state.get("user_id")

            try:
                export = service.exportiere_kosten(
                    projekt_id=projekt_id,
                    beraternummer=beraternummer,
                    mandantennummer=mandantennummer,
                    erstellt_von_user_id=user_id
                )

                st.success(f"Export erstellt: {export.dateiname}")
                st.metric("Buchungen", export.anzahl_buchungen)

                st.download_button(
                    "📥 CSV herunterladen",
                    data=export.dateiinhalt,
                    file_name=export.dateiname,
                    mime="text/csv",
                    key="dl_projekt"
                )

            except Exception as e:
                st.error(f"Fehler beim Export: {e}")


def _render_export_verlauf():
    """Zeigt frühere Exporte"""
    st.subheader("Export-Verlauf")

    with get_session() as db:
        service = DATEVService(db)
        exporte = service.alle_exporte(limit=50)

        if not exporte:
            st.info("Noch keine Exporte durchgeführt")
            return

        for export in exporte:
            with st.expander(
                f"{export.erstellt_am.strftime('%d.%m.%Y %H:%M')} - {export.dateiname}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Typ:** {export.export_typ}")
                    st.write(f"**Zeitraum:** {export.zeitraum_von.strftime('%d.%m.%Y') if export.zeitraum_von else '-'} bis {export.zeitraum_bis.strftime('%d.%m.%Y') if export.zeitraum_bis else '-'}")

                with col2:
                    st.write(f"**Buchungen:** {export.anzahl_buchungen}")
                    st.write(f"**Summe Soll:** {export.summe_soll} EUR")
                    st.write(f"**Summe Haben:** {export.summe_haben} EUR")

                # Download
                if export.dateiinhalt:
                    st.download_button(
                        "📥 Erneut herunterladen",
                        data=export.dateiinhalt,
                        file_name=export.dateiname,
                        mime="text/csv",
                        key=f"dl_{export.id}"
                    )

                # Vorschau
                if st.checkbox("Vorschau anzeigen", key=f"prev_{export.id}"):
                    st.text_area(
                        "CSV-Inhalt",
                        value=export.dateiinhalt[:2000] + "..." if len(export.dateiinhalt) > 2000 else export.dateiinhalt,
                        height=200,
                        disabled=True
                    )
