"""
Digitale Signatur UI - Ermöglicht das digitale Unterschreiben von Dokumenten
"""
import streamlit as st
from datetime import datetime
import base64

from src.config.database import get_session
from src.services.signatur import get_signatur_service
from src.models import Dokument, UnfallProjekt, User
from src.models.signatur import DigitaleSignatur, SignaturAnforderung
from src.ui.components import badge


def render_signatur():
    """Rendert die Signatur-Seite"""

    st.markdown("## Digitale Unterschrift")

    user_id = st.session_state.get("user_id")
    rolle = st.session_state.get("user_role", "")

    with get_session() as db:
        signatur_service = get_signatur_service(db)

        # Tabs
        tabs = st.tabs([
            "Ausstehende Unterschriften",
            "Dokument unterschreiben",
            "Unterschriften anfordern",
            "Meine Unterschriften"
        ])

        with tabs[0]:
            _render_ausstehende(db, signatur_service, user_id)

        with tabs[1]:
            _render_unterschreiben(db, signatur_service, user_id)

        with tabs[2]:
            _render_anfordern(db, signatur_service, user_id, rolle)

        with tabs[3]:
            _render_meine_unterschriften(db, signatur_service, user_id)


def _render_ausstehende(db, signatur_service, user_id: int):
    """Rendert ausstehende Signatur-Anforderungen"""

    st.markdown("### Ausstehende Unterschriften")

    anforderungen = signatur_service.get_ausstehende_anforderungen(user_id)

    if not anforderungen:
        st.info("Keine ausstehenden Unterschriften.")
        return

    for anf in anforderungen:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{anf.dokument.original_dateiname}**")
                st.caption(f"Angefordert von: {anf.angefordert_von.vorname} {anf.angefordert_von.nachname}")
                if anf.nachricht:
                    st.caption(f"Nachricht: {anf.nachricht}")

            with col2:
                if anf.gueltig_bis:
                    tage_verbleibend = (anf.gueltig_bis - datetime.now()).days
                    if tage_verbleibend < 3:
                        st.markdown(badge(f"Läuft in {tage_verbleibend} Tagen ab", "danger"), unsafe_allow_html=True)
                    else:
                        st.caption(f"Gültig bis: {anf.gueltig_bis.strftime('%d.%m.%Y')}")

            with col3:
                if st.button("Unterschreiben", key=f"sign_{anf.id}", type="primary"):
                    st.session_state["sign_dokument_id"] = anf.dokument_id
                    st.session_state["sign_anforderung_id"] = anf.id
                    st.rerun()

                if st.button("Ablehnen", key=f"reject_{anf.id}"):
                    erfolg, nachricht = signatur_service.anforderung_ablehnen(anf.id, user_id)
                    if erfolg:
                        st.success(nachricht)
                    else:
                        st.error(nachricht)
                    st.rerun()

            st.markdown("---")


def _render_unterschreiben(db, signatur_service, user_id: int):
    """Rendert das Unterschriften-Formular"""

    st.markdown("### Dokument unterschreiben")

    # Dokument auswählen oder aus Session nehmen
    dokument_id = st.session_state.get("sign_dokument_id")

    if not dokument_id:
        # Projekt auswählen
        aktives_projekt_id = st.session_state.get("aktives_projekt_id")

        if not aktives_projekt_id:
            st.warning("Bitte wählen Sie zuerst ein Projekt aus oder nutzen Sie eine Signatur-Anforderung.")
            return

        projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == aktives_projekt_id).first()

        if not projekt or not projekt.dokumente:
            st.info("Keine Dokumente zum Unterschreiben verfügbar.")
            return

        # Nur nicht-gelöschte und noch nicht unterschriebene Dokumente
        unterschreibbare = []
        for dok in projekt.dokumente:
            if dok.geloescht:
                continue
            # Prüfen ob bereits unterschrieben
            bereits_signiert = db.query(DigitaleSignatur).filter(
                DigitaleSignatur.dokument_id == dok.id,
                DigitaleSignatur.user_id == user_id
            ).first()
            if not bereits_signiert:
                unterschreibbare.append(dok)

        if not unterschreibbare:
            st.info("Alle Dokumente wurden bereits unterschrieben.")
            return

        dok_optionen = {
            f"{d.dokument_typ_anzeige}: {d.original_dateiname}": d.id
            for d in unterschreibbare
        }

        ausgewaehltes = st.selectbox("Dokument auswählen", list(dok_optionen.keys()))
        dokument_id = dok_optionen[ausgewaehltes]

    dokument = db.query(Dokument).filter(Dokument.id == dokument_id).first()

    if not dokument:
        st.error("Dokument nicht gefunden.")
        return

    st.markdown(f"**Dokument:** {dokument.original_dateiname}")
    st.caption(f"Typ: {dokument.dokument_typ_anzeige}")

    st.markdown("---")

    # Signatur-Typ auswählen
    signatur_typ = st.radio(
        "Art der Unterschrift",
        ["Gezeichnet", "Getippt"],
        horizontal=True
    )

    st.markdown("---")

    if signatur_typ == "Getippt":
        _render_getippte_signatur(db, signatur_service, dokument, user_id)
    else:
        _render_gezeichnete_signatur(db, signatur_service, dokument, user_id)


