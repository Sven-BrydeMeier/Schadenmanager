"""
Papierkorb-Service für Soft-Delete von Dokumenten und Dateien
Ermöglicht das Wiederherstellen gelöschter Dateien innerhalb eines konfigurierbaren Zeitraums
"""
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models import Dokument
from src.config.settings import get_settings


class PapierkorbService:
    """Service für Papierkorb-Operationen"""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self._ensure_papierkorb_folder()

    def _ensure_papierkorb_folder(self):
        """Stellt sicher, dass der Papierkorb-Ordner existiert"""
        os.makedirs(self.settings.papierkorb_folder, exist_ok=True)

    def in_papierkorb_verschieben(
        self,
        dokument_id: int,
        user_id: int
    ) -> Tuple[bool, str]:
        """
        Verschiebt ein Dokument in den Papierkorb (Soft-Delete).

        Args:
            dokument_id: ID des zu löschenden Dokuments
            user_id: ID des löschenden Benutzers

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        dokument = self.db.query(Dokument).filter(
            Dokument.id == dokument_id,
            Dokument.geloescht == False
        ).first()

        if not dokument:
            return False, "Dokument nicht gefunden oder bereits gelöscht"

        try:
            # Datei physisch in Papierkorb verschieben
            if dokument.dateipfad and os.path.exists(dokument.dateipfad):
                # Neuen Pfad im Papierkorb erstellen
                dateiname = os.path.basename(dokument.dateipfad)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                neuer_dateiname = f"{timestamp}_{dokument_id}_{dateiname}"
                papierkorb_pfad = os.path.join(
                    self.settings.papierkorb_folder,
                    neuer_dateiname
                )

                # Datei verschieben
                shutil.move(dokument.dateipfad, papierkorb_pfad)

                # Ursprünglichen Pfad speichern
                dokument.urspruenglicher_pfad = dokument.dateipfad
                dokument.dateipfad = papierkorb_pfad

            # Soft-Delete markieren
            dokument.geloescht = True
            dokument.geloescht_am = datetime.now()
            dokument.geloescht_von_user_id = user_id

            self.db.flush()

            return True, f"Dokument '{dokument.original_dateiname}' in den Papierkorb verschoben"

        except Exception as e:
            return False, f"Fehler beim Löschen: {str(e)}"

    def wiederherstellen(self, dokument_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Stellt ein Dokument aus dem Papierkorb wieder her.

        Args:
            dokument_id: ID des wiederherzustellenden Dokuments
            user_id: ID des wiederherstellenden Benutzers

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        dokument = self.db.query(Dokument).filter(
            Dokument.id == dokument_id,
            Dokument.geloescht == True
        ).first()

        if not dokument:
            return False, "Dokument nicht gefunden oder nicht im Papierkorb"

        # Prüfen ob noch innerhalb der Aufbewahrungsfrist
        if not self._ist_wiederherstellbar(dokument):
            return False, "Aufbewahrungsfrist abgelaufen - Dokument kann nicht mehr wiederhergestellt werden"

        try:
            # Datei zurück verschieben
            if dokument.dateipfad and os.path.exists(dokument.dateipfad):
                if dokument.urspruenglicher_pfad:
                    # Zielverzeichnis erstellen falls nicht vorhanden
                    ziel_verzeichnis = os.path.dirname(dokument.urspruenglicher_pfad)
                    os.makedirs(ziel_verzeichnis, exist_ok=True)

                    # Datei zurück verschieben
                    shutil.move(dokument.dateipfad, dokument.urspruenglicher_pfad)
                    dokument.dateipfad = dokument.urspruenglicher_pfad

            # Soft-Delete aufheben
            dokument.geloescht = False
            dokument.geloescht_am = None
            dokument.geloescht_von_user_id = None
            dokument.urspruenglicher_pfad = None

            self.db.flush()

            return True, f"Dokument '{dokument.original_dateiname}' wiederhergestellt"

        except Exception as e:
            return False, f"Fehler bei der Wiederherstellung: {str(e)}"

    def endgueltig_loeschen(self, dokument_id: int) -> Tuple[bool, str]:
        """
        Löscht ein Dokument endgültig aus dem Papierkorb.

        Args:
            dokument_id: ID des zu löschenden Dokuments

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        dokument = self.db.query(Dokument).filter(
            Dokument.id == dokument_id,
            Dokument.geloescht == True
        ).first()

        if not dokument:
            return False, "Dokument nicht gefunden oder nicht im Papierkorb"

        try:
            dateiname = dokument.original_dateiname

            # Physische Datei löschen
            if dokument.dateipfad and os.path.exists(dokument.dateipfad):
                os.remove(dokument.dateipfad)

            # Datenbankeinträge löschen
            self.db.delete(dokument)
            self.db.flush()

            return True, f"Dokument '{dateiname}' endgültig gelöscht"

        except Exception as e:
            return False, f"Fehler beim endgültigen Löschen: {str(e)}"

    def papierkorb_leeren(self, user_id: int) -> Tuple[int, int]:
        """
        Leert den gesamten Papierkorb.

        Args:
            user_id: ID des Benutzers

        Returns:
            Tuple (Anzahl gelöscht, Anzahl Fehler)
        """
        dokumente = self.db.query(Dokument).filter(
            Dokument.geloescht == True
        ).all()

        geloescht = 0
        fehler = 0

        for dok in dokumente:
            erfolg, _ = self.endgueltig_loeschen(dok.id)
            if erfolg:
                geloescht += 1
            else:
                fehler += 1

        return geloescht, fehler

    def abgelaufene_loeschen(self) -> Tuple[int, int]:
        """
        Löscht alle Dokumente deren Aufbewahrungsfrist abgelaufen ist.

        Returns:
            Tuple (Anzahl gelöscht, Anzahl Fehler)
        """
        if not self.settings.papierkorb_auto_loeschen:
            return 0, 0

        ablauf_zeit = datetime.now() - timedelta(
            hours=self.settings.papierkorb_aufbewahrung_stunden
        )

        abgelaufene = self.db.query(Dokument).filter(
            Dokument.geloescht == True,
            Dokument.geloescht_am < ablauf_zeit
        ).all()

        geloescht = 0
        fehler = 0

        for dok in abgelaufene:
            erfolg, _ = self.endgueltig_loeschen(dok.id)
            if erfolg:
                geloescht += 1
            else:
                fehler += 1

        return geloescht, fehler

    def get_papierkorb_inhalt(
        self,
        projekt_id: Optional[int] = None,
        nur_eigene: bool = False,
        user_id: Optional[int] = None
    ) -> List[Dokument]:
        """
        Holt alle Dokumente im Papierkorb.

        Args:
            projekt_id: Optional - nur Dokumente eines bestimmten Projekts
            nur_eigene: Nur vom Benutzer gelöschte Dokumente
            user_id: Benutzer-ID (erforderlich wenn nur_eigene=True)

        Returns:
            Liste der Dokumente im Papierkorb
        """
        query = self.db.query(Dokument).filter(Dokument.geloescht == True)

        if projekt_id:
            query = query.filter(Dokument.unfallprojekt_id == projekt_id)

        if nur_eigene and user_id:
            query = query.filter(Dokument.geloescht_von_user_id == user_id)

        return query.order_by(Dokument.geloescht_am.desc()).all()

    def get_statistik(self) -> Dict:
        """
        Gibt Statistiken zum Papierkorb zurück.

        Returns:
            Dictionary mit Statistiken
        """
        dokumente = self.db.query(Dokument).filter(
            Dokument.geloescht == True
        ).all()

        jetzt = datetime.now()
        aufbewahrung_stunden = self.settings.papierkorb_aufbewahrung_stunden

        gesamt = len(dokumente)
        wiederherstellbar = 0
        abgelaufen = 0
        gesamt_groesse = 0

        for dok in dokumente:
            if dok.dateigroesse:
                gesamt_groesse += dok.dateigroesse

            if self._ist_wiederherstellbar(dok):
                wiederherstellbar += 1
            else:
                abgelaufen += 1

        return {
            "gesamt": gesamt,
            "wiederherstellbar": wiederherstellbar,
            "abgelaufen": abgelaufen,
            "gesamt_groesse_mb": round(gesamt_groesse / (1024 * 1024), 2),
            "aufbewahrung_stunden": aufbewahrung_stunden
        }

    def _ist_wiederherstellbar(self, dokument: Dokument) -> bool:
        """Prüft ob ein Dokument noch wiederhergestellt werden kann"""
        if not dokument.geloescht_am:
            return True

        ablauf_zeit = dokument.geloescht_am + timedelta(
            hours=self.settings.papierkorb_aufbewahrung_stunden
        )
        return datetime.now() < ablauf_zeit

    def get_verbleibende_zeit(self, dokument: Dokument) -> Optional[timedelta]:
        """
        Berechnet die verbleibende Zeit bis zur endgültigen Löschung.

        Args:
            dokument: Das Dokument

        Returns:
            timedelta oder None wenn bereits abgelaufen
        """
        if not dokument.geloescht_am:
            return timedelta(hours=self.settings.papierkorb_aufbewahrung_stunden)

        ablauf_zeit = dokument.geloescht_am + timedelta(
            hours=self.settings.papierkorb_aufbewahrung_stunden
        )
        verbleibend = ablauf_zeit - datetime.now()

        return verbleibend if verbleibend.total_seconds() > 0 else None


def get_papierkorb_service(db: Session) -> PapierkorbService:
    """Factory-Funktion für den Papierkorb-Service"""
    return PapierkorbService(db)
