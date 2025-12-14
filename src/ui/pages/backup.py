"""
Backup/Export UI-Seite
Datensicherung und Export
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.backup import (
    BackupService, BackupTyp, BackupStatus, ExportFormat, Backup
)


def render_backup():
    """Rendert die Backup-Seite"""
    st.title("💾 Backup & Export")

    st.info("""
    Erstellen Sie vollständige Backups Ihrer Daten oder exportieren Sie
    einzelne Projekte für die Archivierung.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Backup erstellen", "Backups verwalten", "Import"
    ])

    with tab1:
        _render_backup_erstellen()

    with tab2:
        _render_backups_verwalten()

    with tab3:
        _render_import()


def _render_backup_erstellen():
    """Neues Backup erstellen"""
    st.subheader("Backup erstellen")

    with get_session() as db:
        col1, col2 = st.columns(2)

        with col1:
            backup_typ = st.selectbox(
                "Backup-Typ",
                [t.value for t in BackupTyp],
                format_func=lambda x: {
                    'VOLLSTAENDIG': '📦 Vollständiges Backup',
                    'PROJEKT': '📁 Einzelnes Projekt',
                    'DATENBANK': '🗄️ Nur Datenbank',
                    'DOKUMENTE': '📄 Nur Dokumente',
                    'KONFIGURATION': '⚙️ Konfiguration'
                }.get(x, x)
            )

            bezeichnung = st.text_input(
                "Bezeichnung",
                value=f"Backup {datetime.now().strftime('%Y-%m-%d')}"
            )

        with col2:
            format_typ = st.selectbox(
                "Format",
                [f.value for f in ExportFormat],
                format_func=lambda x: {
                    'ZIP': '📦 ZIP-Archiv',
                    'JSON': '📋 JSON',
                    'CSV': '📊 CSV',
                    'XML': '📄 XML'
                }.get(x, x)
            )

        # Projekt auswählen bei Projekt-Backup
        projekt_id = None
        if backup_typ == BackupTyp.PROJEKT.value:
            from src.models import UnfallProjekt
            projekte = db.query(UnfallProjekt).order_by(
                UnfallProjekt.erstellt_am.desc()
            ).limit(50).all()

            if projekte:
                projekt_options = {
                    p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
                    for p in projekte
                }
                projekt_id = st.selectbox(
                    "Projekt auswählen",
                    list(projekt_options.keys()),
                    format_func=lambda x: projekt_options.get(x, "")
                )

        if st.button("🔄 Backup starten", type="primary"):
            with st.spinner("Erstelle Backup..."):
                service = BackupService(db)

                backup = service.backup_erstellen(
                    bezeichnung=bezeichnung,
                    backup_typ=BackupTyp(backup_typ),
                    projekt_id=projekt_id,
                    format=ExportFormat(format_typ)
                )

                db.commit()

            if backup.status == BackupStatus.ABGESCHLOSSEN:
                st.success(f"Backup erstellt: {backup.dateiname}")

                # Statistik anzeigen
                col_s1, col_s2, col_s3 = st.columns(3)

                with col_s1:
                    st.metric("Projekte", backup.anzahl_projekte)
                with col_s2:
                    st.metric("Dokumente", backup.anzahl_dokumente)
                with col_s3:
                    st.metric("Dauer", f"{backup.dauer_sekunden:.1f}s" if backup.dauer_sekunden else "-")

                # Download anbieten
                if format_typ == ExportFormat.ZIP.value:
                    zip_data = service.backup_als_zip(backup.id)
                    if zip_data:
                        st.download_button(
                            "📥 ZIP herunterladen",
                            data=zip_data,
                            file_name=backup.dateiname or "backup.zip",
                            mime="application/zip"
                        )
                else:
                    json_data = service.backup_als_json(backup.id)
                    if json_data:
                        st.download_button(
                            "📥 JSON herunterladen",
                            data=json_data,
                            file_name=backup.dateiname or "backup.json",
                            mime="application/json"
                        )

            else:
                st.error(f"Backup fehlgeschlagen: {backup.fehler_nachricht}")