def _render_getippte_signatur(db, signatur_service, dokument: Dokument, user_id: int):
    """Rendert die getippte Signatur"""

    user = db.query(User).filter(User.id == user_id).first()
    default_name = f"{user.vorname} {user.nachname}" if user else ""

    st.markdown("### Ihre Unterschrift")

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Ihr vollständiger Name", value=default_name)

    with col2:
        ort = st.text_input("Ort", placeholder="z.B. Berlin")

    # Vorschau der getippten Signatur
    if name:
        st.markdown("#### Vorschau")
        st.markdown(f"""
        <div style="
            font-family: 'Brush Script MT', cursive;
            font-size: 32px;
            color: #1a1a2e;
            padding: 20px;
            border-bottom: 2px solid #333;
            width: fit-content;
        ">{name}</div>
        <p style="font-size: 12px; color: #666; margin-top: 5px;">
            {ort}, {datetime.now().strftime('%d.%m.%Y')}
        </p>
        """, unsafe_allow_html=True)

    _render_rechtliche_bestaetigung(db, signatur_service, dokument, user_id, name, ort, "GETIPPT")


def _render_gezeichnete_signatur(db, signatur_service, dokument: Dokument, user_id: int):
    """Rendert die gezeichnete Signatur mit Canvas"""

    st.markdown("### Ihre Unterschrift")
    st.caption("Zeichnen Sie Ihre Unterschrift in das Feld unten (mit Maus oder Touch)")

    ort = st.text_input("Ort", placeholder="z.B. Berlin")

    # Signatur-Canvas (vereinfachte Version ohne externe Komponenten)
    st.markdown("""
    <div id="signature-pad" style="
        border: 2px solid #333;
        border-radius: 5px;
        background: #fff;
        width: 100%;
        height: 200px;
        position: relative;
    ">
        <canvas id="sig-canvas" style="width: 100%; height: 100%;"></canvas>
    </div>
    <p style="font-size: 12px; color: #666; text-align: center; margin-top: 5px;">
        Unterschreiben Sie hier
    </p>
    """, unsafe_allow_html=True)

    # Alternative: Text-basierte Signatur-Eingabe
    st.markdown("---")
    st.caption("Alternative: Geben Sie Ihren Namen ein für eine stilisierte Unterschrift")

    user = db.query(User).filter(User.id == user_id).first()
    default_name = f"{user.vorname} {user.nachname}" if user else ""

    name = st.text_input("Name für Unterschrift", value=default_name, key="drawn_name")

    if name:
        # Generiere eine stilisierte "gezeichnete" Signatur
        st.markdown("#### Vorschau")
        st.markdown(f"""
        <div style="
            font-family: 'Brush Script MT', cursive;
            font-size: 36px;
            color: #000080;
            padding: 20px;
            border-bottom: 3px solid #000;
            width: fit-content;
            transform: rotate(-2deg);
        ">{name}</div>
        <p style="font-size: 12px; color: #666; margin-top: 5px;">
            {ort}, {datetime.now().strftime('%d.%m.%Y')}
        </p>
        """, unsafe_allow_html=True)

    _render_rechtliche_bestaetigung(db, signatur_service, dokument, user_id, name, ort, "GEZEICHNET")


