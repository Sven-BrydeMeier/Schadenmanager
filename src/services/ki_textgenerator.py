"""
KI-Textgenerator für Anspruchsschreiben und Erwiderungen
"""
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, KostenPosition, KostenKategorie,
    Korrespondenz, KorrespondenzRichtung, Dokument
)
from src.config.settings import get_settings


class KITextGenerator:
    """Generiert Schreiben und Erwiderungen mittels KI"""

    def __init__(self):
        self.settings = get_settings()

    def generiere_anspruchsschreiben(
        self,
        projekt: UnfallProjekt,
        db: Session
    ) -> Tuple[Optional[str], str]:
        """
        Generiert ein Anspruchsschreiben an die gegnerische Versicherung.

        Args:
            projekt: Das Unfallprojekt
            db: Datenbank-Session

        Returns:
            Tuple aus (generierter Text oder None, Fehlermeldung)
        """
        # Daten sammeln
        kontext = self._sammle_projekt_kontext(projekt)

        prompt = f"""Erstelle ein professionelles Anspruchsschreiben eines Rechtsanwalts an die gegnerische Haftpflichtversicherung.

FALLDATEN:
{json.dumps(kontext, ensure_ascii=False, indent=2)}

ANFORDERUNGEN:
1. Formelles Anwaltsschreiben mit professionellem Ton
2. Klare Gliederung: Sachverhalt, Anspruchsgrundlage, Forderungen
3. Alle Kostenpositionen einzeln aufführen mit Beträgen
4. Frist zur Regulierung setzen (typisch: 2-3 Wochen)
5. Verweis auf beigefügte Unterlagen (Gutachten, Rechnungen etc.)
6. Korrekte rechtliche Terminologie (BGB §§ 823, 249, 7 StVG etc.)

Das Schreiben soll im Namen des Rechtsanwalts an die gegnerische Versicherung gerichtet sein.
Platzhalter für variable Daten mit [PLATZHALTER] markieren.

Generiere das vollständige Schreiben:"""

        return self._call_ki(prompt)

    def generiere_kuerzungserwiderung(
        self,
        projekt: UnfallProjekt,
        kuerzungen: List[Dict[str, Any]],
        db: Session
    ) -> Tuple[Optional[str], str]:
        """
        Generiert eine Erwiderung auf ein Kürzungsschreiben.

        Args:
            projekt: Das Unfallprojekt
            kuerzungen: Liste der Kürzungen mit Positionen und Begründungen
            db: Datenbank-Session

        Returns:
            Tuple aus (generierter Text oder None, Fehlermeldung)
        """
        kontext = self._sammle_projekt_kontext(projekt)
        kontext["kuerzungen"] = kuerzungen

        prompt = f"""Erstelle eine professionelle Erwiderung eines Rechtsanwalts auf das Kürzungsschreiben der gegnerischen Versicherung.

FALLDATEN UND KÜRZUNGEN:
{json.dumps(kontext, ensure_ascii=False, indent=2)}

ANFORDERUNGEN:
1. Professioneller, aber bestimmter Ton
2. Jede Kürzung einzeln behandeln und widerlegen
3. Rechtliche Argumente für jede Position:
   - Bei Reparaturkosten: Verweis auf Werkstatt des Vertrauens, ortsübliche Preise
   - Bei Gutachterkosten: BVSK-Honorartabelle, Erforderlichkeit
   - Bei Ersatzwagen: Schwacke-Liste, Erforderlichkeit der Klasse
   - Bei Wertminderung: Merkantiler Minderwert nach BGH-Rechtsprechung
4. Fristsetzung zur vollständigen Regulierung
5. Androhung gerichtlicher Schritte bei Ablehnung

Generiere das vollständige Erwiderungsschreiben:"""

        return self._call_ki(prompt)

    def generiere_mandanteninformation(
        self,
        projekt: UnfallProjekt,
        thema: str,
        db: Session
    ) -> Tuple[Optional[str], str]:
        """
        Generiert eine Mandanteninformation zu einem bestimmten Thema.

        Args:
            projekt: Das Unfallprojekt
            thema: Das Thema der Information (z.B. "Verfahrensstand", "Kürzungen")
            db: Datenbank-Session

        Returns:
            Tuple aus (generierter Text oder None, Fehlermeldung)
        """
        kontext = self._sammle_projekt_kontext(projekt)

        prompt = f"""Erstelle eine verständliche Mandanteninformation zum Thema "{thema}".

FALLDATEN:
{json.dumps(kontext, ensure_ascii=False, indent=2)}

ANFORDERUNGEN:
1. Verständliche Sprache für Laien (kein Juristendeutsch)
2. Sachliche, aber freundliche Formulierung
3. Klare Erklärung des aktuellen Stands
4. Nächste Schritte aufzeigen
5. Bei Kürzungen: Erklärung warum widersprochen wird
6. Keine übermäßig technischen Details

Das Schreiben soll vom Rechtsanwalt an den Mandanten (Unfallopfer) gerichtet sein.

Generiere die Mandanteninformation:"""

        return self._call_ki(prompt)

    def _sammle_projekt_kontext(self, projekt: UnfallProjekt) -> Dict[str, Any]:
        """Sammelt alle relevanten Projektdaten für die KI"""

        # Fahrzeugdaten
        fahrzeug_eigen = None
        if projekt.kfz_eigen:
            fahrzeug_eigen = {
                "kennzeichen": projekt.kfz_eigen.kennzeichen,
                "hersteller": projekt.kfz_eigen.hersteller,
                "modell": projekt.kfz_eigen.modell,
                "halter": projekt.kfz_eigen.halter_name
            }

        fahrzeug_gegner = None
        if projekt.kfz_gegner:
            fahrzeug_gegner = {
                "kennzeichen": projekt.kfz_gegner.kennzeichen,
                "hersteller": projekt.kfz_gegner.hersteller,
                "modell": projekt.kfz_gegner.modell
            }

        # Kostenpositionen
        kostenpositionen = []
        for kp in projekt.kostenpositionen:
            kostenpositionen.append({
                "kategorie": kp.kategorie.value if kp.kategorie else "SONSTIG",
                "beschreibung": kp.beschreibung,
                "betrag_brutto": kp.betrag_brutto,
                "status": kp.status_ampel.value if kp.status_ampel else "ROT",
                "gekuerzt": kp.gekuerzt,
                "freigegeben_betrag": kp.von_versicherung_freigegeben_betrag,
                "kuerzung_grund": kp.kuerzung_grund
            })

        # Gesamtsummen
        summe_gefordert = sum(kp.betrag_brutto or 0 for kp in projekt.kostenpositionen)
        summe_freigegeben = sum(kp.von_versicherung_freigegeben_betrag or 0 for kp in projekt.kostenpositionen)

        return {
            "projektnummer": projekt.projektnummer,
            "unfalldatum": projekt.datum_unfall.strftime("%d.%m.%Y") if projekt.datum_unfall else None,
            "unfallort": projekt.ort_unfall,
            "unfallbeschreibung": projekt.beschreibung_unfall,
            "schuld_eigen_prozent": projekt.schuld_eigen_prozent,
            "fahrzeug_eigen": fahrzeug_eigen,
            "fahrzeug_gegner": fahrzeug_gegner,
            "kostenpositionen": kostenpositionen,
            "summe_gefordert": summe_gefordert,
            "summe_freigegeben": summe_freigegeben,
            "differenz": summe_gefordert - summe_freigegeben
        }

    def _call_ki(self, prompt: str) -> Tuple[Optional[str], str]:
        """Ruft die KI-API auf"""
        try:
            if self.settings.ki_provider == "anthropic" and self.settings.anthropic_api_key:
                return self._call_anthropic(prompt)
            elif self.settings.openai_api_key:
                return self._call_openai(prompt)
            else:
                return None, "Keine KI-API konfiguriert"
        except Exception as e:
            return None, f"KI-Fehler: {str(e)}"

    def _call_openai(self, prompt: str) -> Tuple[Optional[str], str]:
        """Ruft die OpenAI API auf"""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Du bist ein erfahrener Rechtsanwalt spezialisiert auf Verkehrsrecht und Schadensregulierung in Deutschland. Du erstellst professionelle Schreiben und Stellungnahmen."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )

            return response.choices[0].message.content, ""

        except Exception as e:
            return None, f"OpenAI-Fehler: {str(e)}"

    def _call_anthropic(self, prompt: str) -> Tuple[Optional[str], str]:
        """Ruft die Anthropic API auf"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system="Du bist ein erfahrener Rechtsanwalt spezialisiert auf Verkehrsrecht und Schadensregulierung in Deutschland. Du erstellst professionelle Schreiben und Stellungnahmen.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.content[0].text, ""

        except Exception as e:
            return None, f"Anthropic-Fehler: {str(e)}"


# Singleton-Instanz
_generator = None


def get_ki_textgenerator() -> KITextGenerator:
    """Gibt die Singleton-Instanz des KI-Textgenerators zurück"""
    global _generator
    if _generator is None:
        _generator = KITextGenerator()
    return _generator
