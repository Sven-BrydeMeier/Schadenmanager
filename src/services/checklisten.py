"""
Checklisten für verschiedene Schadenstypen
"""
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.models.checkliste import ChecklistenItem


# Vordefinierte Checklisten für verschiedene Schadenstypen
CHECKLISTEN = {
    "auffahrunfall": {
        "name": "Auffahrunfall",
        "beschreibung": "Checkliste für klassische Auffahrunfälle",
        "kategorien": {
            "sofortmassnahmen": {
                "name": "Sofortmaßnahmen am Unfallort",
                "items": [
                    {"titel": "Unfallstelle absichern (Warndreieck)", "beschreibung": "Warndreieck in ausreichendem Abstand aufstellen"},
                    {"titel": "Verletzte versorgen / Rettungsdienst rufen", "beschreibung": "Bei Verletzungen sofort 112 anrufen"},
                    {"titel": "Polizei rufen (bei Personenschaden/größerem Sachschaden)", "beschreibung": "Bei Personenschäden immer die Polizei hinzuziehen"},
                    {"titel": "Unfallgegner-Daten aufnehmen", "beschreibung": "Name, Adresse, Kennzeichen, Versicherung"},
                    {"titel": "Fotos der Unfallstelle machen", "beschreibung": "Übersichts- und Detailfotos aus verschiedenen Winkeln"},
                    {"titel": "Fotos der Fahrzeugschäden machen", "beschreibung": "Alle Schäden an beiden Fahrzeugen dokumentieren"},
                    {"titel": "Zeugen notieren", "beschreibung": "Namen und Kontaktdaten von Zeugen aufnehmen"},
                ],
            },
            "dokumentation": {
                "name": "Dokumentation & Unterlagen",
                "items": [
                    {"titel": "Fahrzeugschein kopieren/fotografieren", "beschreibung": "Für die Schadenmeldung benötigt"},
                    {"titel": "Personalausweis kopieren", "beschreibung": "Zur Identifikation"},
                    {"titel": "Unfallbericht ausfüllen", "beschreibung": "Europäischer Unfallbericht oder eigene Dokumentation"},
                    {"titel": "Polizeiliche Unfallaufnahme anfordern", "beschreibung": "Falls Polizei vor Ort war"},
                ],
            },
            "schadensabwicklung": {
                "name": "Schadensabwicklung",
                "items": [
                    {"titel": "Gutachter beauftragen", "beschreibung": "Bei Schäden über 750€ einen unabhängigen Gutachter beauftragen"},
                    {"titel": "Rechtsanwalt beauftragen", "beschreibung": "Zur Durchsetzung der Ansprüche"},
                    {"titel": "Vollmacht unterschreiben", "beschreibung": "Vollmacht für den Rechtsanwalt"},
                    {"titel": "Schadensmeldung an eigene Versicherung", "beschreibung": "Innerhalb einer Woche"},
                    {"titel": "Werkstatt-Termin vereinbaren", "beschreibung": "Reparatur oder Kostenvoranschlag"},
                    {"titel": "Ersatzwagen organisieren", "beschreibung": "Falls Fahrzeug nicht fahrbereit"},
                ],
            },
            "ansprueche": {
                "name": "Ansprüche prüfen",
                "items": [
                    {"titel": "Reparaturkosten/Wiederbeschaffungswert", "beschreibung": "Aus Gutachten"},
                    {"titel": "Merkantiler Minderwert", "beschreibung": "Bei repariertem Fahrzeug"},
                    {"titel": "Nutzungsausfall/Mietwagen", "beschreibung": "Für die Ausfallzeit"},
                    {"titel": "Ab-/Anmeldekosten", "beschreibung": "Bei Totalschaden"},
                    {"titel": "Kostenpauschale (25€)", "beschreibung": "Für Telefon, Porto etc."},
                    {"titel": "Schmerzensgeld prüfen", "beschreibung": "Bei Verletzungen"},
                    {"titel": "Verdienstausfall prüfen", "beschreibung": "Bei Arbeitsunfähigkeit"},
                ],
            },
        },
    },
    "parkschaden": {
        "name": "Parkschaden / Parkrempler",
        "beschreibung": "Checkliste für Parkschäden und Parkrempler",
        "kategorien": {
            "sofortmassnahmen": {
                "name": "Sofortmaßnahmen",
                "items": [
                    {"titel": "Unfallgegner ermitteln", "beschreibung": "Falls vorhanden - Kennzeichen, Kontaktdaten"},
                    {"titel": "Bei Fahrerflucht: Polizei rufen", "beschreibung": "Unerlaubtes Entfernen vom Unfallort anzeigen"},
                    {"titel": "Fotos vom Schaden machen", "beschreibung": "Detaillierte Dokumentation"},
                    {"titel": "Zeugen suchen", "beschreibung": "Anwohner, Passanten befragen"},
                    {"titel": "Überwachungskameras prüfen", "beschreibung": "Geschäfte, Parkhaus nach Aufnahmen fragen"},
                ],
            },
            "dokumentation": {
                "name": "Dokumentation",
                "items": [
                    {"titel": "Schaden dokumentieren", "beschreibung": "Fotos mit Maßstab/Referenz"},
                    {"titel": "Ort und Zeit notieren", "beschreibung": "Genaue Angaben für Anzeige"},
                    {"titel": "Anzeige bei Polizei erstatten", "beschreibung": "Bei Fahrerflucht"},
                ],
            },
            "schadensabwicklung": {
                "name": "Schadensabwicklung",
                "items": [
                    {"titel": "Kostenvoranschlag einholen", "beschreibung": "Bei kleineren Schäden ausreichend"},
                    {"titel": "Gegnerische Versicherung kontaktieren", "beschreibung": "Falls Verursacher bekannt"},
                    {"titel": "Eigene Vollkasko prüfen", "beschreibung": "Falls Verursacher unbekannt - Selbstbeteiligung beachten"},
                ],
            },
        },
    },
    "wildunfall": {
        "name": "Wildunfall",
        "beschreibung": "Checkliste für Unfälle mit Wildtieren",
        "kategorien": {
            "sofortmassnahmen": {
                "name": "Sofortmaßnahmen",
                "items": [
                    {"titel": "Unfallstelle absichern", "beschreibung": "Warnblinklicht, Warndreieck"},
                    {"titel": "Polizei rufen", "beschreibung": "Immer die Polizei informieren"},
                    {"titel": "Tier nicht anfassen", "beschreibung": "Verletztes Wild kann gefährlich sein"},
                    {"titel": "Tier nicht von der Straße ziehen", "beschreibung": "Nur Polizei/Jäger dürfen das"},
                    {"titel": "Wildunfallbescheinigung anfordern", "beschreibung": "Von Polizei oder Jäger ausstellen lassen"},
                ],
            },
            "dokumentation": {
                "name": "Dokumentation",
                "items": [
                    {"titel": "Fotos vom Schaden machen", "beschreibung": "Fahrzeugschäden dokumentieren"},
                    {"titel": "Fotos vom Tier (falls vor Ort)", "beschreibung": "Zur Dokumentation"},
                    {"titel": "Unfallort dokumentieren", "beschreibung": "Straße, Wildwechsel-Schilder"},
                    {"titel": "Wildunfallbescheinigung aufbewahren", "beschreibung": "Wichtig für Versicherung"},
                ],
            },
            "versicherung": {
                "name": "Versicherung",
                "items": [
                    {"titel": "Teilkasko prüfen", "beschreibung": "Wildschäden sind i.d.R. über Teilkasko versichert"},
                    {"titel": "Schaden melden", "beschreibung": "Mit Wildunfallbescheinigung"},
                    {"titel": "Erweiterter Wildschadenschutz prüfen", "beschreibung": "Manche Versicherungen decken alle Tiere ab"},
                ],
            },
        },
    },
    "personenschaden": {
        "name": "Unfall mit Personenschaden",
        "beschreibung": "Checkliste bei Verletzungen durch Verkehrsunfall",
        "kategorien": {
            "sofortmassnahmen": {
                "name": "Sofortmaßnahmen",
                "items": [
                    {"titel": "Rettungsdienst rufen (112)", "beschreibung": "Sofort bei Verletzungen"},
                    {"titel": "Erste Hilfe leisten", "beschreibung": "Nach bestem Wissen und Gewissen"},
                    {"titel": "Polizei hinzuziehen", "beschreibung": "Bei Personenschäden obligatorisch"},
                    {"titel": "Zum Arzt/Krankenhaus gehen", "beschreibung": "Auch bei vermeintlich leichten Verletzungen"},
                ],
            },
            "medizinisch": {
                "name": "Medizinische Dokumentation",
                "items": [
                    {"titel": "Erstbefund dokumentieren lassen", "beschreibung": "Wichtig für spätere Ansprüche"},
                    {"titel": "Alle Arztbesuche dokumentieren", "beschreibung": "Termine, Diagnosen, Behandlungen"},
                    {"titel": "Arbeitsunfähigkeitsbescheinigungen sammeln", "beschreibung": "Für Verdienstausfall"},
                    {"titel": "Atteste/Gutachten anfordern", "beschreibung": "Für Schmerzensgeld-Berechnung"},
                    {"titel": "Schweigepflichtentbindung unterschreiben", "beschreibung": "Für den Anwalt"},
                ],
            },
            "ansprueche": {
                "name": "Ansprüche bei Personenschaden",
                "items": [
                    {"titel": "Schmerzensgeld berechnen", "beschreibung": "Nach Art und Dauer der Verletzung"},
                    {"titel": "Verdienstausfall dokumentieren", "beschreibung": "Einkommensnachweise sammeln"},
                    {"titel": "Heilungskosten erfassen", "beschreibung": "Zuzahlungen, Fahrtkosten zum Arzt"},
                    {"titel": "Haushaltsführungsschaden prüfen", "beschreibung": "Bei Einschränkungen im Haushalt"},
                    {"titel": "Pflegekosten prüfen", "beschreibung": "Bei Pflegebedürftigkeit"},
                    {"titel": "Dauerfolgen dokumentieren", "beschreibung": "Für erhöhtes Schmerzensgeld"},
                ],
            },
        },
    },
    "totalschaden": {
        "name": "Totalschaden",
        "beschreibung": "Checkliste bei wirtschaftlichem oder technischem Totalschaden",
        "kategorien": {
            "feststellung": {
                "name": "Totalschaden-Feststellung",
                "items": [
                    {"titel": "Gutachten prüfen", "beschreibung": "Wirtschaftlicher vs. technischer Totalschaden"},
                    {"titel": "Wiederbeschaffungswert prüfen", "beschreibung": "Vergleichsangebote einholen"},
                    {"titel": "Restwert prüfen", "beschreibung": "Restwertbörse nutzen"},
                    {"titel": "130%-Regelung prüfen", "beschreibung": "Bei sentimentalem Wert oder Spezialfahrzeug"},
                ],
            },
            "abwicklung": {
                "name": "Abwicklung",
                "items": [
                    {"titel": "Fahrzeug abmelden", "beschreibung": "Bei Zulassungsstelle"},
                    {"titel": "Versicherung informieren", "beschreibung": "Eigene KFZ-Versicherung"},
                    {"titel": "Restwert-Angebote vergleichen", "beschreibung": "Nicht das erste Angebot annehmen"},
                    {"titel": "Ersatzfahrzeug suchen", "beschreibung": "Wiederbeschaffungsdauer beachten"},
                ],
            },
            "ansprueche": {
                "name": "Ansprüche bei Totalschaden",
                "items": [
                    {"titel": "Wiederbeschaffungswert geltend machen", "beschreibung": "Abzüglich Restwert"},
                    {"titel": "Ab-/Anmeldekosten", "beschreibung": "Ca. 50-100€"},
                    {"titel": "Nutzungsausfall (max. 14 Tage)", "beschreibung": "Für Wiederbeschaffungsdauer"},
                    {"titel": "Kostenpauschale", "beschreibung": "25€"},
                    {"titel": "Standgebühren prüfen", "beschreibung": "Falls Fahrzeug abgeschleppt wurde"},
                ],
            },
        },
    },
}