def _render_rechtliche_bestaetigung(
    db,
    signatur_service,
    dokument: Dokument,
    user_id: int,
    name: str,
    ort: str,
    signatur_typ: str
):
    """Rendert die rechtlichen Bestätigungen und den Unterschrift-Button"""

    st.markdown("---")
    st.markdown("### Rechtliche Bestätigung")

    bestaetigung_text = f"""
    Ich, {name or '[Name]'}, bestätige hiermit:

    1. Ich habe das Dokument "{dokument.original_dateiname}" vollständig gelesen und verstanden.
    2. Ich bin berechtigt, dieses Dokument zu unterschreiben.
    3. Meine elektronische Unterschrift hat die gleiche Rechtswirkung wie eine handschriftliche Unterschrift.
    4. Die angegebenen Informationen sind korrekt und vollständig.

    Ort: {ort or '[Ort]'}
    Datum: {datetime.now().strftime('%d.%m.%Y')}
    """

    st.text_area("Bestätigungstext", value=bestaetigung_text, height=200, disabled=True)

    col1, col2 = st.columns(2)

    with col1:
        agb = st.checkbox(
            "Ich akzeptiere die Allgemeinen Geschäftsbedingungen",
            key="accept_agb"
        )

    with col2:
        datenschutz = st.checkbox(
            "Ich akzeptiere die Datenschutzerklärung",
            key="accept_datenschutz"
        )

    st.markdown("---")

    # Unterschrift-Button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "Rechtsverbindlich unterschreiben",
            type="primary",
            use_container_width=True,
            disabled=not (name and agb and datenschutz)
        ):
            if not name:
                st.error("Bitte geben Sie Ihren Namen ein.")
                return

            if not agb or not datenschutz:
                st.error("Bitte akzeptieren Sie die rechtlichen Bestimmungen.")
                return

            # Signatur-Daten erstellen (vereinfacht: Name als Base64)
            signatur_daten = base64.b64encode(name.encode()).decode()

            erfolg, nachricht, signatur = signatur_service.signatur_erstellen(
                dokument_id=dokument.id,
                user_id=user_id,
                signatur_daten=signatur_daten,
                signatur_typ=signatur_typ,
                name_gedruckt=name,
                ort=ort,
                bestaetigung_text=bestaetigung_text,
                agb_akzeptiert=agb,
                datenschutz_akzeptiert=datenschutz
            )

            if erfolg:
                st.success("Dokument erfolgreich unterschrieben!")
                st.balloons()

                # Session aufräumen
                if "sign_dokument_id" in st.session_state:
                    del st.session_state["sign_dokument_id"]
                if "sign_anforderung_id" in st.session_state:
                    del st.session_state["sign_anforderung_id"]

                st.rerun()
            else:
                st.error(nachricht)


