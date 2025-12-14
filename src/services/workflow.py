"""
Workflow-Templates für verschiedene Schadensarten
Automatisiert Prozessabläufe und erstellt Meilensteine
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, TimelineMeilenstein, MeilensteinStatus,
    Wiedervorlage, WiedervorlageTyp, WiedervorlagePrioritaet
)


class WorkflowTyp(str, Enum):
    """Verfügbare Workflow-Typen"""
    STANDARD = "standard"
    HAFTPFLICHT_GEGNER = "haftpflicht_gegner"
    HAFTPFLICHT_EIGEN = "haftpflicht_eigen"
    KASKO = "kasko"
    PERSONENSCHADEN = "personenschaden"
    TOTALSCHADEN = "totalschaden"
    BAGATELLE = "bagatelle"


# Workflow-Templates mit Meilensteinen und automatischen Wiedervorlagen
WORKFLOW_TEMPLATES = {
    WorkflowTyp.STANDARD: {
        "name": "Standard-Workflow",
        "beschreibung": "Allgemeiner Workflow für Verkehrsunfälle",
        "meilensteine": [
            {
                "titel": "Mandatsaufnahme",
                "beschreibung": "Aufnahme aller relevanten Daten und Dokumente",
                "tage_offset": 0,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 3}
            },
            {
                "titel": "Vollmacht eingeholt",
                "beschreibung": "Unterschriebene Vollmacht vom Mandanten",
                "tage_offset": 1,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 7}
            },
            {
                "titel": "Gutachten beauftragt",
                "beschreibung": "Gutachter wurde beauftragt",
                "tage_offset": 2,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 5}
            },
            {
                "titel": "Gutachten erhalten",
                "beschreibung": "Gutachten liegt vor",
                "tage_offset": 7,
                "wiedervorlage": None
            },
            {
                "titel": "Anspruchsschreiben versendet",
                "beschreibung": "Schadensersatzforderung an Versicherung",
                "tage_offset": 10,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 14}
            },
            {
                "titel": "Reaktion Versicherung",
                "beschreibung": "Antwort der gegnerischen Versicherung",
                "tage_offset": 24,
                "wiedervorlage": None
            },
            {
                "titel": "Regulierung erfolgt",
                "beschreibung": "Zahlungseingang geprüft",
                "tage_offset": 35,
                "wiedervorlage": None
            },
            {
                "titel": "Akte geschlossen",
                "beschreibung": "Fall abgeschlossen und archiviert",
                "tage_offset": 42,
                "wiedervorlage": None
            }
        ]
    },

    WorkflowTyp.HAFTPFLICHT_GEGNER: {
        "name": "Haftpflichtschaden (gegnerische Versicherung)",
        "beschreibung": "Workflow für Unfälle mit klarer Schuld des Unfallgegners",
        "meilensteine": [
            {
                "titel": "Mandatsaufnahme",
                "beschreibung": "Datenaufnahme und Dokumentensammlung",
                "tage_offset": 0,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 2}
            },
            {
                "titel": "Vollmacht und Abtretung",
                "beschreibung": "Vollmacht und Abtretungserklärung unterschrieben",
                "tage_offset": 1,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 5}
            },
            {
                "titel": "Deckungsanfrage Rechtsschutz",
                "beschreibung": "Deckungszusage bei Rechtsschutzversicherung angefragt",
                "tage_offset": 1,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 7}
            },
            {
                "titel": "Gutachterauftrag",
                "beschreibung": "Sachverständiger beauftragt",
                "tage_offset": 2,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 5}
            },
            {
                "titel": "Mietwagen/Nutzungsausfall geklärt",
                "beschreibung": "Ersatzmobilität organisiert",
                "tage_offset": 2,
                "wiedervorlage": None
            },
            {
                "titel": "Gutachten eingegangen",
                "beschreibung": "Vollständiges Gutachten erhalten",
                "tage_offset": 7,
                "wiedervorlage": None
            },
            {
                "titel": "Anspruchsschreiben",
                "beschreibung": "Forderung an gegnerische Versicherung",
                "tage_offset": 8,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 14}
            },
            {
                "titel": "Werkstattfreigabe",
                "beschreibung": "Reparaturfreigabe erteilt",
                "tage_offset": 10,
                "wiedervorlage": None
            },
            {
                "titel": "Regulierungszusage",
                "beschreibung": "Versicherung hat Regulierung zugesagt",
                "tage_offset": 22,
                "wiedervorlage": {"typ": WiedervorlageTyp.ZAHLUNG, "tage": 14}
            },
            {
                "titel": "Zahlungseingang",
                "beschreibung": "Zahlung vollständig eingegangen",
                "tage_offset": 36,
                "wiedervorlage": None
            },
            {
                "titel": "Abrechnung mit Mandant",
                "beschreibung": "Kostenabrechnung erstellt",
                "tage_offset": 38,
                "wiedervorlage": None
            },
            {
                "titel": "Akte geschlossen",
                "beschreibung": "Fall erfolgreich abgeschlossen",
                "tage_offset": 42,
                "wiedervorlage": None
            }
        ]
    },

    WorkflowTyp.PERSONENSCHADEN: {
        "name": "Personenschaden",
        "beschreibung": "Workflow für Unfälle mit Personenschaden",
        "meilensteine": [
            {
                "titel": "Mandatsaufnahme",
                "beschreibung": "Erstgespräch und Dokumentation",
                "tage_offset": 0,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 2}
            },
            {
                "titel": "Medizinische Unterlagen angefordert",
                "beschreibung": "Arztberichte, Krankenhaus-Entlassung etc.",
                "tage_offset": 1,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 14}
            },
            {
                "titel": "Schweigepflichtentbindung",
                "beschreibung": "Unterschriebene Entbindung erhalten",
                "tage_offset": 3,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 7}
            },
            {
                "titel": "Arbeitsunfähigkeitsbescheinigungen",
                "beschreibung": "Alle AUs gesammelt",
                "tage_offset": 7,
                "wiedervorlage": None
            },
            {
                "titel": "Verdienstausfallberechnung",
                "beschreibung": "Einkommensnachweise ausgewertet",
                "tage_offset": 14,
                "wiedervorlage": None
            },
            {
                "titel": "Medizinische Dokumentation vollständig",
                "beschreibung": "Alle Unterlagen liegen vor",
                "tage_offset": 30,
                "wiedervorlage": None
            },
            {
                "titel": "Schmerzensgeldforderung",
                "beschreibung": "Schmerzensgeld berechnet und geltend gemacht",
                "tage_offset": 35,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 21}
            },
            {
                "titel": "Verhandlung mit Versicherung",
                "beschreibung": "Erste Regulierungsverhandlung",
                "tage_offset": 56,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 14}
            },
            {
                "titel": "Einigung erzielt",
                "beschreibung": "Vergleich oder vollständige Regulierung",
                "tage_offset": 84,
                "wiedervorlage": {"typ": WiedervorlageTyp.ZAHLUNG, "tage": 21}
            },
            {
                "titel": "Abrechnung und Abschluss",
                "beschreibung": "Fall vollständig reguliert",
                "tage_offset": 105,
                "wiedervorlage": None
            }
        ]
    },

    WorkflowTyp.TOTALSCHADEN: {
        "name": "Totalschaden",
        "beschreibung": "Workflow für wirtschaftlichen oder technischen Totalschaden",
        "meilensteine": [
            {
                "titel": "Mandatsaufnahme",
                "beschreibung": "Datenaufnahme inkl. Fahrzeugdaten",
                "tage_offset": 0,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 2}
            },
            {
                "titel": "Gutachten mit Restwertermittlung",
                "beschreibung": "Gutachter beauftragt, Restwert zu ermitteln",
                "tage_offset": 1,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 5}
            },
            {
                "titel": "Gutachten eingegangen",
                "beschreibung": "Wiederbeschaffungswert und Restwert ermittelt",
                "tage_offset": 5,
                "wiedervorlage": None
            },
            {
                "titel": "Restwertangebote geprüft",
                "beschreibung": "Restwertbörse und Höchstgebot ermittelt",
                "tage_offset": 7,
                "wiedervorlage": None
            },
            {
                "titel": "Ersatzfahrzeug gesucht",
                "beschreibung": "Vergleichsangebote für Wiederbeschaffung",
                "tage_offset": 7,
                "wiedervorlage": None
            },
            {
                "titel": "Fahrzeug abgemeldet",
                "beschreibung": "Altes Fahrzeug bei Zulassungsstelle abgemeldet",
                "tage_offset": 10,
                "wiedervorlage": None
            },
            {
                "titel": "Anspruchsschreiben",
                "beschreibung": "Forderung inkl. Ab-/Anmeldekosten",
                "tage_offset": 8,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 14}
            },
            {
                "titel": "Regulierung erfolgt",
                "beschreibung": "Wiederbeschaffungswert minus Restwert erstattet",
                "tage_offset": 28,
                "wiedervorlage": None
            },
            {
                "titel": "Akte geschlossen",
                "beschreibung": "Totalschaden vollständig reguliert",
                "tage_offset": 35,
                "wiedervorlage": None
            }
        ]
    },

    WorkflowTyp.BAGATELLE: {
        "name": "Bagatellschaden",
        "beschreibung": "Schneller Workflow für kleinere Schäden (unter 1.000 EUR)",
        "meilensteine": [
            {
                "titel": "Mandatsaufnahme",
                "beschreibung": "Schnellaufnahme mit Fotos",
                "tage_offset": 0,
                "wiedervorlage": None
            },
            {
                "titel": "Kostenvoranschlag eingeholt",
                "beschreibung": "KVA statt Gutachten",
                "tage_offset": 2,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 3}
            },
            {
                "titel": "Schadenmeldung an Versicherung",
                "beschreibung": "Direktmeldung mit KVA",
                "tage_offset": 3,
                "wiedervorlage": {"typ": WiedervorlageTyp.FRIST, "tage": 10}
            },
            {
                "titel": "Regulierung erfolgt",
                "beschreibung": "Zahlung eingegangen",
                "tage_offset": 14,
                "wiedervorlage": None
            },
            {
                "titel": "Akte geschlossen",
                "beschreibung": "Bagatellschaden abgeschlossen",
                "tage_offset": 16,
                "wiedervorlage": None
            }
        ]
    },

    WorkflowTyp.KASKO: {
        "name": "Kaskoschaden",
        "beschreibung": "Workflow für Schäden über eigene Kaskoversicherung",
        "meilensteine": [
            {
                "titel": "Mandatsaufnahme",
                "beschreibung": "Prüfung der Versicherungsbedingungen",
                "tage_offset": 0,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 2}
            },
            {
                "titel": "Schadenmeldung an eigene Versicherung",
                "beschreibung": "Formular ausgefüllt und eingereicht",
                "tage_offset": 1,
                "wiedervorlage": {"typ": WiedervorlageTyp.NACHFASSEN, "tage": 5}
            },
            {
                "titel": "Besichtigung durch Versicherung",
                "beschreibung": "Termin mit Versicherungsgutachter",
                "tage_offset": 5,
                "wiedervorlage": None
            },
            {
                "titel": "Selbstbeteiligung geklärt",
                "beschreibung": "Höhe der SB festgestellt",
                "tage_offset": 7,
                "wiedervorlage": None
            },
            {
                "titel": "Reparaturfreigabe",
                "beschreibung": "Versicherung gibt Reparatur frei",
                "tage_offset": 10,
                "wiedervorlage": None
            },
            {
                "titel": "Reparatur durchgeführt",
                "beschreibung": "Fahrzeug repariert",
                "tage_offset": 17,
                "wiedervorlage": None
            },
            {
                "titel": "Abrechnung erfolgt",
                "beschreibung": "Werkstatt direkt abgerechnet",
                "tage_offset": 21,
                "wiedervorlage": None
            },
            {
                "titel": "Akte geschlossen",
                "beschreibung": "Kaskoschaden abgeschlossen",
                "tage_offset": 25,
                "wiedervorlage": None
            }
        ]
    }
}


class WorkflowService:
    """Service für Workflow-Management"""

    def __init__(self, db: Session):
        self.db = db

    def get_verfuegbare_workflows(self) -> Dict:
        """Gibt alle verfügbaren Workflow-Templates zurück"""
        return {
            typ.value: {
                "name": template["name"],
                "beschreibung": template["beschreibung"],
                "anzahl_meilensteine": len(template["meilensteine"])
            }
            for typ, template in WORKFLOW_TEMPLATES.items()
        }

    def workflow_anwenden(
        self,
        projekt_id: int,
        workflow_typ: WorkflowTyp,
        start_datum: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> Tuple[bool, str, List[TimelineMeilenstein]]:
        """
        Wendet einen Workflow auf ein Projekt an.

        Args:
            projekt_id: ID des Projekts
            workflow_typ: Typ des Workflows
            start_datum: Startdatum (Standard: heute)
            user_id: ID des anwendenden Benutzers

        Returns:
            Tuple (Erfolg, Nachricht, Liste der erstellten Meilensteine)
        """
        if workflow_typ not in WORKFLOW_TEMPLATES:
            return False, f"Unbekannter Workflow-Typ: {workflow_typ}", []

        projekt = self.db.query(UnfallProjekt).filter(
            UnfallProjekt.id == projekt_id
        ).first()

        if not projekt:
            return False, "Projekt nicht gefunden", []

        template = WORKFLOW_TEMPLATES[workflow_typ]
        start = start_datum or datetime.now()

        erstellte_meilensteine = []

        for i, ms_template in enumerate(template["meilensteine"]):
            # Meilenstein erstellen
            faellig_am = start + timedelta(days=ms_template["tage_offset"])

            meilenstein = TimelineMeilenstein(
                unfallprojekt_id=projekt_id,
                titel=ms_template["titel"],
                beschreibung=ms_template["beschreibung"],
                status=MeilensteinStatus.AUSSTEHEND,
                faellig_am=faellig_am,
                reihenfolge=i
            )

            self.db.add(meilenstein)
            self.db.flush()

            erstellte_meilensteine.append(meilenstein)

            # Wiedervorlage erstellen falls definiert
            wv_config = ms_template.get("wiedervorlage")
            if wv_config and user_id:
                wv_datum = faellig_am + timedelta(days=wv_config["tage"])

                wiedervorlage = Wiedervorlage(
                    unfallprojekt_id=projekt_id,
                    erstellt_von_user_id=user_id,
                    zugewiesen_an_user_id=user_id,
                    typ=wv_config["typ"],
                    prioritaet=WiedervorlagePrioritaet.NORMAL,
                    titel=f"WV: {ms_template['titel']}",
                    beschreibung=f"Automatische Wiedervorlage für Meilenstein: {ms_template['titel']}",
                    faellig_am=wv_datum
                )

                self.db.add(wiedervorlage)

        self.db.flush()

        return True, f"Workflow '{template['name']}' mit {len(erstellte_meilensteine)} Meilensteinen angewendet", erstellte_meilensteine

    def workflow_fortschritt(self, projekt_id: int) -> Dict:
        """
        Berechnet den Fortschritt eines Projekts.

        Args:
            projekt_id: ID des Projekts

        Returns:
            Dictionary mit Fortschrittsinformationen
        """
        meilensteine = self.db.query(TimelineMeilenstein).filter(
            TimelineMeilenstein.unfallprojekt_id == projekt_id
        ).all()

        if not meilensteine:
            return {"gesamt": 0, "erledigt": 0, "prozent": 0, "naechster": None}

        gesamt = len(meilensteine)
        erledigt = len([m for m in meilensteine if m.status == MeilensteinStatus.ERLEDIGT])
        in_bearbeitung = [m for m in meilensteine if m.status == MeilensteinStatus.IN_BEARBEITUNG]
        ausstehend = [m for m in meilensteine if m.status == MeilensteinStatus.AUSSTEHEND]

        # Nächster Meilenstein
        naechster = None
        if in_bearbeitung:
            naechster = in_bearbeitung[0]
        elif ausstehend:
            naechster = sorted(ausstehend, key=lambda x: x.reihenfolge)[0]

        return {
            "gesamt": gesamt,
            "erledigt": erledigt,
            "in_bearbeitung": len(in_bearbeitung),
            "ausstehend": len(ausstehend),
            "prozent": round(erledigt / gesamt * 100) if gesamt > 0 else 0,
            "naechster": naechster
        }

    def meilenstein_abschliessen(
        self,
        meilenstein_id: int,
        user_id: int
    ) -> Tuple[bool, str]:
        """
        Schließt einen Meilenstein ab und aktiviert den nächsten.

        Args:
            meilenstein_id: ID des Meilensteins
            user_id: ID des abschließenden Benutzers

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        meilenstein = self.db.query(TimelineMeilenstein).filter(
            TimelineMeilenstein.id == meilenstein_id
        ).first()

        if not meilenstein:
            return False, "Meilenstein nicht gefunden"

        # Meilenstein als erledigt markieren
        meilenstein.status = MeilensteinStatus.ERLEDIGT
        meilenstein.erledigt_am = datetime.now()
        meilenstein.erledigt_von_user_id = user_id

        # Nächsten Meilenstein aktivieren
        naechster = self.db.query(TimelineMeilenstein).filter(
            TimelineMeilenstein.unfallprojekt_id == meilenstein.unfallprojekt_id,
            TimelineMeilenstein.reihenfolge == meilenstein.reihenfolge + 1
        ).first()

        if naechster:
            naechster.status = MeilensteinStatus.IN_BEARBEITUNG

        self.db.flush()

        return True, f"Meilenstein '{meilenstein.titel}' abgeschlossen"


def get_workflow_service(db: Session) -> WorkflowService:
    """Factory-Funktion für den Workflow-Service"""
    return WorkflowService(db)
