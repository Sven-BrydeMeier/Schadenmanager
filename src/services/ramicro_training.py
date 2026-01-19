"""
RA-Micro Parser Training-System
Speichert Korrekturbeispiele und lernt daraus für zukünftige Importe
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class TrainingBeispiel:
    """Ein Trainingsbeispiel für den Parser"""
    id: str
    erstellt_am: datetime
    aktenvorblatt_text: str  # Der Quelltext

    # Extrahierte/korrigierte Daten
    mandant: Dict[str, Any] = field(default_factory=dict)
    gegner: Dict[str, Any] = field(default_factory=dict)
    versicherung_gegner: Dict[str, Any] = field(default_factory=dict)
    versicherung_eigen: Dict[str, Any] = field(default_factory=dict)
    rechtsschutz: Dict[str, Any] = field(default_factory=dict)
    gutachter: Dict[str, Any] = field(default_factory=dict)

    # Metadaten
    aktenzeichen: Optional[str] = None
    kurzbezeichnung: Optional[str] = None

    # Markierungen wo im Text die Daten gefunden wurden
    text_positionen: Dict[str, Dict[str, tuple]] = field(default_factory=dict)

    # War es eine Korrektur vom Benutzer?
    ist_korrektur: bool = False
    original_extraktion: Optional[Dict[str, Any]] = None


class RAMicroTrainingManager:
    """Verwaltet Trainingsbeispiele für den RA-Micro Parser"""

    def __init__(self, training_dir: str = "data/ramicro_training"):
        self.training_dir = Path(training_dir)
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self._beispiele: List[TrainingBeispiel] = []
        self._load_beispiele()

    def _load_beispiele(self):
        """Lädt alle gespeicherten Trainingsbeispiele"""
        self._beispiele = []
        training_file = self.training_dir / "training_data.json"

        if training_file.exists():
            try:
                with open(training_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("beispiele", []):
                        item["erstellt_am"] = datetime.fromisoformat(item["erstellt_am"])
                        self._beispiele.append(TrainingBeispiel(**item))
            except Exception as e:
                print(f"Fehler beim Laden der Trainingsbeispiele: {e}")

    def _save_beispiele(self):
        """Speichert alle Trainingsbeispiele"""
        training_file = self.training_dir / "training_data.json"

        data = {
            "version": "1.0",
            "beispiele": []
        }

        for b in self._beispiele:
            item = asdict(b)
            item["erstellt_am"] = b.erstellt_am.isoformat()
            data["beispiele"].append(item)

        with open(training_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def speichere_beispiel(self, beispiel: TrainingBeispiel) -> str:
        """Speichert ein neues Trainingsbeispiel"""
        if not beispiel.id:
            beispiel.id = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Prüfe ob bereits ein Beispiel mit ähnlichem Text existiert
        for i, existing in enumerate(self._beispiele):
            if self._text_similarity(existing.aktenvorblatt_text, beispiel.aktenvorblatt_text) > 0.9:
                # Update existierendes Beispiel
                self._beispiele[i] = beispiel
                self._save_beispiele()
                return beispiel.id

        self._beispiele.append(beispiel)
        self._save_beispiele()
        return beispiel.id

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Berechnet Ähnlichkeit zwischen zwei Texten (einfache Implementierung)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def finde_aehnliches_beispiel(self, text: str) -> Optional[TrainingBeispiel]:
        """Findet ein ähnliches Trainingsbeispiel für den gegebenen Text"""
        beste_similarity = 0.0
        bestes_beispiel = None

        for beispiel in self._beispiele:
            similarity = self._text_similarity(text, beispiel.aktenvorblatt_text)
            if similarity > beste_similarity and similarity > 0.5:
                beste_similarity = similarity
                bestes_beispiel = beispiel

        return bestes_beispiel

    def get_alle_beispiele(self) -> List[TrainingBeispiel]:
        """Gibt alle Trainingsbeispiele zurück"""
        return self._beispiele.copy()

    def loesche_beispiel(self, beispiel_id: str) -> bool:
        """Löscht ein Trainingsbeispiel"""
        for i, b in enumerate(self._beispiele):
            if b.id == beispiel_id:
                del self._beispiele[i]
                self._save_beispiele()
                return True
        return False

    def extrahiere_muster(self) -> Dict[str, List[str]]:
        """
        Extrahiert Muster aus den Trainingsbeispielen.
        Gibt zurück: Labels/Marker die vor bestimmten Datentypen stehen
        """
        muster = {
            "mandant_vor": [],
            "mandant_nach": [],
            "gegner_vor": [],
            "gegner_nach": [],
            "versicherung_vor": [],
            "versicherung_nach": [],
        }

        for beispiel in self._beispiele:
            if beispiel.text_positionen:
                # Analysiere Textpositionen um Muster zu finden
                for feld, positionen in beispiel.text_positionen.items():
                    # TODO: Implementiere Musterextraktion
                    pass

        return muster


# Singleton-Instanz
_training_manager: Optional[RAMicroTrainingManager] = None


def get_training_manager() -> RAMicroTrainingManager:
    """Gibt die Training-Manager-Instanz zurück"""
    global _training_manager
    if _training_manager is None:
        _training_manager = RAMicroTrainingManager()
    return _training_manager
