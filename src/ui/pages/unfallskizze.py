"""
Unfallskizze-Tool UI-Seite
Grafische Darstellung des Unfallhergangs
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.unfallskizze import UnfallskizzeService, Unfallskizze, SkizzenElementTyp


def render_unfallskizze():
    """Rendert die Unfallskizze-Seite"""
    st.title("📐 Unfallskizze")

    # Projekt-Auswahl
    projekt_id = st.session_state.get("aktives_projekt_id")

    if not projekt_id:
        with get_session() as db:
            from src.models import UnfallProjekt
            projekte = db.query(UnfallProjekt).order_by(UnfallProjekt.erstellt_am.desc()).limit(50).all()

            if not projekte:
                st.warning("Keine Projekte vorhanden")
                return

            projekt_options = {p.id: f"{p.projektnummer} - {p.aktenzeichen or 'Ohne Az.'}" for p in projekte}
            projekt_id = st.selectbox(
                "Projekt auswählen",
                list(projekt_options.keys()),
                format_func=lambda x: projekt_options.get(x, "")
            )

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Skizzen", "Neue Skizze", "Editor"
    ])

    with tab1:
        _render_skizzen_liste(projekt_id)

    with tab2:
        _render_neue_skizze(projekt_id)

    with tab3:
        _render_skizzen_editor(projekt_id)


def _render_skizzen_liste(projekt_id: int):
    """Zeigt vorhandene Skizzen"""
    st.subheader("Vorhandene Skizzen")

    with get_session() as db:
        service = UnfallskizzeService(db)
        skizzen = service.skizzen_fuer_projekt(projekt_id)

        if not skizzen:
            st.info("Noch keine Skizzen für dieses Projekt")
            return

        for skizze in skizzen:
            with st.expander(f"📐 {skizze.titel} (v{skizze.version})", expanded=False):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.write(f"**Beschreibung:** {skizze.beschreibung or '-'}")
                    st.write(f"**Elemente:** {len(skizze.elemente)}")
                    st.write(f"**Größe:** {skizze.canvas_breite} x {skizze.canvas_hoehe} px")
                    st.write(f"**Erstellt:** {skizze.erstellt_am.strftime('%d.%m.%Y %H:%M')}")

                with col2:
                    if st.button("✏️ Bearbeiten", key=f"edit_{skizze.id}"):
                        st.session_state["edit_skizze_id"] = skizze.id
                        st.rerun()

                    if st.button("📥 SVG Export", key=f"svg_{skizze.id}"):
                        svg_content = service.generiere_svg(skizze)
                        st.download_button(
                            "SVG herunterladen",
                            data=svg_content,
                            file_name=f"unfallskizze_{skizze.id}.svg",
                            mime="image/svg+xml",
                            key=f"dl_{skizze.id}"
                        )

                    if st.button("🗑️ Löschen", key=f"del_{skizze.id}"):
                        service.skizze_loeschen(skizze.id)
                        st.success("Skizze gelöscht")
                        st.rerun()

                # SVG-Vorschau
                if skizze.elemente:
                    st.markdown("**Vorschau:**")
                    svg_content = service.generiere_svg(skizze)
                    st.markdown(f'<div style="border: 1px solid #ddd; padding: 10px; background: #f5f5f5;">{svg_content}</div>', unsafe_allow_html=True)


def _render_neue_skizze(projekt_id: int):
    """Formular für neue Skizze"""
    st.subheader("Neue Skizze erstellen")

    col1, col2 = st.columns(2)

    with col1:
        titel = st.text_input("Titel", value="Unfallskizze")
        beschreibung = st.text_area("Beschreibung", height=100)

    with col2:
        canvas_breite = st.number_input("Breite (px)", min_value=400, max_value=1600, value=800)
        canvas_hoehe = st.number_input("Höhe (px)", min_value=300, max_value=1200, value=600)

        vorlage = st.selectbox(
            "Vorlage verwenden",
            ["Leer", "Kreuzung", "Gerade Straße", "Parkplatz"]
        )

    if st.button("Skizze erstellen", type="primary"):
        with get_session() as db:
            service = UnfallskizzeService(db)
            user_id = st.session_state.get("user_id")

            if vorlage == "Kreuzung":
                skizze = service.erstelle_standard_kreuzung_skizze(
                    projekt_id=projekt_id,
                    erstellt_von_user_id=user_id
                )
                skizze.titel = titel
                skizze.beschreibung = beschreibung
            else:
                skizze = service.skizze_erstellen(
                    projekt_id=projekt_id,
                    titel=titel,
                    beschreibung=beschreibung,
                    erstellt_von_user_id=user_id
                )

            skizze.canvas_breite = canvas_breite
            skizze.canvas_hoehe = canvas_hoehe

            st.success(f"Skizze '{skizze.titel}' erstellt!")
            st.session_state["edit_skizze_id"] = skizze.id
            st.rerun()


def _render_skizzen_editor(projekt_id: int):
    """Skizzen-Editor"""
    st.subheader("Skizzen-Editor")

    skizze_id = st.session_state.get("edit_skizze_id")

    if not skizze_id:
        # Skizze auswählen
        with get_session() as db:
            service = UnfallskizzeService(db)
            skizzen = service.skizzen_fuer_projekt(projekt_id)

            if not skizzen:
                st.info("Bitte erst eine Skizze erstellen")
                return

            skizze_options = {s.id: s.titel for s in skizzen}
            skizze_id = st.selectbox(
                "Skizze auswählen",
                list(skizze_options.keys()),
                format_func=lambda x: skizze_options.get(x, "")
            )

    with get_session() as db:
        service = UnfallskizzeService(db)
        skizze = db.query(Unfallskizze).get(skizze_id)

        if not skizze:
            st.error("Skizze nicht gefunden")
            return

        st.markdown(f"**Bearbeite:** {skizze.titel}")

        # Elemente-Palette
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("### Elemente hinzufügen")

            element_typ = st.selectbox(
                "Element-Typ",
                [t for t in SkizzenElementTyp],
                format_func=lambda t: {
                    SkizzenElementTyp.FAHRZEUG: "🚗 Fahrzeug",
                    SkizzenElementTyp.STRASSE: "🛣️ Straße",
                    SkizzenElementTyp.KREUZUNG: "✚ Kreuzung",
                    SkizzenElementTyp.FUSSGAENGER: "🚶 Fußgänger",
                    SkizzenElementTyp.RADFAHRER: "🚴 Radfahrer",
                    SkizzenElementTyp.AMPEL: "🚦 Ampel",
                    SkizzenElementTyp.SCHILD: "🛑 Schild",
                    SkizzenElementTyp.MARKIERUNG: "📍 Markierung",
                    SkizzenElementTyp.PFEIL: "➡️ Bewegungspfeil",
                    SkizzenElementTyp.TEXT: "📝 Text",
                    SkizzenElementTyp.BAUM: "🌳 Baum",
                    SkizzenElementTyp.GEBAEUDE: "🏢 Gebäude"
                }.get(t, str(t))
            )

            # Position
            x_pos = st.number_input("X-Position", min_value=0, max_value=skizze.canvas_breite, value=skizze.canvas_breite // 2)
            y_pos = st.number_input("Y-Position", min_value=0, max_value=skizze.canvas_hoehe, value=skizze.canvas_hoehe // 2)

            # Spezifische Eigenschaften
            eigenschaften = {}

            if element_typ == SkizzenElementTyp.FAHRZEUG:
                fahrzeug_typ = st.selectbox(
                    "Fahrzeugtyp",
                    ["pkw", "lkw", "motorrad", "fahrrad"],
                    format_func=lambda x: {"pkw": "PKW", "lkw": "LKW", "motorrad": "Motorrad", "fahrrad": "Fahrrad"}.get(x, x)
                )
                eigenschaften["fahrzeug_typ"] = fahrzeug_typ

                label = st.text_input("Beschriftung", max_chars=3, placeholder="A/B")
                if label:
                    eigenschaften["label"] = label

                farbe = st.color_picker("Farbe", "#3498db")
                eigenschaften["farbe"] = farbe

            elif element_typ == SkizzenElementTyp.PFEIL:
                laenge = st.number_input("Länge", min_value=20, max_value=200, value=50)
                eigenschaften["laenge"] = laenge

                gestrichelt = st.checkbox("Gestrichelt")
                eigenschaften["gestrichelt"] = gestrichelt

                farbe = st.color_picker("Farbe", "#e74c3c")
                eigenschaften["farbe"] = farbe

            elif element_typ == SkizzenElementTyp.TEXT:
                text = st.text_input("Text")
                eigenschaften["text"] = text

                schriftgroesse = st.number_input("Schriftgröße", min_value=8, max_value=48, value=14)
                eigenschaften["schriftgroesse"] = schriftgroesse

            elif element_typ == SkizzenElementTyp.STRASSE:
                breite = st.number_input("Breite", min_value=50, max_value=300, value=100)
                eigenschaften["breite"] = breite

                hoehe = st.number_input("Länge", min_value=100, max_value=600, value=300)
                eigenschaften["hoehe"] = hoehe

            if st.button("Element hinzufügen", type="primary"):
                try:
                    service.element_hinzufuegen(
                        skizze_id=skizze.id,
                        element_typ=element_typ,
                        x=x_pos,
                        y=y_pos,
                        eigenschaften=eigenschaften
                    )
                    st.success("Element hinzugefügt")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")

        with col2:
            st.markdown("### Vorschau")

            # SVG rendern
            svg_content = service.generiere_svg(skizze)
            st.markdown(
                f'<div style="border: 2px solid #333; background: {skizze.hintergrund_farbe}; overflow: auto;">{svg_content}</div>',
                unsafe_allow_html=True
            )

            # Elemente-Liste
            st.markdown("### Vorhandene Elemente")

            if skizze.elemente:
                for element in skizze.elemente:
                    col_a, col_b, col_c = st.columns([2, 1, 1])

                    with col_a:
                        st.write(f"**{element.get('typ')}** @ ({element.get('x')}, {element.get('y')})")

                    with col_b:
                        rotation = st.number_input(
                            "Rotation",
                            min_value=0,
                            max_value=360,
                            value=element.get('rotation', 0),
                            key=f"rot_{element.get('id')}"
                        )

                        if rotation != element.get('rotation', 0):
                            if st.button("Drehen", key=f"rotate_{element.get('id')}"):
                                service.element_aktualisieren(
                                    skizze.id,
                                    element.get('id'),
                                    {"rotation": rotation}
                                )
                                st.rerun()

                    with col_c:
                        if st.button("🗑️", key=f"del_el_{element.get('id')}"):
                            service.element_loeschen(skizze.id, element.get('id'))
                            st.rerun()
            else:
                st.info("Keine Elemente vorhanden")

            # Export-Optionen
            st.markdown("### Export")

            col_exp1, col_exp2 = st.columns(2)

            with col_exp1:
                st.download_button(
                    "📥 SVG herunterladen",
                    data=svg_content,
                    file_name=f"{skizze.titel.replace(' ', '_')}.svg",
                    mime="image/svg+xml"
                )

            with col_exp2:
                # Als HTML-Seite für Druck
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{skizze.titel}</title>
    <style>
        body {{ margin: 20px; font-family: Arial, sans-serif; }}
        h1 {{ font-size: 18px; }}
        .info {{ margin-bottom: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <h1>Unfallskizze: {skizze.titel}</h1>
    <div class="info">
        Erstellt am: {skizze.erstellt_am.strftime('%d.%m.%Y %H:%M')}<br>
        {skizze.beschreibung or ''}
    </div>
    {svg_content}
</body>
</html>
"""
                st.download_button(
                    "🖨️ Druckversion (HTML)",
                    data=html_content,
                    file_name=f"{skizze.titel.replace(' ', '_')}.html",
                    mime="text/html"
                )
