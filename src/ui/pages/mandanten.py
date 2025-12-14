"""
Multi-Mandanten UI-Seite
Verwaltung mehrerer Kanzleien/Mandanten
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.mandanten import (
    MandantenService, MandantStatus, LizenzTyp,
    Mandant, MandantBenutzer
)


def render_mandanten():
    """Rendert die Mandanten-Verwaltung"""
    st.title("🏢 Multi-Mandanten-Verwaltung")

    st.info("""
    Verwalten Sie mehrere Kanzleien oder Mandanten in einer Installation.
    Jeder Mandant hat eigene Benutzer, Projekte und Einstellungen.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Mandanten", "Benutzer-Zuordnung", "Lizenzen"
    ])

    with tab1:
        _render_mandanten_liste()

    with tab2:
        _render_benutzer_zuordnung()

    with tab3:
        _render_lizenzen()


def _render_mandanten_liste():
    """Mandanten-Liste"""
    st.subheader("Mandanten")

    with get_session() as db:
        service = MandantenService(db)

        # Neuer Mandant
        with st.expander("➕ Neuen Mandanten anlegen"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Name", placeholder="Musterkanzlei GmbH")
                kurzbezeichnung = st.text_input(
                    "Kurzbezeichnung (eindeutig)",
                    placeholder="musterkanzlei"
                )
                rechtsform = st.selectbox(
                    "Rechtsform",
                    ["Einzelkanzlei", "PartG", "PartG mbB", "GmbH", "AG", "GbR", "Sonstige"]
                )

            with col2:
                strasse = st.text_input("Straße")
                plz = st.text_input("PLZ", max_chars=5)
                ort = st.text_input("Ort")
                telefon = st.text_input("Telefon")
                email = st.text_input("E-Mail")

            lizenz = st.selectbox(
                "Lizenz-Typ",
                [l.value for l in LizenzTyp],
                format_func=lambda x: {
                    'BASIC': '📦 Basic (3 Benutzer, 50 Projekte)',
                    'PROFESSIONAL': '⭐ Professional (10 Benutzer, 500 Projekte)',
                    'ENTERPRISE': '🏆 Enterprise (50 Benutzer, 5000 Projekte)',
                    'UNLIMITED': '♾️ Unlimited'
                }.get(x, x)
            )

            if st.button("💾 Mandant anlegen"):
                if name and kurzbezeichnung:
                    try:
                        mandant = service.mandant_erstellen(
                            name=name,
                            kurzbezeichnung=kurzbezeichnung,
                            lizenz_typ=LizenzTyp(lizenz),
                            rechtsform=rechtsform,
                            strasse=strasse,
                            plz=plz,
                            ort=ort,
                            telefon=telefon,
                            email=email
                        )
                        db.commit()
                        st.success(f"Mandant '{name}' angelegt!")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                else:
                    st.error("Bitte Name und Kurzbezeichnung eingeben")

        st.markdown("---")

        # Mandanten-Liste
        mandanten = service.alle_mandanten(nur_aktive=False)

        if not mandanten:
            st.info("Noch keine Mandanten angelegt")
            return

        for mandant in mandanten:
            status_icon = {
                MandantStatus.AKTIV: "🟢",
                MandantStatus.INAKTIV: "⚪",
                MandantStatus.TESTPHASE: "🟡",
                MandantStatus.GESPERRT: "🔴"
            }.get(mandant.status, "⚪")

            lizenz_icon = {
                LizenzTyp.BASIC: "📦",
                LizenzTyp.PROFESSIONAL: "⭐",
                LizenzTyp.ENTERPRISE: "🏆",
                LizenzTyp.UNLIMITED: "♾️"
            }.get(mandant.lizenz_typ, "📦")

            with st.expander(
                f"{status_icon} {mandant.name} ({mandant.kurzbezeichnung}) {lizenz_icon}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Rechtsform:** {mandant.rechtsform or '-'}")
                    st.write(f"**Adresse:** {mandant.vollstaendige_adresse or '-'}")
                    st.write(f"**Telefon:** {mandant.telefon or '-'}")
                    st.write(f"**E-Mail:** {mandant.email or '-'}")

                with col2:
                    st.write(f"**Status:** {mandant.status.value if mandant.status else '-'}")
                    st.write(f"**Lizenz:** {mandant.lizenz_typ.value if mandant.lizenz_typ else '-'}")
                    st.write(f"**Max. Benutzer:** {mandant.max_benutzer}")
                    st.write(f"**Max. Projekte:** {mandant.max_projekte}")

                # Nutzungsstatistik
                statistik = service.nutzungs_statistik(mandant.id)

                col_s1, col_s2, col_s3 = st.columns(3)

                with col_s1:
                    st.metric(
                        "Benutzer",
                        f"{statistik['benutzer']['aktuell']}/{statistik['benutzer']['limit']}"
                    )

                with col_s2:
                    st.metric(
                        "Projekte",
                        f"{statistik['projekte']['aktuell']}/{statistik['projekte']['limit']}"
                    )

                with col_s3:
                    st.metric(
                        "Speicher",
                        f"{statistik['speicher']['aktuell_mb']}/{statistik['speicher']['limit_mb']} MB"
                    )

                # Aktionen
                col_a1, col_a2 = st.columns(2)

                with col_a1:
                    if mandant.status == MandantStatus.AKTIV:
                        if st.button("⏸️ Deaktivieren", key=f"deact_{mandant.id}"):
                            service.mandant_aktualisieren(
                                mandant.id,
                                status=MandantStatus.INAKTIV
                            )
                            db.commit()
                            st.rerun()
                    else:
                        if st.button("▶️ Aktivieren", key=f"act_{mandant.id}"):
                            service.mandant_aktualisieren(
                                mandant.id,
                                status=MandantStatus.AKTIV
                            )
                            db.commit()
                            st.rerun()


def _render_benutzer_zuordnung():
    """Benutzer zu Mandanten zuordnen"""
    st.subheader("Benutzer-Zuordnung")

    with get_session() as db:
        service = MandantenService(db)
        mandanten = service.alle_mandanten()

        if not mandanten:
            st.warning("Keine Mandanten vorhanden")
            return

        mandant_options = {m.id: m.name for m in mandanten}
        selected_mandant = st.selectbox(
            "Mandant auswählen",
            list(mandant_options.keys()),
            format_func=lambda x: mandant_options.get(x, "")
        )

        if selected_mandant:
            # Aktuelle Benutzer
            benutzer = service.benutzer_fuer_mandant(selected_mandant)

            st.markdown("### Zugeordnete Benutzer")

            if benutzer:
                for b in benutzer:
                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        st.write(f"**Benutzer-ID:** {b.user_id}")

                    with col2:
                        st.write("👑 Admin" if b.ist_admin else "👤 Benutzer")

                    with col3:
                        if st.button("🗑️ Entfernen", key=f"rem_{b.id}"):
                            service.benutzer_entfernen(selected_mandant, b.user_id)
                            db.commit()
                            st.rerun()
            else:
                st.info("Keine Benutzer zugeordnet")

            # Benutzer hinzufügen
            st.markdown("### Benutzer hinzufügen")

            col_h1, col_h2, col_h3 = st.columns([2, 1, 1])

            with col_h1:
                user_id = st.number_input("Benutzer-ID", min_value=1, step=1)

            with col_h2:
                ist_admin = st.checkbox("Als Admin")

            with col_h3:
                if st.button("➕ Hinzufügen"):
                    try:
                        service.benutzer_hinzufuegen(
                            mandant_id=selected_mandant,
                            user_id=user_id,
                            ist_admin=ist_admin
                        )
                        db.commit()
                        st.success("Benutzer hinzugefügt!")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))


