"""
Aktenmanagement-Service für Aktenzeichen-Generierung
"""
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import UnfallProjekt


class AktenmanagementService:
    """Service für Aktenzeichen-Verwaltung"""

    def __init__(self, db: Session):
        self.db = db

    def generiere_aktenzeichen(self, organisation_id: Optional[int] = None) -> str:
        """
        Generiert ein neues Aktenzeichen im Format "NNN/YY".

        Format:
        - NNN: Fortlaufende Nummer (1, 2, 3, ...)
        - YY: Zweistellige Jahreszahl

        Args:
            organisation_id: Optional - für organisationsspezifische Nummerierung

        Returns:
            Aktenzeichen im Format "NNN/YY"
        """
        aktuelles_jahr = datetime.now().year
        jahr_kurz = str(aktuelles_jahr)[-2:]  # "25" für 2025

        # Höchste Nummer für dieses Jahr finden
        query = self.db.query(
            func.max(UnfallProjekt.aktenzeichen_nummer)
        ).filter(
            UnfallProjekt.aktenzeichen_jahr == aktuelles_jahr
        )

        if organisation_id:
            query = query.filter(
                UnfallProjekt.anlegende_organisation_id == organisation_id
            )

        hoechste_nummer = query.scalar() or 0
        neue_nummer = hoechste_nummer + 1

        return f"{neue_nummer}/{jahr_kurz}"

    def parse_aktenzeichen(self, aktenzeichen: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Parst ein Aktenzeichen und gibt Nummer und Jahr zurück.

        Args:
            aktenzeichen: Aktenzeichen im Format "NNN/YY"

        Returns:
            Tuple aus (Nummer, Jahr) oder (None, None) bei ungültigem Format
        """
        if not aktenzeichen or "/" not in aktenzeichen:
            return None, None

        try:
            teile = aktenzeichen.split("/")
            nummer = int(teile[0])
            jahr_kurz = int(teile[1])

            # Jahr ergänzen (z.B. "25" -> 2025)
            if jahr_kurz < 100:
                if jahr_kurz > 50:
                    jahr = 1900 + jahr_kurz
                else:
                    jahr = 2000 + jahr_kurz
            else:
                jahr = jahr_kurz

            return nummer, jahr

        except (ValueError, IndexError):
            return None, None

    def aktenzeichen_existiert(self, aktenzeichen: str, organisation_id: Optional[int] = None) -> bool:
        """
        Prüft ob ein Aktenzeichen bereits existiert.

        Args:
            aktenzeichen: Das zu prüfende Aktenzeichen
            organisation_id: Optional - für organisationsspezifische Prüfung

        Returns:
            True wenn das Aktenzeichen bereits existiert
        """
        nummer, jahr = self.parse_aktenzeichen(aktenzeichen)
        if nummer is None:
            return False

        query = self.db.query(UnfallProjekt).filter(
            UnfallProjekt.aktenzeichen_nummer == nummer,
            UnfallProjekt.aktenzeichen_jahr == jahr
        )

        if organisation_id:
            query = query.filter(
                UnfallProjekt.anlegende_organisation_id == organisation_id
            )

        return query.first() is not None

    def suche_nach_aktenzeichen(
        self,
        aktenzeichen: str,
        organisation_id: Optional[int] = None
    ) -> Optional[UnfallProjekt]:
        """
        Sucht ein Projekt nach Aktenzeichen.

        Args:
            aktenzeichen: Das Aktenzeichen
            organisation_id: Optional - für organisationsspezifische Suche

        Returns:
            Das gefundene Projekt oder None
        """
        nummer, jahr = self.parse_aktenzeichen(aktenzeichen)
        if nummer is None:
            return None

        query = self.db.query(UnfallProjekt).filter(
            UnfallProjekt.aktenzeichen_nummer == nummer,
            UnfallProjekt.aktenzeichen_jahr == jahr
        )

        if organisation_id:
            query = query.filter(
                UnfallProjekt.anlegende_organisation_id == organisation_id
            )

        return query.first()