class ChecklistenService:
    """Service für Checklisten-Verwaltung"""

    def __init__(self, db: Session):
        self.db = db

    def get_verfuegbare_checklisten(self) -> Dict:
        """Gibt alle verfügbaren Checklistentypen zurück"""
        return {
            key: {"name": value["name"], "beschreibung": value["beschreibung"]}
            for key, value in CHECKLISTEN.items()
        }

    def initialisiere_checkliste(self, projekt_id: int, checklisten_typ: str) -> List[ChecklistenItem]:
        """
        Initialisiert eine Checkliste für ein Projekt.

        Args:
            projekt_id: ID des Projekts
            checklisten_typ: Typ der Checkliste

        Returns:
            Liste der erstellten ChecklistenItems
        """
        if checklisten_typ not in CHECKLISTEN:
            raise ValueError(f"Unbekannter Checklistentyp: {checklisten_typ}")

        checkliste = CHECKLISTEN[checklisten_typ]
        items = []
        reihenfolge = 0

        for kat_key, kategorie in checkliste["kategorien"].items():
            for item in kategorie["items"]:
                cl_item = ChecklistenItem(
                    unfallprojekt_id=projekt_id,
                    checkliste_typ=checklisten_typ,
                    kategorie=kategorie["name"],
                    titel=item["titel"],
                    beschreibung=item.get("beschreibung", ""),
                    reihenfolge=reihenfolge,
                )
                self.db.add(cl_item)
                items.append(cl_item)
                reihenfolge += 1

        self.db.flush()
        return items

    def get_checkliste(self, projekt_id: int) -> Dict[str, List[ChecklistenItem]]:
        """
        Holt die Checkliste für ein Projekt, gruppiert nach Kategorie.

        Args:
            projekt_id: ID des Projekts

        Returns:
            Dictionary mit Kategorien und zugehörigen Items
        """
        items = self.db.query(ChecklistenItem).filter(
            ChecklistenItem.unfallprojekt_id == projekt_id
        ).order_by(ChecklistenItem.reihenfolge).all()

        kategorien = {}
        for item in items:
            if item.kategorie not in kategorien:
                kategorien[item.kategorie] = []
            kategorien[item.kategorie].append(item)

        return kategorien

    def item_erledigen(self, item_id: int, user_id: int, notiz: Optional[str] = None) -> ChecklistenItem:
        """Markiert ein Item als erledigt"""
        item = self.db.query(ChecklistenItem).filter(ChecklistenItem.id == item_id).first()
        if item:
            item.erledigt = True
            item.erledigt_am = datetime.now()
            item.erledigt_von_user_id = user_id
            if notiz:
                item.notiz = notiz
            self.db.flush()
        return item

    def get_fortschritt(self, projekt_id: int) -> Dict:
        """Berechnet den Fortschritt einer Checkliste"""
        items = self.db.query(ChecklistenItem).filter(
            ChecklistenItem.unfallprojekt_id == projekt_id
        ).all()

        if not items:
            return {"gesamt": 0, "erledigt": 0, "prozent": 0}

        gesamt = len(items)
        erledigt = len([i for i in items if i.erledigt])

        return {
            "gesamt": gesamt,
            "erledigt": erledigt,
            "prozent": round(erledigt / gesamt * 100) if gesamt > 0 else 0
        }


def get_checklisten_service(db: Session) -> ChecklistenService:
    """Factory-Funktion für den Checklisten-Service"""
    return ChecklistenService(db)
