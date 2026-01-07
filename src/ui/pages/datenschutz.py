"""
Datenschutz-Zustimmung UI-Seite
Anzeige der Datenschutzerklärung, AGB, Widerrufsbelehrung mit Bestätigungsmöglichkeit
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.models.datenschutz import (
    DatenschutzZustimmung,
    AKTUELLE_VERSIONEN,
    DATENSCHUTZERKLAERUNG,
    AGB_TEXT,
    WIDERRUFSBELEHRUNG,
    VERTRAULICHKEITSHINWEIS
)


def render_datenschutz():
    """Rendert die Datenschutz-Seite"""
    st.title("Datenschutz & Einwilligungen")

    user_id = st.session_state.get("user_id")

    if not user_id:
        st.warning("Bitte melden Sie sich an, um die Datenschutzeinstellungen zu sehen.")
        return

    with get_session() as db:
        # Bestehende Zustimmung laden
        zustimmung = db.query(DatenschutzZustimmung).filter(
            DatenschutzZustimmung.user_id == user_id,
            DatenschutzZustimmung.widerrufen == False
        ).first()

        # Status anzeigen
        if zustimmung and zustimmung.alle_pflicht_akzeptiert:
            st.success(f"Status: {zustimmung.status_text}")
            st.caption(f"Zustimmung erteilt am: {zustimmung.erstellt_am.strftime('%d.%m.%Y %H:%M')}")

            with st.expander("Zustimmungen verwalten"):
                _render_zustimmung_details(zustimmung)

                st.markdown("---")

                if st.button("Einwilligungen widerrufen", type="secondary"):
                    st.session_state["show_widerruf_dialog"] = True

                if st.session_state.get("show_widerruf_dialog"):
                    _render_widerruf_dialog(db, zustimmung)
        else:
            st.warning("Bitte bestätigen Sie die erforderlichen Einwilligungen, um den Service nutzen zu können.")
            _render_zustimmung_formular(db, user_id, zustimmung)


def _render_zustimmung_formular(db, user_id: int, bestehende_zustimmung=None):
    """Formular für neue Zustimmung"""

    st.markdown("---")
    st.subheader("Erforderliche Einwilligungen")

    st.info("""
    Bitte lesen Sie die folgenden Dokumente sorgfältig durch und bestätigen Sie Ihre Zustimmung.
    Klicken Sie auf die Pfeile (▶), um die vollständigen Texte anzuzeigen.
    """)

    # Datenschutzerklärung
    st.markdown("### 1. Datenschutzerklärung (Pflicht)")
    with st.expander("📄 Datenschutzerklärung lesen", expanded=False):
        st.markdown(DATENSCHUTZERKLAERUNG)

    datenschutz_check = st.checkbox(
        "Ich habe die Datenschutzerklärung gelesen und akzeptiere diese.",
        value=bestehende_zustimmung.datenschutz_akzeptiert if bestehende_zustimmung else False,
        key="datenschutz_check"
    )

    st.markdown("---")

    # AGB
    st.markdown("### 2. Allgemeine Geschäftsbedingungen (Pflicht)")
    with st.expander("📄 AGB lesen", expanded=False):
        st.markdown(AGB_TEXT)

    agb_check = st.checkbox(
        "Ich habe die AGB gelesen und akzeptiere diese.",
        value=bestehende_zustimmung.agb_akzeptiert if bestehende_zustimmung else False,
        key="agb_check"
    )

    st.markdown("---")

    # Widerrufsbelehrung
    st.markdown("### 3. Widerrufsbelehrung (Pflicht)")
    with st.expander("📄 Widerrufsbelehrung lesen", expanded=False):
        st.markdown(WIDERRUFSBELEHRUNG)

    widerruf_check = st.checkbox(
        "Ich habe die Widerrufsbelehrung zur Kenntnis genommen.",
        value=bestehende_zustimmung.widerrufsbelehrung_akzeptiert if bestehende_zustimmung else False,
        key="widerruf_check"
    )

    st.markdown("---")

    # Vertraulichkeitsvereinbarung
    st.markdown("### 4. Vertraulichkeitsvereinbarung (Pflicht)")
    with st.expander("📄 Vertraulichkeitsvereinbarung lesen", expanded=False):
        st.markdown(VERTRAULICHKEITSHINWEIS)

    vertraulichkeit_check = st.checkbox(
        "Ich akzeptiere die Vertraulichkeitsvereinbarung.",
        value=bestehende_zustimmung.vertraulichkeit_akzeptiert if bestehende_zustimmung else False,
        key="vertraulichkeit_check"
    )

    st.markdown("---")

    # Optionale Einwilligungen
    st.subheader("Optionale Einwilligungen")

    st.markdown("### 5. Kontaktaufnahme (Optional)")
    kontakt_check = st.checkbox(
        "Ich bin damit einverstanden, dass mich Schadenmanager.vom GmbH per E-Mail oder Telefon kontaktiert.",
        value=bestehende_zustimmung.kontakt_einwilligung if bestehende_zustimmung else False,
        key="kontakt_check"
    )

    st.markdown("---")

    st.markdown("### 6. Verzicht auf Widerrufsrecht (Optional)")
    st.caption("""
    Falls Sie möchten, dass wir sofort mit der Bearbeitung Ihres Schadensfalls beginnen,
    können Sie auf Ihr Widerrufsrecht verzichten. Dies bedeutet, dass Sie den Vertrag
    nicht mehr innerhalb von 14 Tagen widerrufen können, sobald wir mit der Arbeit begonnen haben.
    """)
    verzicht_check = st.checkbox(
        "Ich stimme dem vorzeitigen Beginn der Dienstleistung zu und verzichte auf mein Widerrufsrecht nach Leistungsbeginn.",
        value=bestehende_zustimmung.widerrufsrecht_verzicht if bestehende_zustimmung else False,
        key="verzicht_check"
    )

    st.markdown("---")

    # Prüfen ob Pflichtfelder ausgefüllt
    pflicht_ok = all([datenschutz_check, agb_check, widerruf_check, vertraulichkeit_check])

    if not pflicht_ok:
        st.warning("Bitte akzeptieren Sie alle Pflichtfelder (1-4), um fortzufahren.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Zustimmung erteilen", disabled=not pflicht_ok, type="primary"):
            # IP-Adresse und User-Agent (in Produktion aus Request)
            ip_adresse = st.session_state.get("client_ip", "127.0.0.1")
            user_agent = st.session_state.get("user_agent", "Streamlit")

            jetzt = datetime.utcnow()

            if bestehende_zustimmung:
                # Bestehende aktualisieren
                zustimmung = bestehende_zustimmung
            else:
                # Neue erstellen
                zustimmung = DatenschutzZustimmung(user_id=user_id)
                db.add(zustimmung)

            # Werte setzen
            zustimmung.datenschutz_akzeptiert = datenschutz_check
            zustimmung.datenschutz_akzeptiert_am = jetzt if datenschutz_check else None
            zustimmung.datenschutz_version = AKTUELLE_VERSIONEN["datenschutz"]

            zustimmung.agb_akzeptiert = agb_check
            zustimmung.agb_akzeptiert_am = jetzt if agb_check else None
            zustimmung.agb_version = AKTUELLE_VERSIONEN["agb"]

            zustimmung.widerrufsbelehrung_akzeptiert = widerruf_check
            zustimmung.widerrufsbelehrung_akzeptiert_am = jetzt if widerruf_check else None

            zustimmung.vertraulichkeit_akzeptiert = vertraulichkeit_check
            zustimmung.vertraulichkeit_akzeptiert_am = jetzt if vertraulichkeit_check else None

            zustimmung.kontakt_einwilligung = kontakt_check
            zustimmung.kontakt_einwilligung_am = jetzt if kontakt_check else None

            zustimmung.widerrufsrecht_verzicht = verzicht_check
            zustimmung.widerrufsrecht_verzicht_am = jetzt if verzicht_check else None

            zustimmung.ip_adresse = ip_adresse
            zustimmung.user_agent = user_agent

            db.commit()

            st.success("Ihre Zustimmung wurde gespeichert!")
            st.rerun()

    with col2:
        if st.button("❌ Abbrechen"):
            st.rerun()


def _render_zustimmung_details(zustimmung: DatenschutzZustimmung):
    """Zeigt Details der aktuellen Zustimmung"""
    st.markdown("**Ihre aktuellen Einwilligungen:**")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Pflichteinwilligungen:**")
        st.write(f"✅ Datenschutzerklärung: {zustimmung.datenschutz_akzeptiert_am.strftime('%d.%m.%Y') if zustimmung.datenschutz_akzeptiert_am else '-'}")
        st.write(f"✅ AGB: {zustimmung.agb_akzeptiert_am.strftime('%d.%m.%Y') if zustimmung.agb_akzeptiert_am else '-'}")
        st.write(f"✅ Widerrufsbelehrung: {zustimmung.widerrufsbelehrung_akzeptiert_am.strftime('%d.%m.%Y') if zustimmung.widerrufsbelehrung_akzeptiert_am else '-'}")
        st.write(f"✅ Vertraulichkeit: {zustimmung.vertraulichkeit_akzeptiert_am.strftime('%d.%m.%Y') if zustimmung.vertraulichkeit_akzeptiert_am else '-'}")

    with col2:
        st.write("**Optionale Einwilligungen:**")
        kontakt_status = "✅" if zustimmung.kontakt_einwilligung else "❌"
        verzicht_status = "✅" if zustimmung.widerrufsrecht_verzicht else "❌"
        st.write(f"{kontakt_status} Kontaktaufnahme")
        st.write(f"{verzicht_status} Verzicht Widerrufsrecht")

    st.caption(f"Version Datenschutz: {zustimmung.datenschutz_version or '-'} | AGB: {zustimmung.agb_version or '-'}")
    st.caption(f"IP-Adresse: {zustimmung.ip_adresse or '-'}")


def _render_widerruf_dialog(db, zustimmung: DatenschutzZustimmung):
    """Dialog zum Widerruf der Einwilligungen"""
    st.markdown("---")
    st.warning("**Achtung:** Wenn Sie Ihre Einwilligungen widerrufen, können Sie den Service nicht mehr nutzen.")

    grund = st.text_area(
        "Grund für den Widerruf (optional)",
        placeholder="Bitte geben Sie optional einen Grund an...",
        key="widerruf_grund"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Widerruf bestätigen", type="primary"):
            zustimmung.widerrufen = True
            zustimmung.widerrufen_am = datetime.utcnow()
            zustimmung.widerruf_grund = grund

            db.commit()

            st.session_state["show_widerruf_dialog"] = False
            st.success("Ihre Einwilligungen wurden widerrufen.")
            st.rerun()

    with col2:
        if st.button("Abbrechen"):
            st.session_state["show_widerruf_dialog"] = False
            st.rerun()


def check_datenschutz_akzeptiert(user_id: int) -> bool:
    """
    Prüft ob ein Benutzer alle Pflicht-Datenschutzeinwilligungen erteilt hat.
    Kann in anderen Teilen der App verwendet werden.
    """
    if not user_id:
        return False

    with get_session() as db:
        zustimmung = db.query(DatenschutzZustimmung).filter(
            DatenschutzZustimmung.user_id == user_id,
            DatenschutzZustimmung.widerrufen == False
        ).first()

        if not zustimmung:
            return False

        return zustimmung.alle_pflicht_akzeptiert


def render_datenschutz_check_banner():
    """
    Zeigt ein Banner an, wenn der Benutzer die Datenschutzeinwilligungen noch nicht erteilt hat.
    Kann auf jeder Seite eingebunden werden.
    """
    user_id = st.session_state.get("user_id")

    if not user_id:
        return

    if not check_datenschutz_akzeptiert(user_id):
        st.warning("""
        ⚠️ **Datenschutzeinwilligung erforderlich**

        Bitte bestätigen Sie die Datenschutzerklärung und AGB, um alle Funktionen nutzen zu können.
        """)
        if st.button("Jetzt bestätigen →"):
            st.session_state["current_page"] = "datenschutz"
            st.rerun()
