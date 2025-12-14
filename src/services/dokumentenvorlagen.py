"""
Dokumentenvorlagen-Service für automatische Dokumentenerstellung
"""
from datetime import datetime
from typing import Optional, Dict
from jinja2 import Template

from src.models import UnfallProjekt


class DokumentenvorlagenService:
    """Service für Dokumentenvorlagen"""

    def generiere_dokument(
        self,
        vorlage_typ: str,
        projekt: UnfallProjekt,
        zusatz_daten: Optional[Dict] = None
    ) -> str:
        """
        Generiert ein Dokument aus einer Vorlage.

        Args:
            vorlage_typ: Typ der Vorlage
            projekt: Das Unfallprojekt
            zusatz_daten: Zusätzliche Daten für die Vorlage

        Returns:
            Das generierte Dokument als Text
        """
        vorlage = VORLAGEN.get(vorlage_typ)
        if not vorlage:
            raise ValueError(f"Unbekannter Vorlagentyp: {vorlage_typ}")

        # Daten für Template zusammenstellen
        daten = self._erstelle_template_daten(projekt, zusatz_daten)

        # Template rendern
        template = Template(vorlage)
        return template.render(**daten)

    def _erstelle_template_daten(
        self,
        projekt: UnfallProjekt,
        zusatz_daten: Optional[Dict] = None
    ) -> Dict:
        """Erstellt die Daten für das Template"""
        daten = {
            "datum_heute": datetime.now().strftime("%d.%m.%Y"),
            "aktenzeichen": projekt.aktenzeichen or projekt.projektnummer,
            "projektnummer": projekt.projektnummer,
            "unfalldatum": projekt.datum_unfall.strftime("%d.%m.%Y") if projekt.datum_unfall else "",
            "unfallort": projekt.ort_unfall or "",
            "polizei_aktenzeichen": projekt.polizei_aktenzeichen or "",
            "schuld_gegner_prozent": 100 - (projekt.schuld_eigen_prozent or 0),
        }

        # Fahrzeugdaten
        if projekt.kfz_eigen:
            daten.update({
                "kfz_kennzeichen": projekt.kfz_eigen.kennzeichen,
                "kfz_modell": projekt.kfz_eigen.fahrzeug_bezeichnung,
                "kfz_halter": projekt.kfz_eigen.halter_name or "",
                "kfz_fin": projekt.kfz_eigen.fin or "",
            })

        if projekt.kfz_gegner:
            daten.update({
                "gegner_kennzeichen": projekt.kfz_gegner.kennzeichen,
                "gegner_versicherung": projekt.kfz_gegner.versicherung_name or "",
                "gegner_vs_nummer": projekt.kfz_gegner.versicherung_nr or "",
            })

        # Beteiligte
        if projekt.unfallopfer:
            daten.update({
                "mandant_name": projekt.unfallopfer.voller_name,
                "mandant_adresse": projekt.unfallopfer.adresse_komplett or "",
            })

        if projekt.anwalt:
            daten.update({
                "anwalt_name": projekt.anwalt.voller_name,
                "anwalt_kanzlei": projekt.anwalt.organisation.name if projekt.anwalt.organisation else "",
            })

        # Kosten summieren
        if projekt.kostenpositionen:
            summe = sum(k.betrag_gefordert or 0 for k in projekt.kostenpositionen)
            daten["schadenssumme"] = f"{float(summe):,.2f}"

        # Zusätzliche Daten
        if zusatz_daten:
            daten.update(zusatz_daten)

        return daten

    def get_verfuegbare_vorlagen(self) -> Dict[str, str]:
        """Gibt alle verfügbaren Vorlagen zurück"""
        return {
            "anspruchsschreiben": "Anspruchsschreiben an Versicherung",
            "vollmacht": "Vollmacht für Rechtsanwalt",
            "widerspruch": "Widerspruch gegen Kürzung",
            "mahnung": "Zahlungsmahnung",
            "abrechnung_fiktiv": "Fiktive Abrechnung",
            "abtretung": "Abtretungserklärung",
            "schweigepflicht": "Schweigepflichtentbindung",
            "datenschutz": "Datenschutzerklärung",
        }


