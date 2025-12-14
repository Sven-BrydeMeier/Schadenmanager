"""
Bankkonten-Abgleich Service
Ermöglicht den Import von Kontoauszügen und automatische Zuordnung zu Projekten
"""
import csv
import re
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models import UnfallProjekt, KostenPosition


class BankTransaktionsTyp(str, Enum):
    """Typ der Transaktion"""
    EINGANG = "eingang"
    AUSGANG = "ausgang"


class ZuordnungsStatus(str, Enum):
    """Status der Zuordnung"""
    ZUGEORDNET = "zugeordnet"
    VORGESCHLAGEN = "vorgeschlagen"
    NICHT_ZUGEORDNET = "nicht_zugeordnet"
    MANUELL = "manuell"


class BankTransaktion:
    """Repräsentiert eine Bank-Transaktion"""

    def __init__(
        self,
        datum: datetime,
        betrag: Decimal,
        verwendungszweck: str,
        auftraggeber: Optional[str] = None,
        iban: Optional[str] = None,
        bic: Optional[str] = None,
        typ: BankTransaktionsTyp = None
    ):
        self.datum = datum
        self.betrag = betrag
        self.verwendungszweck = verwendungszweck
        self.auftraggeber = auftraggeber
        self.iban = iban
        self.bic = bic
        self.typ = typ or (BankTransaktionsTyp.EINGANG if betrag > 0 else BankTransaktionsTyp.AUSGANG)

        # Zuordnung
        self.projekt_id: Optional[int] = None
        self.projekt: Optional[UnfallProjekt] = None
        self.zuordnungs_status: ZuordnungsStatus = ZuordnungsStatus.NICHT_ZUGEORDNET
        self.konfidenz: float = 0.0


