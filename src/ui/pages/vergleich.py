"""
Vergleichsrechner UI-Seite
Bewertung von Vergleichsangeboten
"""
import streamlit as st
from datetime import datetime, date
from decimal import Decimal

from src.config.database import get_session
from src.services.vergleich import VergleichsService, VergleichsStatus, Vergleichsangebot


def render_vergleich():
    """Rendert die Vergleichsrechner-Seite"""
    st.title("🤝 Vergleichsrechner")

    st.info("""
    Bewerten Sie Vergleichsangebote und berechnen Sie, ob ein Vergleich
    wirtschaftlich sinnvoll ist.
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Neues Angebot", "Angebote-Übersicht", "Vergleich berechnen"
    ])

    with tab1:
        _render_neues_angebot()

    with tab2:
        _render_angebote_uebersicht()

    with tab3:
        _render_vergleich_berechnen()


def _render_neues_angebot():
    """Neues Vergleichsangebot erfassen"""
    st.subheader("Vergleichsangebot erfassen")

    with get_session() as db:
        from src.models import UnfallProjekt

        projekte = db.query(UnfallProjekt).order_by(
            UnfallProjekt.erstellt_am.desc()
        ).limit(50).all()

        if not projekte:
            st.warning("Keine Projekte vorhanden")
            return

        col1, col2 = st.columns(2)

        with col1:
            projekt_options = {
                p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}"
                for p in projekte
            }
            projekt_id = st.selectbox(
                "Projekt",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, "")
            )

            anbieter = st.text_input("Anbieter", placeholder="z.B. Allianz Versicherung")

            angebotsdatum = st.date_input("Angebotsdatum", value=date.today())

        with col2:
            angebotssumme = st.number_input(
                "Angebotssumme (EUR)",
                min_value=0.0,
                step=100.0
            )

            urspruengliche_forderung = st.number_input(
                "Ursprüngliche Forderung (EUR)",
                min_value=0.0,
                step=100.0
            )

            gueltig_bis = st.date_input(
                "Gültig bis",
                value=date.today()
            )

        st.markdown("### Bedingungen")

        bedingungen = st.text_area(
            "Bedingungen des Angebots",
            placeholder="z.B. Abgeltung aller Ansprüche, Verzicht auf Rechtsmittel..."
        )

        notizen = st.text_area("Interne Notizen (optional)")

        if st.button("💾 Angebot speichern", type="primary"):
            if not anbieter or angebotssumme <= 0:
                st.error("Bitte alle Pflichtfelder ausfüllen")
                return

            service = VergleichsService(db)
            angebot = service.angebot_erstellen(
                projekt_id=projekt_id,
                anbieter=anbieter,
                angebotssumme=Decimal(str(angebotssumme)),
                urspruengliche_forderung=Decimal(str(urspruengliche_forderung)),
                angebotsdatum=angebotsdatum,
                gueltig_bis=gueltig_bis,
                bedingungen=bedingungen if bedingungen else None,
                notizen=notizen if notizen else None
            )

            db.commit()

            st.success("Angebot gespeichert!")

            # Empfehlung anzeigen
            empfehlung = service.empfehlung_generieren(angebot.id)
            _zeige_empfehlung(empfehlung)


def _zeige_empfehlung(empfehlung: dict):
    """Zeigt Empfehlung an"""
    st.markdown("---")
    st.markdown("### 📊 Analyse")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Vergleichsquote", f"{empfehlung.get('vergleichsquote', 0):.1f}%")
    with col2:
        st.metric("Differenz", f"{empfehlung.get('differenz_betrag', 0):,.2f} EUR")
    with col3:
        tendenz = empfehlung.get('tendenz', 'neutral')
        icon = "✅" if tendenz == "annehmen" else "❌" if tendenz == "ablehnen" else "⚖️"
        st.metric("Tendenz", f"{icon} {tendenz.title()}")

    st.markdown("### 💡 Empfehlung")
    st.info(empfehlung.get('empfehlung_text', 'Keine Empfehlung'))


def _render_angebote_uebersicht():
    """Übersicht aller Vergleichsangebote"""
    st.subheader("Vergleichsangebote")

    with get_session() as db:
        angebote = db.query(Vergleichsangebot).order_by(
            Vergleichsangebot.erstellt_am.desc()
        ).limit(50).all()

        if not angebote:
            st.info("Noch keine Vergleichsangebote erfasst")
            return

        for angebot in angebote:
            status_icon = {
                VergleichsStatus.OFFEN: "🔵",
                VergleichsStatus.ANGENOMMEN: "✅",
                VergleichsStatus.ABGELEHNT: "❌",
                VergleichsStatus.ABGELAUFEN: "⏰",
                VergleichsStatus.VERHANDLUNG: "🤝"
            }.get(angebot.status, "⚪")

            with st.expander(
                f"{status_icon} {angebot.anbieter} - {angebot.angebotssumme:,.2f} EUR "
                f"({angebot.angebotsdatum.strftime('%d.%m.%Y') if angebot.angebotsdatum else '-'})"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Projekt:** {angebot.projekt_id}")
                    st.write(f"**Angebotssumme:** {float(angebot.angebotssumme):,.2f} EUR")
                    st.write(f"**Ursprüngliche Forderung:** {float(angebot.urspruengliche_forderung or 0):,.2f} EUR")

                with col2:
                    if angebot.urspruengliche_forderung and angebot.urspruengliche_forderung > 0:
                        quote = float(angebot.angebotssumme) / float(angebot.urspruengliche_forderung) * 100
                        st.write(f"**Quote:** {quote:.1f}%")
                    st.write(f"**Gültig bis:** {angebot.gueltig_bis.strftime('%d.%m.%Y') if angebot.gueltig_bis else '-'}")
                    st.write(f"**Status:** {angebot.status.value}")

                if angebot.bedingungen:
                    st.write(f"**Bedingungen:** {angebot.bedingungen}")

                # Aktionen
                if angebot.status == VergleichsStatus.OFFEN:
                    col_a1, col_a2 = st.columns(2)

                    with col_a1:
                        if st.button("✅ Annehmen", key=f"ann_{angebot.id}"):
                            service = VergleichsService(db)
                            service.status_aendern(angebot.id, VergleichsStatus.ANGENOMMEN)
                            db.commit()
                            st.rerun()

                    with col_a2:
                        if st.button("❌ Ablehnen", key=f"abl_{angebot.id}"):
                            service = VergleichsService(db)
                            service.status_aendern(angebot.id, VergleichsStatus.ABGELEHNT)
                            db.commit()
                            st.rerun()


def _render_vergleich_berechnen():
    """Schneller Vergleichsrechner"""
    st.subheader("Schnellrechner")

    col1, col2 = st.columns(2)

    with col1:
        urspruengliche_forderung = st.number_input(
            "Ursprüngliche Forderung (EUR)",
            min_value=0.0,
            value=10000.0,
            step=100.0,
            key="calc_forderung"
        )

        angebot = st.number_input(
            "Vergleichsangebot (EUR)",
            min_value=0.0,
            value=7500.0,
            step=100.0,
            key="calc_angebot"
        )

    with col2:
        prozesskosten_eigen = st.number_input(
            "Eigene Prozesskosten (geschätzt)",
            min_value=0.0,
            value=2000.0,
            step=100.0
        )

        erfolgswahrscheinlichkeit = st.slider(
            "Erfolgswahrscheinlichkeit (%)",
            min_value=0,
            max_value=100,
            value=70
        )

    if st.button("📊 Berechnen", type="primary"):
        if urspruengliche_forderung > 0:
            quote = (angebot / urspruengliche_forderung) * 100

            # Erwartungswert bei Prozess
            erwartungswert_prozess = (
                urspruengliche_forderung * (erfolgswahrscheinlichkeit / 100) -
                prozesskosten_eigen
            )

            # Vergleich
            differenz = angebot - erwartungswert_prozess

            st.markdown("---")
            st.markdown("### 📊 Ergebnis")

            col_r1, col_r2, col_r3 = st.columns(3)

            with col_r1:
                st.metric("Vergleichsquote", f"{quote:.1f}%")
            with col_r2:
                st.metric("Erwartungswert Prozess", f"{erwartungswert_prozess:,.2f} EUR")
            with col_r3:
                st.metric(
                    "Differenz",
                    f"{differenz:,.2f} EUR",
                    delta=f"{'+' if differenz > 0 else ''}{differenz:,.2f} EUR"
                )

            st.markdown("### 💡 Empfehlung")

            if differenz > 0:
                st.success(f"""
                **Vergleich empfohlen**

                Das Vergleichsangebot ({angebot:,.2f} EUR) liegt über dem
                Erwartungswert bei Prozessführung ({erwartungswert_prozess:,.2f} EUR).

                Bei einer Erfolgswahrscheinlichkeit von {erfolgswahrscheinlichkeit}%
                und geschätzten Prozesskosten von {prozesskosten_eigen:,.2f} EUR
                ist der Vergleich wirtschaftlich vorteilhafter.
                """)
            else:
                st.warning(f"""
                **Prozess könnte vorteilhafter sein**

                Der Erwartungswert bei Prozessführung ({erwartungswert_prozess:,.2f} EUR)
                liegt über dem Vergleichsangebot ({angebot:,.2f} EUR).

                Allerdings sollten auch nicht-monetäre Faktoren berücksichtigt werden
                (Zeit, Stress, Unsicherheit).
                """)
