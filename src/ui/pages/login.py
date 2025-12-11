"""
Login-Seite mit 2FA-Unterstützung
"""
import streamlit as st
from sqlalchemy.orm import Session

from src.services.auth import AuthService, speichere_sms_code, verifiziere_sms_code
from src.config.database import get_session


def render_login():
    """Rendert die Login-Seite"""

    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Zentrierter Login-Container
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## Anmelden")
        st.markdown("Melden Sie sich mit Ihren Zugangsdaten an.")

        # Login-Formular
        with st.form("login_form"):
            email = st.text_input("E-Mail-Adresse")
            passwort = st.text_input("Passwort", type="password")
            submitted = st.form_submit_button("Anmelden", use_container_width=True)

            if submitted:
                if not email or not passwort:
                    st.error("Bitte E-Mail und Passwort eingeben.")
                else:
                    with get_session() as db:
                        auth_service = AuthService(db)
                        user, fehler = auth_service.benutzer_authentifizieren(email, passwort)

                        if user:
                            # Prüfe ob 2FA aktiviert ist
                            if user.zwei_faktor_aktiviert:
                                st.session_state["pending_2fa_user_id"] = user.id
                                st.session_state["pending_2fa_method"] = "totp" if user.totp_secret else "sms"

                                # SMS-Code senden wenn nötig
                                if not user.totp_secret and user.telefonnummer:
                                    code = auth_service.generiere_sms_code()
                                    speichere_sms_code(user.id, code)
                                    erfolg, sms_fehler = auth_service.sende_sms_code(user.telefonnummer, code)
                                    if not erfolg:
                                        st.error(f"SMS konnte nicht gesendet werden: {sms_fehler}")
                                        return

                                st.rerun()
                            else:
                                # Direkt einloggen wenn kein 2FA
                                _complete_login(user, db, auth_service)
                                st.rerun()
                        else:
                            st.error(fehler)

        # Link zur Registrierung
        st.markdown("---")
        st.markdown("Noch kein Konto?")
        if st.button("Einladungslink verwenden", use_container_width=True):
            st.session_state["show_invitation"] = True
            st.rerun()


def render_2fa_verification():
    """Rendert die 2FA-Verifizierungsseite"""

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## Zwei-Faktor-Authentifizierung")

        user_id = st.session_state.get("pending_2fa_user_id")
        method = st.session_state.get("pending_2fa_method", "totp")

        if method == "totp":
            st.markdown("Bitte geben Sie den Code aus Ihrer Authenticator-App ein.")
        else:
            st.markdown("Ein Verifizierungscode wurde an Ihre Telefonnummer gesendet.")

        with st.form("2fa_form"):
            code = st.text_input("Verifizierungscode", max_chars=6)
            submitted = st.form_submit_button("Verifizieren", use_container_width=True)

            if submitted:
                if not code:
                    st.error("Bitte Code eingeben.")
                else:
                    with get_session() as db:
                        from src.models import User
                        auth_service = AuthService(db)
                        user = db.query(User).filter(User.id == user_id).first()

                        if not user:
                            st.error("Benutzer nicht gefunden.")
                            return

                        if method == "totp":
                            if auth_service.verifiziere_totp(user, code):
                                _complete_login(user, db, auth_service)
                                _clear_2fa_state()
                                st.rerun()
                            else:
                                st.error("Ungültiger Code.")
                        else:
                            if verifiziere_sms_code(user_id, code):
                                _complete_login(user, db, auth_service)
                                _clear_2fa_state()
                                st.rerun()
                            else:
                                st.error("Ungültiger oder abgelaufener Code.")

        # Zurück-Button
        if st.button("Zurück zum Login"):
            _clear_2fa_state()
            st.rerun()


def render_invitation():
    """Rendert die Einladungsannahme-Seite"""

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## Einladung annehmen")
        st.markdown("Geben Sie Ihren Einladungscode ein und erstellen Sie Ihr Konto.")

        with st.form("invitation_form"):
            token = st.text_input("Einladungscode")
            st.markdown("---")
            vorname = st.text_input("Vorname")
            nachname = st.text_input("Nachname")
            telefonnummer = st.text_input("Telefonnummer (für 2FA)")
            passwort = st.text_input("Passwort", type="password")
            passwort_bestaetigung = st.text_input("Passwort bestätigen", type="password")

            submitted = st.form_submit_button("Konto erstellen", use_container_width=True)

            if submitted:
                if not all([token, passwort, passwort_bestaetigung]):
                    st.error("Bitte alle Pflichtfelder ausfüllen.")
                elif passwort != passwort_bestaetigung:
                    st.error("Passwörter stimmen nicht überein.")
                else:
                    with get_session() as db:
                        auth_service = AuthService(db)
                        user, fehler = auth_service.einladung_annehmen(
                            token=token,
                            passwort=passwort,
                            vorname=vorname,
                            nachname=nachname,
                            telefonnummer=telefonnummer
                        )

                        if user:
                            st.success("Konto erfolgreich erstellt! Sie können sich jetzt anmelden.")
                            st.session_state["show_invitation"] = False
                            st.rerun()
                        else:
                            st.error(fehler)

        if st.button("Zurück zum Login"):
            st.session_state["show_invitation"] = False
            st.rerun()


def _complete_login(user, db: Session, auth_service: AuthService):
    """Schließt den Login-Prozess ab und setzt die Session"""
    auth_service.login_abschliessen(user)

    st.session_state["user_id"] = user.id
    st.session_state["user_email"] = user.email
    st.session_state["user_name"] = user.voller_name
    st.session_state["user_rolle"] = user.rolle.value
    st.session_state["user_organisation_id"] = user.organisation_id
    st.session_state["logged_in"] = True


def _clear_2fa_state():
    """Löscht den 2FA-State"""
    keys_to_remove = ["pending_2fa_user_id", "pending_2fa_method"]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]


def is_logged_in() -> bool:
    """Prüft ob ein Benutzer eingeloggt ist"""
    return st.session_state.get("logged_in", False)


def get_current_user_role() -> str:
    """Gibt die Rolle des aktuellen Benutzers zurück"""
    return st.session_state.get("user_rolle", "")


def require_login():
    """Decorator/Guard für geschützte Seiten"""
    if not is_logged_in():
        if st.session_state.get("pending_2fa_user_id"):
            render_2fa_verification()
        elif st.session_state.get("show_invitation"):
            render_invitation()
        else:
            render_login()
        return False
    return True