def _render_anfordern(db, signatur_service, user_id: int, rolle: str):
    """Rendert das Formular zum Anfordern von Unterschriften"""

    st.markdown("### Unterschrift anfordern")

    if rolle not in ["ADMIN", "ANWALT"]:
        st.warning("Nur Administratoren und Anwälte können Unterschriften anfordern.")
        return

    # Projekt auswählen
    aktives_projekt_id = st.session_state.get("aktives_projekt_id")

    if not aktives_projekt_id:
        st.warning("Bitte wählen Sie zuerst ein Projekt aus.")
        return

    projekt = db.query(UnfallProjekt).filter(UnfallProjekt.id == aktives_projekt_id).first()

    if not projekt:
        st.error("Projekt nicht gefunden.")
        return

    # Dokument auswählen
    dokumente = [d for d in projekt.dokumente if not d.geloescht]

    if not dokumente:
        st.info("Keine Dokumente verfügbar.")
        return

    dok_optionen = {
        f"{d.dokument_typ_anzeige}: {d.original_dateiname}": d.id
        for d in dokumente
    }

    ausgewaehltes_dok = st.selectbox("Dokument", list(dok_optionen.keys()))
    dokument_id = dok_optionen[ausgewaehltes_dok]

    st.markdown("---")

    # Empfänger auswählen
    st.markdown("#### Empfänger")

    empfaenger_typ = st.radio(
        "Unterschrift anfordern von",
        ["Projektbeteiligter", "Externer (per E-Mail)"],
        horizontal=True
    )

    empfaenger_user_id = None
    empfaenger_email = None

    if empfaenger_typ == "Projektbeteiligter":
        # Beteiligte des Projekts
        beteiligte = []
        if projekt.unfallopfer:
            beteiligte.append((f"Unfallopfer: {projekt.unfallopfer.vorname} {projekt.unfallopfer.nachname}", projekt.unfallopfer.id))
        if projekt.werkstatt:
            beteiligte.append((f"Werkstatt: {projekt.werkstatt.vorname} {projekt.werkstatt.nachname}", projekt.werkstatt.id))
        if projekt.gutachter:
            beteiligte.append((f"Gutachter: {projekt.gutachter.vorname} {projekt.gutachter.nachname}", projekt.gutachter.id))

        if not beteiligte:
            st.info("Keine Projektbeteiligten verfügbar.")
            return

        beteiligte_optionen = {name: uid for name, uid in beteiligte}
        ausgewaehlter = st.selectbox("Beteiligter", list(beteiligte_optionen.keys()))
        empfaenger_user_id = beteiligte_optionen[ausgewaehlter]

    else:
        empfaenger_email = st.text_input("E-Mail-Adresse", placeholder="email@beispiel.de")

    st.markdown("---")

    # Nachricht und Gültigkeit
    nachricht = st.text_area(
        "Nachricht an den Unterzeichner (optional)",
        placeholder="Bitte unterschreiben Sie das beigefügte Dokument..."
    )

    gueltig_tage = st.slider("Gültig für (Tage)", min_value=1, max_value=30, value=14)

    st.markdown("---")

    # Anforderung senden
    if st.button("Signatur-Anforderung senden", type="primary"):
        if empfaenger_typ == "Externer (per E-Mail)" and not empfaenger_email:
            st.error("Bitte geben Sie eine E-Mail-Adresse ein.")
            return

        erfolg, nachricht_result, anforderung = signatur_service.signatur_anfordern(
            dokument_id=dokument_id,
            angefordert_von_user_id=user_id,
            angefordert_fuer_user_id=empfaenger_user_id,
            angefordert_fuer_email=empfaenger_email,
            nachricht=nachricht,
            gueltig_tage=gueltig_tage
        )

        if erfolg:
            st.success("Signatur-Anforderung wurde gesendet!")
            if empfaenger_email:
                st.info(f"Eine E-Mail wurde an {empfaenger_email} gesendet.")
        else:
            st.error(nachricht_result)


def _render_meine_unterschriften(db, signatur_service, user_id: int):
    """Rendert die Liste der eigenen Unterschriften"""

    st.markdown("### Meine Unterschriften")

    signaturen = db.query(DigitaleSignatur).filter(
        DigitaleSignatur.user_id == user_id
    ).order_by(DigitaleSignatur.erstellt_am.desc()).all()

    if not signaturen:
        st.info("Sie haben noch keine Dokumente unterschrieben.")
        return

    for sig in signaturen:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{sig.dokument.original_dateiname}**")
                st.caption(f"Unterschrieben am: {sig.erstellt_am.strftime('%d.%m.%Y %H:%M')}")
                if sig.ort:
                    st.caption(f"Ort: {sig.ort}")

            with col2:
                if sig.ist_gueltig:
                    st.markdown(badge("Gültig", "success"), unsafe_allow_html=True)
                else:
                    st.markdown(badge("Ungültig", "danger"), unsafe_allow_html=True)

            with col3:
                if st.button("Verifizieren", key=f"verify_{sig.id}"):
                    gueltig, nachricht = signatur_service.signatur_verifizieren(sig.id)
                    if gueltig:
                        st.success(nachricht)
                    else:
                        st.error(nachricht)

            st.markdown("---")
