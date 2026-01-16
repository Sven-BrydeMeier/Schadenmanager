"""
Mandanten-Portal - Vereinfachte Ansicht für Unfallopfer
"""
import streamlit as st
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, Dokument, TimelineMeilenstein,
    KostenPosition, MeilensteinStatus
)
from src.ui.components import badge
from src.config.database import get_session


def render_mandanten_portal():
    """Rendert das Mandanten-Portal für Unfallopfer"""

    st.markdown("## Mein Schadensfall")

    user_id = st.session_state.get("user_id")

    with get_session() as db:
        # Projekte des Mandanten laden
        projekte = db.query(UnfallProjekt).filter(
            UnfallProjekt.unfallopfer_user_id == user_id
        ).order_by(UnfallProjekt.erstellt_am.desc()).all()

        if not projekte:
            st.info("Sie haben derzeit keine aktiven Schadensfälle.")
            st.markdown("""
            ### Was können Sie hier tun?

            Im Mandanten-Portal haben Sie jederzeit Einblick in den aktuellen Stand
            Ihres Schadensfalles. Sie können:

            - Den Fortschritt Ihres Falles verfolgen
            - Hochgeladene Dokumente einsehen
            - Die Kostenübersicht betrachten
            - Nachrichten mit Ihrem Anwalt austauschen

            Sobald ein Schadensfall für Sie angelegt wurde, erscheint er hier.
            """)
            return

        # Wenn mehrere Projekte, Auswahl anbieten
        if len(projekte) > 1:
            projekt_optionen = {
                f"{p.aktenzeichen or p.projektnummer} - {p.datum_unfall.strftime('%d.%m.%Y') if p.datum_unfall else 'Unbekannt'}": p.id
                for p in projekte
            }

            ausgewaehltes = st.selectbox(
                "Schadensfall auswählen",
                list(projekt_optionen.keys())
            )
            projekt_id = projekt_optionen[ausgewaehltes]
            projekt = next(p for p in projekte if p.id == projekt_id)
        else:
            projekt = projekte[0]

        # Tabs für verschiedene Bereiche
        tabs = st.tabs([
            "Übersicht",
            "Fortschritt",
            "Dokumente",
            "Kosten",
            "Kontakt"
        ])

        with tabs[0]:
            _render_uebersicht(projekt)

        with tabs[1]:
            _render_fortschritt(db, projekt)

        with tabs[2]:
            _render_dokumente(db, projekt)

        with tabs[3]:
            _render_kosten_uebersicht(db, projekt)

        with tabs[4]:
            _render_kontakt(db, projekt)


