"""
Meilenstein-Engine: Berechnet den Status von Timeline-Meilensteinen
basierend auf der Konfigurationsdatei.
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, TimelineMeilenstein, MeilensteinStatus,
    Dokument, DokumentTyp, KostenPosition, KostenKategorie, KostenAmpel,
    Korrespondenz, KorrespondenzRichtung, User
)


class MeilensteinEngine:
    """Engine zur Berechnung und Aktualisierung von Meilenstein-Status"""

    def __init__(self, config_path: str = None):
        """
        Initialisiert die Engine mit der Konfigurationsdatei.

        Args:
            config_path: Pfad zur meilensteine.json Datei
        """
        if config_path is None:
            # Standard-Pfad relativ zum Projektverzeichnis
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, "config", "meilensteine.json")

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Lädt die Meilenstein-Konfiguration aus der JSON-Datei"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Meilenstein-Konfiguration nicht gefunden: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Fehler beim Parsen der Konfiguration: {e}")

    def get_meilenstein_definitionen(self) -> List[Dict]:
        """Gibt alle Meilenstein-Definitionen zurück"""
        return self.config.get("meilensteine", [])

    def initialisiere_meilensteine(self, db: Session, projekt: UnfallProjekt) -> List[TimelineMeilenstein]:
        """
        Erstellt alle Meilensteine für ein neues Projekt basierend auf der Konfiguration.

        Args:
            db: Datenbank-Session
            projekt: Das Unfallprojekt

        Returns:
            Liste der erstellten Meilensteine
        """
        meilensteine = []

        for definition in self.get_meilenstein_definitionen():
            meilenstein = TimelineMeilenstein(
                unfallprojekt_id=projekt.id,
                code=definition["code"],
                beschreibung=definition["beschreibung"],
                reihenfolge=definition["reihenfolge"],
                partei_zustaendig=",".join(definition.get("partei_zustaendig", [])),
                status=MeilensteinStatus.ROT,
                automatisch_berechnet="JA"
            )
            db.add(meilenstein)
            meilensteine.append(meilenstein)

        db.flush()
        return meilensteine

    def berechne_status(self, db: Session, projekt: UnfallProjekt) -> Dict[str, MeilensteinStatus]:
        """
        Berechnet den Status aller Meilensteine für ein Projekt.

        Args:
            db: Datenbank-Session
            projekt: Das Unfallprojekt

        Returns:
            Dictionary mit Meilenstein-Code -> Status
        """
        ergebnisse = {}
        kontext = self._sammle_kontext(db, projekt)

        for definition in self.get_meilenstein_definitionen():
            code = definition["code"]
            regeln = definition.get("regeln", {})

            # Prüfe Regeln in Reihenfolge: grün -> orange -> rot
            if self._pruefe_bedingung(regeln.get("gruen", {}), kontext):
                ergebnisse[code] = MeilensteinStatus.GRUEN
            elif self._pruefe_bedingung(regeln.get("orange", {}), kontext):
                ergebnisse[code] = MeilensteinStatus.ORANGE
            else:
                ergebnisse[code] = MeilensteinStatus.ROT

        return ergebnisse

    def aktualisiere_meilensteine(self, db: Session, projekt: UnfallProjekt) -> None:
        """
        Aktualisiert alle Meilensteine eines Projekts basierend auf den berechneten Status.

        Args:
            db: Datenbank-Session
            projekt: Das Unfallprojekt
        """
        status_map = self.berechne_status(db, projekt)

        for meilenstein in projekt.timeline_meilensteine:
            if meilenstein.automatisch_berechnet == "JA":
                neuer_status = status_map.get(meilenstein.code)
                if neuer_status and meilenstein.status != neuer_status:
                    alter_status = meilenstein.status
                    meilenstein.status = neuer_status
                    meilenstein.aktualisiert_am = datetime.utcnow()

                    # Setze erledigt_am wenn Status auf GRÜN wechselt
                    if neuer_status == MeilensteinStatus.GRUEN and alter_status != MeilensteinStatus.GRUEN:
                        meilenstein.erledigt_am = datetime.utcnow()

        db.flush()

    def _sammle_kontext(self, db: Session, projekt: UnfallProjekt) -> Dict[str, Any]:
        """
        Sammelt alle relevanten Daten für die Regelauswertung.

        Args:
            db: Datenbank-Session
            projekt: Das Unfallprojekt

        Returns:
            Dictionary mit allen Kontextdaten
        """
        # Dokumente nach Typ gruppieren
        dokumente_nach_typ = {}
        for dok in projekt.dokumente:
            typ = dok.dokument_typ.value if dok.dokument_typ else "SONSTIG"
            if typ not in dokumente_nach_typ:
                dokumente_nach_typ[typ] = []
            dokumente_nach_typ[typ].append(dok)

        # Kostenpositionen nach Kategorie gruppieren
        kosten_nach_kategorie = {}
        for kp in projekt.kostenpositionen:
            kat = kp.kategorie.value if kp.kategorie else "SONSTIG"
            if kat not in kosten_nach_kategorie:
                kosten_nach_kategorie[kat] = []
            kosten_nach_kategorie[kat].append(kp)

        # Korrespondenz nach Richtung gruppieren
        korrespondenz_nach_richtung = {}
        for korr in projekt.korrespondenzen:
            richtung = korr.richtung.value if korr.richtung else "SONSTIG"
            if richtung not in korrespondenz_nach_richtung:
                korrespondenz_nach_richtung[richtung] = []
            korrespondenz_nach_richtung[richtung].append(korr)

        # Unfallopfer-User laden falls vorhanden
        unfallopfer = None
        if projekt.unfallopfer_user_id:
            unfallopfer = db.query(User).filter(User.id == projekt.unfallopfer_user_id).first()

        return {
            "projekt": projekt,
            "dokumente": projekt.dokumente,
            "dokumente_nach_typ": dokumente_nach_typ,
            "kostenpositionen": projekt.kostenpositionen,
            "kosten_nach_kategorie": kosten_nach_kategorie,
            "korrespondenzen": projekt.korrespondenzen,
            "korrespondenz_nach_richtung": korrespondenz_nach_richtung,
            "unfallopfer": unfallopfer,
            "alle_kosten_gruen": all(
                kp.status_ampel == KostenAmpel.GRUEN
                for kp in projekt.kostenpositionen
            ) if projekt.kostenpositionen else False,
            "hat_kosten_gruen": any(
                kp.status_ampel == KostenAmpel.GRUEN
                for kp in projekt.kostenpositionen
            ) if projekt.kostenpositionen else False,
        }

    def _pruefe_bedingung(self, regel: Dict, kontext: Dict[str, Any]) -> bool:
        """
        Prüft ob eine Regel-Bedingung erfüllt ist.

        Diese Methode implementiert eine vereinfachte Regelauswertung.
        Komplexere Bedingungen werden über spezifische Prüfmethoden abgebildet.

        Args:
            regel: Die Regel mit Bedingung
            kontext: Der Kontext mit allen Daten

        Returns:
            True wenn die Bedingung erfüllt ist
        """
        bedingung = regel.get("bedingung", "")

        if not bedingung or bedingung == "DEFAULT" or bedingung == "FALSE":
            return False

        projekt = kontext["projekt"]

        # Basisdaten-Prüfungen
        if "projekt.kfz_eigen_id IS NOT NULL AND projekt.datum_unfall IS NOT NULL" in bedingung:
            return projekt.kfz_eigen_id is not None and projekt.datum_unfall is not None

        if "projekt.kfz_eigen_id IS NOT NULL OR projekt.datum_unfall IS NOT NULL" in bedingung:
            return projekt.kfz_eigen_id is not None or projekt.datum_unfall is not None

        # Unfallopfer-Prüfungen
        if "projekt.unfallopfer_user_id IS NOT NULL AND user.zwei_faktor_aktiviert = TRUE" in bedingung:
            unfallopfer = kontext.get("unfallopfer")
            return projekt.unfallopfer_user_id is not None and unfallopfer and unfallopfer.zwei_faktor_aktiviert

        if "projekt.unfallopfer_user_id IS NOT NULL" in bedingung:
            return projekt.unfallopfer_user_id is not None

        # Gutachter-Prüfungen
        if "projekt.gutachter_user_id IS NOT NULL" in bedingung:
            return projekt.gutachter_user_id is not None

        # Ersatzwagen-Prüfungen
        if "projekt.ersatzwagenanbieter_id IS NOT NULL AND kostenposition.kategorie = 'ERSATZWAGEN'" in bedingung:
            return (
                projekt.ersatzwagenanbieter_id is not None and
                "ERSATZWAGEN" in kontext["kosten_nach_kategorie"]
            )

        if "projekt.ersatzwagenanbieter_id IS NOT NULL" in bedingung:
            return projekt.ersatzwagenanbieter_id is not None

        # Dokument-Prüfungen
        if "dokument.typ = 'FAHRZEUGSCHEIN'" in bedingung:
            fahrzeugscheine = kontext["dokumente_nach_typ"].get("FAHRZEUGSCHEIN", [])
            if not fahrzeugscheine:
                return False
            if "ki_verarbeitet = TRUE" in bedingung:
                return any(d.ki_verarbeitet for d in fahrzeugscheine)
            if "ocr_verarbeitet = TRUE" in bedingung:
                return any(d.ocr_verarbeitet for d in fahrzeugscheine)
            return True

        if "dokument.typ = 'GUTACHTEN'" in bedingung:
            gutachten = kontext["dokumente_nach_typ"].get("GUTACHTEN", [])
            if not gutachten:
                return False
            if "status = 'VERARBEITET'" in bedingung:
                return any(d.status == "VERARBEITET" for d in gutachten)
            return True

        if "dokument.typ = 'RECHNUNG'" in bedingung:
            rechnungen = kontext["dokumente_nach_typ"].get("RECHNUNG", [])
            if not rechnungen:
                return False
            if "Reparatur" in bedingung:
                return any(d.beschreibung and "Reparatur" in d.beschreibung for d in rechnungen)
            return True

        # Kosten-Prüfungen
        if "kostenposition.kategorie = 'ERSATZWAGEN'" in bedingung:
            ersatzwagen = kontext["kosten_nach_kategorie"].get("ERSATZWAGEN", [])
            if not ersatzwagen:
                return False
            if "status_ampel = 'GRUEN'" in bedingung:
                return any(k.status_ampel == KostenAmpel.GRUEN for k in ersatzwagen)
            if "status_ampel = 'ORANGE'" in bedingung:
                return any(k.status_ampel == KostenAmpel.ORANGE for k in ersatzwagen)
            return True

        if "kostenposition.kategorie = 'REPARATUR'" in bedingung:
            reparatur = kontext["kosten_nach_kategorie"].get("REPARATUR", [])
            if not reparatur:
                return False
            if "status_ampel = 'GRUEN'" in bedingung:
                return any(k.status_ampel == KostenAmpel.GRUEN for k in reparatur)
            if "status_ampel = 'ORANGE'" in bedingung:
                return any(k.status_ampel == KostenAmpel.ORANGE for k in reparatur)
            return True

        # Korrespondenz-Prüfungen
        if "korrespondenz.richtung = 'RA_AN_VERSICHERUNG'" in bedingung:
            ra_an_vers = kontext["korrespondenz_nach_richtung"].get("RA_AN_VERSICHERUNG", [])
            if not ra_an_vers:
                return False
            if "status = 'VERSENDET'" in bedingung:
                return any(k.status == "VERSENDET" for k in ra_an_vers)
            if "status = 'FREIGEGEBEN'" in bedingung:
                return any(k.status == "FREIGEGEBEN" for k in ra_an_vers)
            if "antwort_erhalten = FALSE" in bedingung:
                return any(not k.antwort_erhalten for k in ra_an_vers)
            if "antwort_erhalten = TRUE" in bedingung:
                return any(k.antwort_erhalten for k in ra_an_vers)
            return True

        # Alle Kosten grün
        if "ALL(kostenposition.status_ampel = 'GRUEN')" in bedingung:
            return kontext["alle_kosten_gruen"]

        if "ANY(kostenposition.status_ampel = 'GRUEN')" in bedingung:
            if "ANY(kostenposition.status_ampel != 'GRUEN')" in bedingung:
                # Teilweise reguliert
                return (
                    kontext["hat_kosten_gruen"] and
                    not kontext["alle_kosten_gruen"]
                )
            return kontext["hat_kosten_gruen"]

        return False


# Singleton-Instanz
_engine_instance = None


def get_meilenstein_engine() -> MeilensteinEngine:
    """Gibt die Singleton-Instanz der Meilenstein-Engine zurück"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = MeilensteinEngine()
    return _engine_instance