# Dokumentenvorlagen
VORLAGEN = {
    "anspruchsschreiben": """
{{ anwalt_kanzlei }}
{{ datum_heute }}

An die
{{ gegner_versicherung }}
Schadenabteilung

Unser Zeichen: {{ aktenzeichen }}
Schaden-Nr.: {{ gegner_vs_nummer }}
Unfalltag: {{ unfalldatum }}

Sehr geehrte Damen und Herren,

in vorbezeichneter Angelegenheit zeigen wir an, dass uns Herr/Frau {{ mandant_name }} mit der Wahrnehmung seiner/ihrer rechtlichen Interessen beauftragt hat.

Ordnungsgemäße Bevollmächtigung wird anwaltlich versichert. Eine schriftliche Vollmacht wird auf Anforderung nachgereicht.

Am {{ unfalldatum }} ereignete sich in {{ unfallort }} ein Verkehrsunfall, an dem unser Mandant mit seinem Fahrzeug {{ kfz_kennzeichen }} ({{ kfz_modell }}) sowie der bei Ihnen versicherte Unfallgegner (Kennzeichen: {{ gegner_kennzeichen }}) beteiligt waren.

{% if polizei_aktenzeichen %}
Der Unfall wurde polizeilich aufgenommen (Az.: {{ polizei_aktenzeichen }}).
{% endif %}

Die Haftung Ihres Versicherungsnehmers dem Grunde nach dürfte bei einer Quote von {{ schuld_gegner_prozent }}% unstreitig sein.

Wir machen namens und in Vollmacht unseres Mandanten folgende Schadenspositionen geltend:

{{ schadenspositionen }}

Gesamtforderung: {{ schadenssumme }} EUR

Wir bitten um Regulierung des Schadens innerhalb von 14 Tagen auf das Konto unserer Mandantschaft.

Für Rückfragen stehen wir gerne zur Verfügung.

Mit freundlichen Grüßen

{{ anwalt_name }}
Rechtsanwalt
""",

    "vollmacht": """
VOLLMACHT

Hiermit bevollmächtige ich,

{{ mandant_name }}
{{ mandant_adresse }}

die Rechtsanwaltskanzlei

{{ anwalt_kanzlei }}
{{ anwalt_name }}

mich in der Schadensangelegenheit

Aktenzeichen: {{ aktenzeichen }}
Unfalldatum: {{ unfalldatum }}
Unfallort: {{ unfallort }}
Eigenes Fahrzeug: {{ kfz_kennzeichen }}

gegenüber der gegnerischen Haftpflichtversicherung ({{ gegner_versicherung }}) und allen weiteren Beteiligten zu vertreten.

Die Vollmacht umfasst insbesondere:
- Die außergerichtliche Vertretung
- Die Geltendmachung sämtlicher Schadensersatzansprüche
- Die Entgegennahme von Zahlungen
- Die Einholung von Auskünften
- Die Beauftragung von Sachverständigen

Diese Vollmacht gilt bis auf Widerruf.

{{ datum_heute }}

_______________________________
Unterschrift Vollmachtgeber
""",

    "widerspruch": """
{{ anwalt_kanzlei }}
{{ datum_heute }}

An die
{{ gegner_versicherung }}
Schadenabteilung

Unser Zeichen: {{ aktenzeichen }}
Ihr Zeichen: {{ gegner_vs_nummer }}
Betreff: Widerspruch gegen Ihre Abrechnung vom {{ kuerzung_datum }}

Sehr geehrte Damen und Herren,

gegen Ihre Schadensabrechnung vom {{ kuerzung_datum }} legen wir namens und in Vollmacht unserer Mandantschaft hiermit

WIDERSPRUCH

ein.

In Ihrem Schreiben haben Sie folgende Positionen gekürzt:

{{ kuerzungen }}

Diese Kürzungen sind aus folgenden Gründen nicht berechtigt:

{{ kuerzung_begruendung }}

Wir fordern Sie daher auf, den noch offenen Betrag in Höhe von {{ offener_betrag }} EUR innerhalb von 14 Tagen auf das bekannte Konto zu überweisen.

Sollte die Zahlung nicht fristgerecht erfolgen, werden wir unserer Mandantschaft die Einleitung gerichtlicher Schritte empfehlen.

Mit freundlichen Grüßen

{{ anwalt_name }}
Rechtsanwalt
""",

    "mahnung": """
{{ anwalt_kanzlei }}
{{ datum_heute }}

An die
{{ gegner_versicherung }}
Schadenabteilung

Unser Zeichen: {{ aktenzeichen }}
Ihr Zeichen: {{ gegner_vs_nummer }}

MAHNUNG

Sehr geehrte Damen und Herren,

trotz mehrfacher Aufforderung ist die Regulierung des oben genannten Schadens bislang nicht erfolgt.

Wir fordern Sie hiermit letztmalig auf, den Betrag in Höhe von

{{ offener_betrag }} EUR

bis zum {{ zahlungsfrist }} auf das Konto unserer Mandantschaft zu überweisen.

Sollte die Zahlung nicht fristgerecht erfolgen, werden wir ohne weitere Ankündigung Klage erheben. Die dadurch entstehenden Kosten gehen zu Ihren Lasten.

Mit freundlichen Grüßen

{{ anwalt_name }}
Rechtsanwalt
""",

    "abrechnung_fiktiv": """
{{ anwalt_kanzlei }}
{{ datum_heute }}

An die
{{ gegner_versicherung }}

Unser Zeichen: {{ aktenzeichen }}

Betreff: Fiktive Abrechnung

Sehr geehrte Damen und Herren,

unser Mandant hat sich entschieden, den Schaden an seinem Fahrzeug ({{ kfz_kennzeichen }}) fiktiv abzurechnen.

Gemäß dem beigefügten Gutachten des Sachverständigen betragen:

Reparaturkosten netto:     {{ reparaturkosten_netto }} EUR
Wertminderung:             {{ wertminderung }} EUR
Nutzungsausfall ({{ ausfall_tage }} Tage): {{ nutzungsausfall }} EUR
Gutachterkosten:           {{ gutachterkosten }} EUR
Kostenpauschale:           {{ kostenpauschale }} EUR

Gesamtforderung:           {{ gesamtforderung }} EUR

Wir bitten um Überweisung auf das bekannte Konto innerhalb von 14 Tagen.

Mit freundlichen Grüßen

{{ anwalt_name }}
Rechtsanwalt
""",

    "abtretung": """
ABTRETUNGSERKLÄRUNG

Der Unterzeichnende

{{ mandant_name }}
{{ mandant_adresse }}

tritt hiermit seine Ansprüche aus dem Verkehrsunfall vom {{ unfalldatum }} in {{ unfallort }}

- gegen den Unfallgegner (Fahrzeug {{ gegner_kennzeichen }})
- gegen die {{ gegner_versicherung }}

in Höhe der Reparaturkosten gemäß Gutachten/Kostenvoranschlag

an die

{{ abtretung_empfaenger }}

ab.

Die Abtretung erfolgt erfüllungshalber zur Sicherung der Forderungen des Abtretungsempfängers.

{{ datum_heute }}

_______________________________
{{ mandant_name }}
""",

    "schweigepflicht": """
ENTBINDUNG VON DER SCHWEIGEPFLICHT

Ich, {{ mandant_name }}, geboren am {{ geburtsdatum }},
wohnhaft: {{ mandant_adresse }}

entbinde hiermit

- alle mich behandelnden Ärzte
- Krankenhäuser und Kliniken
- Krankenkassen und Berufsgenossenschaften
- Rentenversicherungsträger

von ihrer Schweigepflicht gegenüber

{{ anwalt_kanzlei }}

soweit dies für die Geltendmachung meiner Schadensersatzansprüche aus dem Unfall vom {{ unfalldatum }} erforderlich ist.

{{ datum_heute }}

_______________________________
{{ mandant_name }}
""",

    "datenschutz": """
DATENSCHUTZERKLÄRUNG UND EINWILLIGUNG

Mandant: {{ mandant_name }}
Aktenzeichen: {{ aktenzeichen }}

Ich wurde darüber informiert, dass die Kanzlei {{ anwalt_kanzlei }} meine personenbezogenen Daten im Rahmen der Mandatsbearbeitung verarbeitet.

Dies umfasst insbesondere:
- Name, Adresse, Kontaktdaten
- Fahrzeugdaten
- Unfalldaten und -hergang
- Gesundheitsdaten (soweit für Personenschäden relevant)
- Bankverbindung für Zahlungen

Die Daten werden ausschließlich zur Durchsetzung meiner Ansprüche verwendet und an die gegnerische Versicherung, Gutachter und ggf. Gerichte übermittelt.

Ich willige in diese Datenverarbeitung ein.

{{ datum_heute }}

_______________________________
{{ mandant_name }}
"""
}


def get_dokumentenvorlagen_service() -> DokumentenvorlagenService:
    """Factory-Funktion für den Dokumentenvorlagen-Service"""
    return DokumentenvorlagenService()