def _render_backups_verwalten():
    """Backups verwalten"""
    st.subheader("Vorhandene Backups")

    with get_session() as db:
        service = BackupService(db)

        # Speicherplatz-Statistik
        speicher = service.speicherplatz_statistik()

        col_s1, col_s2, col_s3 = st.columns(3)

        with col_s1:
            st.metric("Anzahl Backups", speicher['anzahl_backups'])
        with col_s2:
            st.metric("Speicherplatz", f"{speicher['gesamt_mb']} MB")
        with col_s3:
            if speicher['neuestes_backup']:
                st.metric(
                    "Letztes Backup",
                    speicher['neuestes_backup'].strftime('%d.%m.%Y')
                )

        st.markdown("---")

        # Backup-Liste
        backups = service.alle_backups()

        if not backups:
            st.info("Noch keine Backups vorhanden")
            return

        for backup in backups:
            status_icon = {
                BackupStatus.GESTARTET: "🔄",
                BackupStatus.LAEUFT: "⏳",
                BackupStatus.ABGESCHLOSSEN: "✅",
                BackupStatus.FEHLER: "❌"
            }.get(backup.status, "⚪")

            with st.expander(
                f"{status_icon} {backup.bezeichnung} - "
                f"{backup.gestartet_am.strftime('%d.%m.%Y %H:%M') if backup.gestartet_am else '-'}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Typ:** {backup.backup_typ.value if backup.backup_typ else '-'}")
                    st.write(f"**Format:** {backup.format.value if backup.format else '-'}")
                    st.write(f"**Status:** {backup.status.value if backup.status else '-'}")

                with col2:
                    st.write(f"**Projekte:** {backup.anzahl_projekte}")
                    st.write(f"**Dokumente:** {backup.anzahl_dokumente}")
                    st.write(f"**Dateiname:** {backup.dateiname or '-'}")

                if backup.fehler_nachricht:
                    st.error(backup.fehler_nachricht)

                # Aktionen
                col_a1, col_a2 = st.columns(2)

                with col_a1:
                    if backup.status == BackupStatus.ABGESCHLOSSEN:
                        json_data = service.backup_als_json(backup.id)
                        if json_data:
                            st.download_button(
                                "📥 Herunterladen",
                                data=json_data,
                                file_name=backup.dateiname or "backup.json",
                                mime="application/json",
                                key=f"dl_{backup.id}"
                            )

                with col_a2:
                    if st.button("🗑️ Löschen", key=f"del_{backup.id}"):
                        service.backup_loeschen(backup.id)
                        db.commit()
                        st.rerun()


def _render_import():
    """Backup importieren"""
    st.subheader("Backup importieren")

    st.warning("""
    **Achtung:** Der Import kann vorhandene Daten überschreiben.
    Erstellen Sie vorher ein Backup der aktuellen Daten!
    """)

    uploaded_file = st.file_uploader(
        "Backup-Datei auswählen",
        type=['json', 'zip']
    )

    if uploaded_file:
        st.write(f"**Datei:** {uploaded_file.name}")
        st.write(f"**Größe:** {uploaded_file.size / 1024:.1f} KB")

        # Vorschau
        if uploaded_file.name.endswith('.json'):
            try:
                import json
                inhalt = json.loads(uploaded_file.read())
                uploaded_file.seek(0)

                st.markdown("### Backup-Inhalt")

                if 'meta' in inhalt:
                    st.write(f"**Typ:** {inhalt['meta'].get('typ', '-')}")
                    st.write(f"**Erstellt:** {inhalt['meta'].get('erstellt_am', '-')}")

                if 'projekte' in inhalt:
                    st.write(f"**Projekte:** {len(inhalt['projekte'])}")

                if 'statistik' in inhalt:
                    st.write(f"**Dokumente:** {inhalt['statistik'].get('dokumente', 0)}")

            except Exception as e:
                st.error(f"Fehler beim Lesen der Datei: {e}")

        # Import starten
        if st.button("📥 Import starten", type="primary"):
            with get_session() as db:
                service = BackupService(db)

                json_data = uploaded_file.read().decode('utf-8')
                ergebnis = service.importiere_backup(json_data)

                if ergebnis['erfolgreich']:
                    st.success(f"Import abgeschlossen! {ergebnis['importierte_projekte']} Projekt(e) importiert.")
                    db.commit()
                else:
                    st.error("Import fehlgeschlagen!")
                    for fehler in ergebnis.get('fehler', []):
                        st.write(f"- {fehler}")