class BankabgleichService:
    """Service für den Bankkonten-Abgleich"""

    def __init__(self, db: Session):
        self.db = db

    def csv_importieren(
        self,
        csv_content: str,
        bank_format: str = "standard"
    ) -> Tuple[bool, str, List[BankTransaktion]]:
        """
        Importiert Transaktionen aus einer CSV-Datei.

        Args:
            csv_content: Inhalt der CSV-Datei
            bank_format: Format der Bank (standard, sparkasse, volksbank, etc.)

        Returns:
            Tuple (Erfolg, Nachricht, Liste der Transaktionen)
        """
        try:
            transaktionen = []
            lines = csv_content.strip().split('\n')

            # Format-spezifische Spalten-Mapping
            spalten_mapping = self._get_spalten_mapping(bank_format)

            reader = csv.DictReader(lines, delimiter=';')

            for row in reader:
                try:
                    # Datum parsen
                    datum_str = row.get(spalten_mapping['datum'], '')
                    datum = self._parse_datum(datum_str)

                    # Betrag parsen
                    betrag_str = row.get(spalten_mapping['betrag'], '0')
                    betrag = self._parse_betrag(betrag_str)

                    # Verwendungszweck
                    verwendungszweck = row.get(spalten_mapping['verwendungszweck'], '')

                    # Auftraggeber/Empfänger
                    auftraggeber = row.get(spalten_mapping.get('auftraggeber', ''), '')

                    # IBAN
                    iban = row.get(spalten_mapping.get('iban', ''), '')

                    transaktion = BankTransaktion(
                        datum=datum,
                        betrag=betrag,
                        verwendungszweck=verwendungszweck,
                        auftraggeber=auftraggeber,
                        iban=iban
                    )

                    transaktionen.append(transaktion)

                except Exception as e:
                    continue  # Fehlerhafte Zeile überspringen

            return True, f"{len(transaktionen)} Transaktionen importiert", transaktionen

        except Exception as e:
            return False, f"Fehler beim Import: {str(e)}", []

    def transaktionen_zuordnen(
        self,
        transaktionen: List[BankTransaktion]
    ) -> List[BankTransaktion]:
        """
        Ordnet Transaktionen automatisch Projekten zu.

        Args:
            transaktionen: Liste der zu prüfenden Transaktionen

        Returns:
            Liste der Transaktionen mit Zuordnungen
        """
        # Alle aktiven Projekte laden
        projekte = self.db.query(UnfallProjekt).filter(
            or_(
                UnfallProjekt.status == "AKTIV",
                UnfallProjekt.status == "IN_BEARBEITUNG"
            )
        ).all()

        for transaktion in transaktionen:
            beste_zuordnung = None
            beste_konfidenz = 0.0

            for projekt in projekte:
                konfidenz = self._berechne_zuordnungs_konfidenz(transaktion, projekt)

                if konfidenz > beste_konfidenz:
                    beste_konfidenz = konfidenz
                    beste_zuordnung = projekt

            if beste_zuordnung and beste_konfidenz >= 0.7:
                transaktion.projekt_id = beste_zuordnung.id
                transaktion.projekt = beste_zuordnung
                transaktion.konfidenz = beste_konfidenz
                transaktion.zuordnungs_status = ZuordnungsStatus.ZUGEORDNET
            elif beste_zuordnung and beste_konfidenz >= 0.4:
                transaktion.projekt_id = beste_zuordnung.id
                transaktion.projekt = beste_zuordnung
                transaktion.konfidenz = beste_konfidenz
                transaktion.zuordnungs_status = ZuordnungsStatus.VORGESCHLAGEN

        return transaktionen

    def zuordnung_bestaetigen(
        self,
        transaktion: BankTransaktion,
        projekt_id: int,
        als_erstattung: bool = True,
        beschreibung: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Bestätigt eine Zuordnung und erstellt eine Kostenposition.

        Args:
            transaktion: Die Transaktion
            projekt_id: ID des Projekts
            als_erstattung: Ob es eine Erstattung ist
            beschreibung: Optionale Beschreibung

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        projekt = self.db.query(UnfallProjekt).filter(
            UnfallProjekt.id == projekt_id
        ).first()

        if not projekt:
            return False, "Projekt nicht gefunden"

        # Prüfen ob bereits eine Kostenposition mit diesem Betrag existiert
        if als_erstattung:
            # Bei Erstattungen: Passende Kostenposition finden und aktualisieren
            passende_positionen = self.db.query(KostenPosition).filter(
                KostenPosition.unfallprojekt_id == projekt_id,
                KostenPosition.erstattet_betrag.is_(None) | (KostenPosition.erstattet_betrag == 0)
            ).all()

            # Beste Übereinstimmung finden
            for pos in passende_positionen:
                if abs(float(pos.betrag) - float(transaktion.betrag)) < 0.01:
                    pos.erstattet_betrag = transaktion.betrag
                    pos.erstattet_am = transaktion.datum
                    pos.notizen = f"Zahlung am {transaktion.datum.strftime('%d.%m.%Y')} eingegangen. {beschreibung or ''}"
                    self.db.flush()
                    return True, f"Erstattung der Kostenposition '{pos.beschreibung}' erfasst"

        # Neue Kostenposition erstellen
        from src.models import KostenKategorie, KostenAmpel

        position = KostenPosition(
            unfallprojekt_id=projekt_id,
            kategorie=KostenKategorie.SONSTIG,
            beschreibung=beschreibung or f"Bank-Import: {transaktion.verwendungszweck[:100]}",
            betrag=abs(transaktion.betrag),
            ampel=KostenAmpel.GRUEN if als_erstattung else KostenAmpel.ROT,
            erstattet_betrag=transaktion.betrag if als_erstattung else None,
            erstattet_am=transaktion.datum if als_erstattung else None
        )

        self.db.add(position)
        self.db.flush()

        return True, "Kostenposition erstellt"

    def get_offene_zahlungen(self, projekt_id: Optional[int] = None) -> List[KostenPosition]:
        """
        Holt alle Kostenpositionen die noch nicht erstattet wurden.

        Args:
            projekt_id: Optional - nur für bestimmtes Projekt

        Returns:
            Liste der offenen Kostenpositionen
        """
        query = self.db.query(KostenPosition).filter(
            or_(
                KostenPosition.erstattet_betrag.is_(None),
                KostenPosition.erstattet_betrag == 0
            )
        )

        if projekt_id:
            query = query.filter(KostenPosition.unfallprojekt_id == projekt_id)

        return query.order_by(KostenPosition.erstellt_am.desc()).all()

    def get_statistik(self) -> Dict:
        """
        Gibt Statistiken zu Zahlungen zurück.

        Returns:
            Dictionary mit Statistiken
        """
        alle_positionen = self.db.query(KostenPosition).all()

        gesamt_gefordert = sum(float(p.betrag) for p in alle_positionen)
        gesamt_erstattet = sum(float(p.erstattet_betrag or 0) for p in alle_positionen)
        offen = gesamt_gefordert - gesamt_erstattet

        return {
            "gesamt_gefordert": gesamt_gefordert,
            "gesamt_erstattet": gesamt_erstattet,
            "offen": offen,
            "anzahl_positionen": len(alle_positionen),
            "anzahl_offen": len([p for p in alle_positionen if not p.erstattet_betrag])
        }

    def _get_spalten_mapping(self, bank_format: str) -> Dict[str, str]:
        """Gibt das Spalten-Mapping für das Bank-Format zurück"""
        mappings = {
            "standard": {
                "datum": "Buchungstag",
                "betrag": "Betrag",
                "verwendungszweck": "Verwendungszweck",
                "auftraggeber": "Auftraggeber/Empfänger",
                "iban": "IBAN"
            },
            "sparkasse": {
                "datum": "Buchungstag",
                "betrag": "Betrag",
                "verwendungszweck": "Verwendungszweck",
                "auftraggeber": "Beguenstigter/Zahlungspflichtiger",
                "iban": "Kontonummer/IBAN"
            },
            "volksbank": {
                "datum": "Buchungstag",
                "betrag": "Umsatz",
                "verwendungszweck": "Vorgang/Verwendungszweck",
                "auftraggeber": "Empfänger/Zahlungspflichtiger",
                "iban": "IBAN"
            },
            "deutsche_bank": {
                "datum": "Buchungstag",
                "betrag": "Betrag (EUR)",
                "verwendungszweck": "Verwendungszweck",
                "auftraggeber": "Auftraggeber / Begünstigter",
                "iban": "IBAN Auftraggeber"
            }
        }

        return mappings.get(bank_format, mappings["standard"])

    def _parse_datum(self, datum_str: str) -> datetime:
        """Parst ein Datum aus verschiedenen Formaten"""
        formate = [
            "%d.%m.%Y",
            "%d.%m.%y",
            "%Y-%m-%d",
            "%d/%m/%Y"
        ]

        for fmt in formate:
            try:
                return datetime.strptime(datum_str.strip(), fmt)
            except ValueError:
                continue

        return datetime.now()

    def _parse_betrag(self, betrag_str: str) -> Decimal:
        """Parst einen Betrag aus verschiedenen Formaten"""
        # Leerzeichen und Währungszeichen entfernen
        betrag_str = re.sub(r'[€$\s]', '', betrag_str)

        # Deutsches Format: 1.234,56 -> 1234.56
        if ',' in betrag_str and '.' in betrag_str:
            betrag_str = betrag_str.replace('.', '').replace(',', '.')
        elif ',' in betrag_str:
            betrag_str = betrag_str.replace(',', '.')

        try:
            return Decimal(betrag_str)
        except:
            return Decimal('0')

    def _berechne_zuordnungs_konfidenz(
        self,
        transaktion: BankTransaktion,
        projekt: UnfallProjekt
    ) -> float:
        """
        Berechnet die Konfidenz einer Zuordnung.

        Args:
            transaktion: Die Transaktion
            projekt: Das Projekt

        Returns:
            Konfidenz-Wert zwischen 0 und 1
        """
        konfidenz = 0.0
        verwendungszweck = transaktion.verwendungszweck.lower()

        # Aktenzeichen prüfen
        if projekt.aktenzeichen:
            az_clean = projekt.aktenzeichen.lower().replace('/', '').replace('-', '')
            vz_clean = verwendungszweck.replace('/', '').replace('-', '')
            if az_clean in vz_clean:
                konfidenz += 0.5

        # Projektnummer prüfen
        if projekt.projektnummer:
            if projekt.projektnummer.lower() in verwendungszweck:
                konfidenz += 0.3

        # Kennzeichen prüfen
        if projekt.fahrzeug and projekt.fahrzeug.kennzeichen:
            kz_clean = projekt.fahrzeug.kennzeichen.lower().replace(' ', '').replace('-', '')
            vz_clean = verwendungszweck.replace(' ', '').replace('-', '')
            if kz_clean in vz_clean:
                konfidenz += 0.3

        # Versicherungs-Keywords
        versicherungs_keywords = ['huk', 'allianz', 'axa', 'generali', 'zurich', 'vgh', 'devk', 'ergo']
        for keyword in versicherungs_keywords:
            if keyword in verwendungszweck:
                konfidenz += 0.1
                break

        # Schadens-Keywords
        schadens_keywords = ['schaden', 'unfall', 'regulierung', 'erstattung', 'reparatur']
        for keyword in schadens_keywords:
            if keyword in verwendungszweck:
                konfidenz += 0.1
                break

        # Betragsabgleich mit offenen Positionen
        for kostenpos in projekt.kostenpositionen:
            if not kostenpos.erstattet_betrag:
                if abs(float(kostenpos.betrag) - abs(float(transaktion.betrag))) < 1.0:
                    konfidenz += 0.3
                    break

        return min(konfidenz, 1.0)


def get_bankabgleich_service(db: Session) -> BankabgleichService:
    """Factory-Funktion für den Bankabgleich-Service"""
    return BankabgleichService(db)