def _render_uebersicht(projekt: UnfallProjekt):
    """Rendert die Fallübersicht"""

    st.markdown("### Ihr Schadensfall auf einen Blick")

    # Status-Karte
    col1, col2, col3 = st.columns(3)

    with col1:
        status_farben = {
            "AKTIV": "success",
            "IN_BEARBEITUNG": "warning",
            "ABGESCHLOSSEN": "info",
            "STORNIERT": "danger"
        }
        st.markdown(
            f"**Status:** {badge(projekt.status or 'IN BEARBEITUNG', status_farben.get(projekt.status, 'info'))}",
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(f"**Aktenzeichen:** {projekt.aktenzeichen or projekt.projektnummer}")

    with col3:
        if projekt.datum_unfall:
            st.markdown(f"**Unfalldatum:** {projekt.datum_unfall.strftime('%d.%m.%Y')}")

    st.markdown("---")

    # Wichtige Informationen
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Unfalldaten")

        if projekt.ort_unfall:
            st.markdown(f"**Unfallort:** {projekt.ort_unfall}")

        if projekt.beschreibung_unfall:
            beschreibung = projekt.beschreibung_unfall
            st.markdown(f"**Hergang:** {beschreibung[:200]}..." if len(beschreibung) > 200 else f"**Hergang:** {beschreibung}")

        # Schuldfrage aus Prozent
        if projekt.schuld_eigen_prozent is not None:
            if projekt.schuld_eigen_prozent == 0:
                schuld_text = "Keine Eigenschuld"
            elif projekt.schuld_eigen_prozent == 100:
                schuld_text = "Volle Eigenschuld"
            else:
                schuld_text = f"{projekt.schuld_eigen_prozent}% Eigenschuld"
            st.markdown(f"**Schuldfrage:** {schuld_text}")

    with col2:
        st.markdown("#### Fahrzeug")

        if projekt.kfz_eigen:
            fz = projekt.kfz_eigen
            st.markdown(f"**Fahrzeug:** {fz.hersteller} {fz.modell}")
            st.markdown(f"**Kennzeichen:** {fz.kennzeichen}")
            if fz.erstzulassung:
                st.markdown(f"**Erstzulassung:** {fz.erstzulassung.strftime('%m/%Y')}")

    st.markdown("---")

    # Nächste Schritte / Hinweise
    st.markdown("#### Aktuelle Hinweise")

    hinweise = []

    # Prüfe auf ausstehende Aktionen
    if not projekt.dokumente or len([d for d in projekt.dokumente if d.dokument_typ == "VOLLMACHT"]) == 0:
        hinweise.append("Bitte unterschreiben Sie die Vollmacht und laden Sie diese hoch.")

    if not projekt.kfz_eigen:
        hinweise.append("Fahrzeugdaten wurden noch nicht erfasst.")

    if hinweise:
        for hinweis in hinweise:
            st.warning(hinweis)
    else:
        st.success("Derzeit sind keine Aktionen Ihrerseits erforderlich. Wir melden uns bei Neuigkeiten.")


def _render_fortschritt(db: Session, projekt: UnfallProjekt):
    """Rendert den Fallfortschritt als Timeline"""

    st.markdown("### Fortschritt Ihres Schadensfalles")

    # Meilensteine laden
    meilensteine = db.query(TimelineMeilenstein).filter(
        TimelineMeilenstein.unfallprojekt_id == projekt.id
    ).order_by(TimelineMeilenstein.reihenfolge).all()

    if not meilensteine:
        st.info("Der Fortschritt wird hier angezeigt, sobald Meilensteine erfasst wurden.")
        return

    # Fortschrittsbalken
    erledigt = len([m for m in meilensteine if m.status == MeilensteinStatus.ERLEDIGT])
    gesamt = len(meilensteine)
    prozent = int(erledigt / gesamt * 100) if gesamt > 0 else 0

    st.progress(prozent / 100)
    st.caption(f"{erledigt} von {gesamt} Schritten abgeschlossen ({prozent}%)")

    st.markdown("---")

    # Timeline anzeigen
    for ms in meilensteine:
        col1, col2 = st.columns([1, 4])

        with col1:
            if ms.status == MeilensteinStatus.ERLEDIGT:
                st.markdown("**Erledigt**")
            elif ms.status == MeilensteinStatus.IN_BEARBEITUNG:
                st.markdown("**In Bearbeitung**")
            else:
                st.markdown("Ausstehend")

        with col2:
            # Titel aus code (lesbar formatiert) oder beschreibung
            titel = ms.beschreibung or ms.code.replace("_", " ").title() if ms.code else "Meilenstein"
            if ms.status == MeilensteinStatus.ERLEDIGT:
                st.markdown(f"~~{titel}~~")
                if ms.erledigt_am:
                    st.caption(f"Abgeschlossen am {ms.erledigt_am.strftime('%d.%m.%Y')}")
            elif ms.status == MeilensteinStatus.IN_BEARBEITUNG:
                st.markdown(f"**{titel}**")
            else:
                st.markdown(titel)

        st.markdown("---")


def _render_dokumente(db: Session, projekt: UnfallProjekt):
    """Rendert die Dokumentenübersicht für den Mandanten"""

    st.markdown("### Dokumente")

    user_id = st.session_state.get("user_id")

    # Dokumente laden - freigegebene oder vom Mandanten selbst hochgeladene
    dokumente = db.query(Dokument).filter(
        Dokument.unfallprojekt_id == projekt.id,
        Dokument.geloescht == False,
        # Zeige freigegebene ODER vom Mandanten hochgeladene Dokumente
        ((Dokument.freigabe_erteilt == True) | (Dokument.hochgeladen_von_user_id == user_id))
    ).order_by(Dokument.erstellt_am.desc()).all()

    if not dokumente:
        st.info("Es wurden noch keine Dokumente hochgeladen oder für Sie freigegeben.")
    else:
        # Dokumente nach Typ gruppieren
        dok_typen = {}
        for dok in dokumente:
            typ = dok.dokument_typ_anzeige
            if typ not in dok_typen:
                dok_typen[typ] = []
            dok_typen[typ].append(dok)

        for typ, doks in dok_typen.items():
            with st.expander(f"{typ} ({len(doks)})", expanded=True):
                for dok in doks:
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(f"**{dok.original_dateiname}**")
                        st.caption(f"Hochgeladen: {dok.erstellt_am.strftime('%d.%m.%Y') if dok.erstellt_am else 'Unbekannt'}")

                    with col2:
                        # Status anzeigen
                        if dok.hochgeladen_von_user_id == user_id and not dok.freigabe_erteilt:
                            st.caption("⏳ Wird geprüft")
                        elif dok.freigabe_erteilt:
                            st.caption("✅ Freigegeben")

                    with col3:
                        # Download mit Storage-Abstraktion
                        try:
                            file_bytes = dok.get_bytes()
                            if file_bytes:
                                st.download_button(
                                    "📥 Download",
                                    data=file_bytes,
                                    file_name=dok.original_dateiname,
                                    key=f"dl_{dok.id}"
                                )
                        except Exception:
                            st.caption("Nicht verfügbar")

                    st.markdown("---")

    # Upload-Bereich für Mandanten
    st.markdown("### Dokument hochladen")
    st.caption("Laden Sie hier Dokumente hoch, die für Ihren Fall relevant sind.")

    uploaded_file = st.file_uploader(
        "Datei auswählen",
        type=["pdf", "jpg", "jpeg", "png", "doc", "docx"],
        key="mandant_upload"
    )

    if uploaded_file:
        from src.models.enums import DokumentTyp

        typ_mapping = {
            "Vollmacht": DokumentTyp.VOLLMACHT,
            "Personalausweis": DokumentTyp.PERSONALAUSWEIS,
            "Fahrzeugschein": DokumentTyp.FAHRZEUGSCHEIN,
            "Sonstiges": DokumentTyp.SONSTIG
        }

        dokument_typ_str = st.selectbox(
            "Dokumenttyp",
            list(typ_mapping.keys())
        )

        if st.button("Hochladen", type="primary"):
            try:
                import os
                from datetime import datetime

                # Speicherpfad erstellen
                upload_dir = f"uploads/mandanten/{projekt.id}"
                os.makedirs(upload_dir, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dateiname = f"{timestamp}_{uploaded_file.name}"
                dateipfad = os.path.join(upload_dir, dateiname)

                # Datei speichern
                with open(dateipfad, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Dokument in DB erstellen
                neues_dokument = Dokument(
                    unfallprojekt_id=projekt.id,
                    hochgeladen_von_user_id=user_id,
                    dokument_typ=typ_mapping[dokument_typ_str],
                    original_dateiname=uploaded_file.name,
                    dateipfad=dateipfad,
                    mime_typ=uploaded_file.type,
                    dateigroesse=uploaded_file.size,
                    storage_provider="local",
                    storage_key=dateipfad,
                    freigabe_erforderlich=True,
                    freigabe_erteilt=False,
                    status="HOCHGELADEN"
                )
                db.add(neues_dokument)
                db.commit()

                st.success("Dokument erfolgreich hochgeladen!")
                st.info("Das Dokument wird geprüft und ist dann in der Übersicht sichtbar.")
                st.rerun()

            except Exception as e:
                st.error(f"Fehler beim Hochladen: {str(e)}")


def _render_kosten_uebersicht(db: Session, projekt: UnfallProjekt):
    """Rendert die Kostenübersicht für den Mandanten"""

    st.markdown("### Kostenübersicht")
    st.caption("Hier sehen Sie alle geltend gemachten Schadenspositionen.")

    # Kosten laden
    kosten = db.query(KostenPosition).filter(
        KostenPosition.unfallprojekt_id == projekt.id
    ).all()

    if not kosten:
        st.info("Es wurden noch keine Kostenpositionen erfasst.")
        return

    # Zusammenfassung
    gesamt_gefordert = sum((k.betrag_brutto or 0) for k in kosten)
    gesamt_erstattet = sum((k.bezahlt_betrag or 0) for k in kosten)
    offen = gesamt_gefordert - gesamt_erstattet

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Gefordert", f"{float(gesamt_gefordert):,.2f} EUR")

    with col2:
        st.metric("Erstattet", f"{float(gesamt_erstattet):,.2f} EUR")

    with col3:
        st.metric("Offen", f"{float(offen):,.2f} EUR")

    st.markdown("---")

    # Detailaufstellung
    st.markdown("#### Detailaufstellung")

    for k in kosten:
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"**{k.beschreibung or 'Ohne Beschreibung'}**")
            kategorie_text = k.kategorie.value if k.kategorie else "Sonstig"
            st.caption(kategorie_text)

        with col2:
            st.markdown(f"{float(k.betrag_brutto or 0):,.2f} EUR")

        with col3:
            betrag_gefordert = k.betrag_brutto or 0
            betrag_gezahlt = k.bezahlt_betrag or 0

            if k.bezahlt and betrag_gezahlt >= betrag_gefordert and betrag_gefordert > 0:
                # Vollständig erstattet (gezahlter Betrag >= geforderter Betrag)
                st.markdown(badge("Erstattet", "success"), unsafe_allow_html=True)
            elif betrag_gezahlt > 0 and betrag_gezahlt < betrag_gefordert:
                # Teilweise erstattet (es wurde etwas gezahlt, aber weniger als gefordert)
                st.markdown(badge("Teilweise", "info"), unsafe_allow_html=True)
                st.caption(f"({float(betrag_gezahlt):,.2f} EUR)")
            else:
                # Noch offen (nichts gezahlt)
                st.markdown(badge("Offen", "warning"), unsafe_allow_html=True)

    st.markdown("---")

    # Hinweis
    st.info("""
    **Hinweis:** Die Erstattung erfolgt durch die gegnerische Versicherung.
    Der Prozess kann mehrere Wochen dauern. Bei Fragen wenden Sie sich bitte an Ihren Anwalt.
    """)


def _render_kontakt(db: Session, projekt: UnfallProjekt):
    """Rendert den Kontaktbereich"""

    st.markdown("### Kontakt")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Ihr Anwalt")

        if projekt.anwalt:
            st.markdown(f"**{projekt.anwalt.vorname or ''} {projekt.anwalt.nachname or ''}**")
            if projekt.anwalt.email:
                st.markdown(f"E-Mail: {projekt.anwalt.email}")
            if projekt.anwalt.telefonnummer:
                st.markdown(f"Telefon: {projekt.anwalt.telefonnummer}")
        else:
            st.info("Noch kein Anwalt zugewiesen.")

    with col2:
        st.markdown("#### Ihre Werkstatt")

        if projekt.werkstatt:
            st.markdown(f"**{projekt.werkstatt.vorname or ''} {projekt.werkstatt.nachname or ''}**")
            if projekt.werkstatt.email:
                st.markdown(f"E-Mail: {projekt.werkstatt.email}")
            if projekt.werkstatt.telefonnummer:
                st.markdown(f"Telefon: {projekt.werkstatt.telefonnummer}")
        else:
            st.info("Noch keine Werkstatt zugewiesen.")

    st.markdown("---")

    # Nachricht senden
    st.markdown("#### Nachricht an Ihren Anwalt")

    nachricht = st.text_area(
        "Ihre Nachricht",
        placeholder="Schreiben Sie hier Ihre Nachricht...",
        height=150
    )

    if st.button("Nachricht senden", type="primary", use_container_width=True):
        if nachricht:
            # Hier würde die Nachrichtenlogik implementiert
            st.success("Ihre Nachricht wurde gesendet!")
        else:
            st.error("Bitte geben Sie eine Nachricht ein.")

    st.markdown("---")

    # FAQ
    with st.expander("Häufige Fragen"):
        st.markdown("""
        **Wie lange dauert die Schadensregulierung?**

        Die Dauer hängt von verschiedenen Faktoren ab. In der Regel dauert es
        4-8 Wochen bis zur ersten Zahlung der Versicherung. Bei strittigen
        Fällen kann es länger dauern.

        ---

        **Muss ich in Vorleistung gehen?**

        Nein, in der Regel nicht. Die Werkstatt rechnet direkt mit der
        Versicherung ab. Nur bei Eigenanteilen oder nicht erstattungsfähigen
        Positionen kann eine Zahlung erforderlich sein.

        ---

        **Was ist ein merkantiler Minderwert?**

        Der merkantile Minderwert ist der Wertverlust, den ein Fahrzeug
        trotz fachgerechter Reparatur erleidet, weil es als "Unfallwagen" gilt.

        ---

        **Kann ich mir die Werkstatt aussuchen?**

        Ja! Als Geschädigter haben Sie freie Werkstattwahl. Sie müssen nicht
        in eine Partnerwerkstatt der Versicherung gehen.
        """)
