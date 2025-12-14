"""
DAT/Schwacke Fahrzeugbewertung Service
Integration für professionelle Fahrzeugbewertungen
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Numeric, Date
from sqlalchemy.orm import relationship
from src.models.base import Base


class BewertungsAnbieter(str, Enum):
    """Anbieter für Fahrzeugbewertung"""
    DAT = "DAT"
    SCHWACKE = "SCHWACKE"
    EUROTAX = "EUROTAX"
    MANUELL = "MANUELL"


class BewertungsTyp(str, Enum):
    """Typ der Bewertung"""
    WIEDERBESCHAFFUNGSWERT = "WIEDERBESCHAFFUNGSWERT"
    RESTWERT = "RESTWERT"
    HAENDLER_EK = "HAENDLER_EK"
    HAENDLER_VK = "HAENDLER_VK"
    ZEITWERT = "ZEITWERT"
    NEUPREIS = "NEUPREIS"


class ZustandsNote(str, Enum):
    """Zustandsnote des Fahrzeugs"""
    EINS = "1"      # Wie neu
    ZWEI = "2"      # Gut
    DREI = "3"      # Befriedigend
    VIER = "4"      # Ausreichend
    FUENF = "5"     # Mangelhaft


class Fahrzeugbewertung(Base):
    """Model für Fahrzeugbewertungen"""
    __tablename__ = "fahrzeugbewertung"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="fahrzeugbewertungen")

    # Anbieter
    anbieter = Column(SQLEnum(BewertungsAnbieter), default=BewertungsAnbieter.MANUELL)
    bewertungs_typ = Column(SQLEnum(BewertungsTyp), default=BewertungsTyp.WIEDERBESCHAFFUNGSWERT)

    # Fahrzeugdaten
    hersteller = Column(String(100))
    modell = Column(String(100))
    variante = Column(String(200))
    hsn = Column(String(10))  # Herstellerschlüsselnummer
    tsn = Column(String(10))  # Typschlüsselnummer
    fahrzeug_ident_nr = Column(String(20))  # VIN

    erstzulassung = Column(Date)
    kilometerstand = Column(Integer)
    hubraum = Column(Integer)
    leistung_kw = Column(Integer)
    kraftstoff = Column(String(50))
    getriebe = Column(String(50))

    # Zustand
    zustandsnote = Column(SQLEnum(ZustandsNote))
    _ausstattung = Column("ausstattung", Text)  # JSON
    _vorschaeden = Column("vorschaeden", Text)  # JSON

    # Bewertungsergebnis
    bewertungsdatum = Column(Date, default=date.today)
    wert_brutto = Column(Numeric(12, 2))
    wert_netto = Column(Numeric(12, 2))
    mwst_satz = Column(Numeric(5, 2), default=19.0)

    # Differenzbesteuerung
    differenzbesteuert = Column(Boolean, default=False)

    # Anpassungen
    korrektur_km = Column(Numeric(12, 2), default=0)  # +/- für Km-Abweichung
    korrektur_ausstattung = Column(Numeric(12, 2), default=0)
    korrektur_zustand = Column(Numeric(12, 2), default=0)
    korrektur_sonstige = Column(Numeric(12, 2), default=0)
    korrektur_beschreibung = Column(Text)

    # Referenzen
    dat_dossiernummer = Column(String(50))
    schwacke_id = Column(String(50))

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def ausstattung(self) -> List[str]:
        if self._ausstattung:
            return json.loads(self._ausstattung)
        return []

    @ausstattung.setter
    def ausstattung(self, value: List[str]):
        self._ausstattung = json.dumps(value)

    @property
    def vorschaeden(self) -> List[Dict]:
        if self._vorschaeden:
            return json.loads(self._vorschaeden)
        return []

    @vorschaeden.setter
    def vorschaeden(self, value: List[Dict]):
        self._vorschaeden = json.dumps(value)

    @property
    def wert_korrigiert(self) -> Decimal:
        """Berechnet den korrigierten Wert"""
        basis = self.wert_brutto or Decimal('0')
        korrekturen = (
            (self.korrektur_km or Decimal('0')) +
            (self.korrektur_ausstattung or Decimal('0')) +
            (self.korrektur_zustand or Decimal('0')) +
            (self.korrektur_sonstige or Decimal('0'))
        )
        return basis + korrekturen

    @property
    def fahrzeug_bezeichnung(self) -> str:
        """Vollständige Fahrzeugbezeichnung"""
        teile = [self.hersteller, self.modell, self.variante]
        return " ".join([t for t in teile if t])

    @property
    def alter_monate(self) -> int:
        """Fahrzeugalter in Monaten"""
        if not self.erstzulassung:
            return 0
        heute = date.today()
        monate = (heute.year - self.erstzulassung.year) * 12
        monate += heute.month - self.erstzulassung.month
        return max(0, monate)


class FahrzeugbewertungService:
    """Service für Fahrzeugbewertungen"""

    # Standard-Ausstattungen
    STANDARD_AUSSTATTUNGEN = [
        "Klimaanlage", "Klimaautomatik", "Navigationssystem", "Lederausstattung",
        "Sitzheizung", "Einparkhilfe", "Rückfahrkamera", "Tempomat",
        "Adaptiver Tempomat", "LED-Scheinwerfer", "Xenon-Scheinwerfer",
        "Panoramadach", "Schiebedach", "Alufelgen", "Metallic-Lackierung",
        "Anhängerkupplung", "Standheizung", "Elektrische Sitze",
        "Soundsystem", "Bluetooth", "Apple CarPlay", "Android Auto"
    ]

    # Km-Korrekturfaktoren pro 1000 km Abweichung
    KM_KORREKTUR_FAKTOREN = {
        'KLEINWAGEN': 50,
        'KOMPAKTWAGEN': 75,
        'MITTELKLASSE': 100,
        'OBERKLASSE': 150,
        'SUV': 125,
        'TRANSPORTER': 60
    }

    def __init__(self, db_session):
        self.db = db_session

    def bewertung_erstellen(
        self,
        projekt_id: int,
        hersteller: str,
        modell: str,
        erstzulassung: date,
        kilometerstand: int,
        anbieter: BewertungsAnbieter = BewertungsAnbieter.MANUELL,
        bewertungs_typ: BewertungsTyp = BewertungsTyp.WIEDERBESCHAFFUNGSWERT,
        erstellt_von_user_id: Optional[int] = None,
        **kwargs
    ) -> Fahrzeugbewertung:
        """Erstellt eine neue Fahrzeugbewertung"""
        bewertung = Fahrzeugbewertung(
            projekt_id=projekt_id,
            hersteller=hersteller,
            modell=modell,
            erstzulassung=erstzulassung,
            kilometerstand=kilometerstand,
            anbieter=anbieter,
            bewertungs_typ=bewertungs_typ,
            erstellt_von_user_id=erstellt_von_user_id
        )

        # Zusätzliche Felder setzen
        for key, value in kwargs.items():
            if hasattr(bewertung, key):
                setattr(bewertung, key, value)

        self.db.add(bewertung)
        self.db.flush()

        return bewertung

    def wert_berechnen(
        self,
        bewertung_id: int,
        basis_wert: Decimal
    ) -> Fahrzeugbewertung:
        """Berechnet den Fahrzeugwert mit Korrekturen"""
        bewertung = self.db.query(Fahrzeugbewertung).get(bewertung_id)

        if not bewertung:
            raise ValueError("Bewertung nicht gefunden")

        bewertung.wert_brutto = basis_wert

        # Netto berechnen
        if bewertung.differenzbesteuert:
            bewertung.wert_netto = basis_wert
        else:
            mwst = bewertung.mwst_satz or Decimal('19')
            bewertung.wert_netto = basis_wert / (1 + mwst / 100)

        self.db.flush()

        return bewertung

    def km_korrektur_berechnen(
        self,
        bewertung_id: int,
        soll_km: int,
        fahrzeugklasse: str = 'MITTELKLASSE'
    ) -> Decimal:
        """Berechnet die Kilometerkorrektur"""
        bewertung = self.db.query(Fahrzeugbewertung).get(bewertung_id)

        if not bewertung or not bewertung.kilometerstand:
            return Decimal('0')

        diff_km = soll_km - bewertung.kilometerstand
        faktor = self.KM_KORREKTUR_FAKTOREN.get(fahrzeugklasse, 100)

        korrektur = Decimal(str((diff_km / 1000) * faktor))

        bewertung.korrektur_km = korrektur
        self.db.flush()

        return korrektur

    def dat_abfrage_simulieren(
        self,
        hsn: str,
        tsn: str,
        erstzulassung: date,
        kilometerstand: int
    ) -> Dict[str, Any]:
        """
        Simuliert eine DAT-Abfrage
        In Produktion: Echte DAT SilverDAT API Integration
        """
        # Simulierte Daten - in Produktion würde hier die DAT API aufgerufen
        alter_monate = (date.today().year - erstzulassung.year) * 12
        alter_monate += date.today().month - erstzulassung.month

        # Einfache Wertberechnung für Demo
        basis_wert = 35000  # Beispiel-Neupreis
        abschreibung_pro_monat = 0.015  # 1.5% pro Monat
        km_abschreibung = kilometerstand * 0.05  # 5 Cent pro km

        wert = basis_wert * (1 - abschreibung_pro_monat * min(alter_monate, 48))
        wert -= km_abschreibung
        wert = max(wert, 500)  # Mindestwert

        return {
            'anbieter': 'DAT',
            'datum': date.today().isoformat(),
            'hsn': hsn,
            'tsn': tsn,
            'hersteller': 'Volkswagen',
            'modell': 'Golf',
            'variante': '1.4 TSI Comfortline',
            'wiederbeschaffungswert_brutto': round(wert, 2),
            'wiederbeschaffungswert_netto': round(wert / 1.19, 2),
            'restwert': round(wert * 0.15, 2),
            'neupreis': basis_wert,
            'standard_km': 15000 * (alter_monate / 12),
            'dossiernummer': f"DAT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }

    def schwacke_abfrage_simulieren(
        self,
        hersteller: str,
        modell: str,
        erstzulassung: date,
        kilometerstand: int,
        ausstattung: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Simuliert eine Schwacke-Abfrage
        In Produktion: Echte Schwacke API Integration
        """
        alter_monate = (date.today().year - erstzulassung.year) * 12
        alter_monate += date.today().month - erstzulassung.month

        # Basis-Wert (simuliert)
        basis_wert = 30000
        wert = basis_wert * (1 - 0.02 * min(alter_monate, 36))
        wert -= kilometerstand * 0.04

        # Ausstattungsaufschläge
        ausstattung_wert = 0
        if ausstattung:
            ausstattung_werte = {
                'Navigationssystem': 800,
                'Lederausstattung': 1500,
                'LED-Scheinwerfer': 500,
                'Panoramadach': 1200,
                'Standheizung': 800
            }
            for item in ausstattung:
                ausstattung_wert += ausstattung_werte.get(item, 200)

        wert += ausstattung_wert
        wert = max(wert, 500)

        return {
            'anbieter': 'Schwacke',
            'datum': date.today().isoformat(),
            'hersteller': hersteller,
            'modell': modell,
            'haendler_ek': round(wert * 0.85, 2),
            'haendler_vk': round(wert, 2),
            'privat_vk': round(wert * 0.92, 2),
            'ausstattungswert': ausstattung_wert,
            'schwacke_id': f"SCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }

    def bewertung_aktualisieren(
        self,
        bewertung_id: int,
        **kwargs
    ) -> Optional[Fahrzeugbewertung]:
        """Aktualisiert eine Bewertung"""
        bewertung = self.db.query(Fahrzeugbewertung).get(bewertung_id)

        if bewertung:
            for key, value in kwargs.items():
                if hasattr(bewertung, key):
                    setattr(bewertung, key, value)
            self.db.flush()

        return bewertung

    def bewertungen_fuer_projekt(self, projekt_id: int) -> List[Fahrzeugbewertung]:
        """Holt alle Bewertungen für ein Projekt"""
        return self.db.query(Fahrzeugbewertung).filter(
            Fahrzeugbewertung.projekt_id == projekt_id
        ).order_by(Fahrzeugbewertung.bewertungsdatum.desc()).all()

    def aktuelle_bewertung(
        self,
        projekt_id: int,
        bewertungs_typ: BewertungsTyp = BewertungsTyp.WIEDERBESCHAFFUNGSWERT
    ) -> Optional[Fahrzeugbewertung]:
        """Holt die aktuellste Bewertung eines Typs"""
        return self.db.query(Fahrzeugbewertung).filter(
            Fahrzeugbewertung.projekt_id == projekt_id,
            Fahrzeugbewertung.bewertungs_typ == bewertungs_typ
        ).order_by(Fahrzeugbewertung.bewertungsdatum.desc()).first()

    def totalschaden_pruefen(
        self,
        wiederbeschaffungswert: Decimal,
        restwert: Decimal,
        reparaturkosten: Decimal,
        grenzwert_prozent: Decimal = Decimal('130')
    ) -> Dict[str, Any]:
        """Prüft ob ein wirtschaftlicher Totalschaden vorliegt"""
        if wiederbeschaffungswert <= 0:
            return {'fehler': 'Wiederbeschaffungswert muss größer 0 sein'}

        # Wirtschaftlicher Totalschaden wenn Reparaturkosten > 130% des WBW
        grenze = wiederbeschaffungswert * grenzwert_prozent / 100
        ist_totalschaden = reparaturkosten > grenze

        # Integritätsinteresse (bis 130% des WBW)
        integritaet_moeglich = reparaturkosten <= grenze

        # Abrechnung auf Totalschadenbasis
        abrechnungsbetrag_totalschaden = wiederbeschaffungswert - restwert

        return {
            'ist_totalschaden': ist_totalschaden,
            'wirtschaftlichkeitsgrenze': float(grenze),
            'reparaturkosten': float(reparaturkosten),
            'wiederbeschaffungswert': float(wiederbeschaffungswert),
            'restwert': float(restwert),
            'integritaet_moeglich': integritaet_moeglich,
            'abrechnungsbetrag_totalschaden': float(abrechnungsbetrag_totalschaden),
            'empfehlung': 'Totalschadenabrechnung' if ist_totalschaden else 'Reparatur wirtschaftlich'
        }

    def generiere_bewertungs_report(self, bewertung_id: int) -> str:
        """Generiert einen Textbericht der Bewertung"""
        bewertung = self.db.query(Fahrzeugbewertung).get(bewertung_id)

        if not bewertung:
            return "Bewertung nicht gefunden"

        report = f"""
FAHRZEUGBEWERTUNG
=================

Fahrzeug: {bewertung.fahrzeug_bezeichnung}
Erstzulassung: {bewertung.erstzulassung.strftime('%d.%m.%Y') if bewertung.erstzulassung else '-'}
Kilometerstand: {bewertung.kilometerstand:,} km
Fahrzeugalter: {bewertung.alter_monate} Monate

Bewertung:
----------
Anbieter: {bewertung.anbieter.value if bewertung.anbieter else '-'}
Bewertungsdatum: {bewertung.bewertungsdatum.strftime('%d.%m.%Y') if bewertung.bewertungsdatum else '-'}
Bewertungstyp: {bewertung.bewertungs_typ.value if bewertung.bewertungs_typ else '-'}

Werte:
------
Brutto: {float(bewertung.wert_brutto):,.2f} EUR
Netto: {float(bewertung.wert_netto):,.2f} EUR

Korrekturen:
- Kilometer: {float(bewertung.korrektur_km or 0):+,.2f} EUR
- Ausstattung: {float(bewertung.korrektur_ausstattung or 0):+,.2f} EUR
- Zustand: {float(bewertung.korrektur_zustand or 0):+,.2f} EUR
- Sonstige: {float(bewertung.korrektur_sonstige or 0):+,.2f} EUR

KORRIGIERTER WERT: {float(bewertung.wert_korrigiert):,.2f} EUR

Ausstattung: {', '.join(bewertung.ausstattung) if bewertung.ausstattung else '-'}
"""
        return report