def _render_lizenzen():
    """Lizenz-Verwaltung"""
    st.subheader("Lizenzen")

    with get_session() as db:
        service = MandantenService(db)
        mandanten = service.alle_mandanten(nur_aktive=False)

        if not mandanten:
            st.info("Keine Mandanten vorhanden")
            return

        st.markdown("### Lizenz-Übersicht")

        for mandant in mandanten:
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**{mandant.name}**")

            with col2:
                st.write(mandant.lizenz_typ.value if mandant.lizenz_typ else "-")

            with col3:
                gueltig_bis = mandant.lizenz_gueltig_bis
                if gueltig_bis:
                    tage_bis = (gueltig_bis.date() - datetime.now().date()).days
                    if tage_bis < 0:
                        st.write("⚠️ Abgelaufen")
                    elif tage_bis < 30:
                        st.write(f"⚠️ {tage_bis} Tage")
                    else:
                        st.write(f"✅ {tage_bis} Tage")
                else:
                    st.write("♾️ Unbegrenzt")

        st.markdown("---")

        # Lizenz-Upgrade
        st.markdown("### Lizenz-Upgrade")

        col1, col2 = st.columns(2)

        with col1:
            mandant_options = {m.id: m.name for m in mandanten}
            upgrade_mandant = st.selectbox(
                "Mandant",
                list(mandant_options.keys()),
                format_func=lambda x: mandant_options.get(x, ""),
                key="upgrade_mandant"
            )

        with col2:
            neuer_typ = st.selectbox(
                "Neue Lizenz",
                [l.value for l in LizenzTyp],
                format_func=lambda x: {
                    'BASIC': '📦 Basic',
                    'PROFESSIONAL': '⭐ Professional',
                    'ENTERPRISE': '🏆 Enterprise',
                    'UNLIMITED': '♾️ Unlimited'
                }.get(x, x)
            )

        gueltig_bis = st.date_input("Gültig bis (optional)")

        if st.button("⬆️ Upgrade durchführen"):
            service.lizenz_upgrade(
                mandant_id=upgrade_mandant,
                neuer_typ=LizenzTyp(neuer_typ),
                gueltig_bis=datetime.combine(gueltig_bis, datetime.min.time()) if gueltig_bis else None
            )
            db.commit()
            st.success("Lizenz aktualisiert!")
            st.rerun()

        # Lizenz-Features
        st.markdown("### Lizenz-Features")

        st.markdown("""
        | Feature | Basic | Professional | Enterprise | Unlimited |
        |---------|-------|--------------|------------|-----------|
        | Benutzer | 3 | 10 | 50 | ♾️ |
        | Projekte | 50 | 500 | 5.000 | ♾️ |
        | Speicher | 500 MB | 5 GB | 50 GB | ♾️ |
        | Timeline | ❌ | ✅ | ✅ | ✅ |
        | Fristen | ❌ | ✅ | ✅ | ✅ |
        | Berichte | ❌ | ✅ | ✅ | ✅ |
        | API | ❌ | ❌ | ✅ | ✅ |
        | Support | E-Mail | E-Mail | Telefon | 24/7 |
        """)
