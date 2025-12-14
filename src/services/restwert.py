"""
Restwertbörse-Integration Service
Verwaltung von Restwertanfragen bei Totalschäden
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Date, Numeric
from sqlalchemy.orm import relationship
from src.models.base import Base


class RestwertStatus(str, Enum):
    """Status einer Restwertanfrage"""
    ENTWURF = "ENTWURF"
    ANFRAGE_GESENDET = "ANFRAGE_GESENDET"
    ANGEBOTE_EINGEGANGEN = "ANGEBOTE_EINGEGANGEN"
    ANGEBOT_AKZEPTIERT = "ANGEBOT_AKZEPTIERT"
    FAHRZEUG_ABGEHOLT = "FAHRZEUG_ABGEHOLT"
    ABGESCHLOSSEN = "ABGESCHLOSSEN"
    ABGEBROCHEN = "ABGEBROCHEN"


class RestwertAnfrage(Base):
    """Model für Restwertanfragen"""
    __tablename__ = "restwert_anfrage"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="restwert_anfragen")

    # Fahrzeug-Zuordnung
    fahrzeug_id = Column(Integer, ForeignKey("fahrzeug.id"))
    fahrzeug = relationship("Fahrzeug")

    # Status
    status = Column(SQLEnum(RestwertStatus), default=RestwertStatus.ENTWURF)

    # Fahrzeugdaten für Anfrage
    kennzeichen = Column(String(20))
    hersteller = Column(String(100))
    modell = Column(String(100))
    baujahr = Column(Integer)
    erstzulassung = Column(Date)
    kilometerstand = Column(Integer)
    hubraum = Column(Integer)
    leistung_kw = Column(Integer)
    kraftstoff = Column(String(50))
    getriebe = Column(String(50))
    farbe = Column(String(50))
    tueren = Column(Integer)

    # Zustand
    unfallschaden_beschreibung = Column(Text)
    vorschaeden = Column(Boolean, default=False)
    vorschaeden_beschreibung = Column(Text)
    tuev_bis = Column(Date)
    fahrbereit = Column(Boolean, default=False)
    schluessel_vorhanden = Column(Boolean, default=True)
    fahrzeugbrief_vorhanden = Column(Boolean, default=True)

    # Gutachterwerte
    wiederbeschaffungswert = Column(Numeric(12, 2))
    reparaturkosten = Column(Numeric(12, 2))
    restwert_gutachter = Column(Numeric(12, 2))

    # Standort
    standort_plz = Column(String(10))
    standort_ort = Column(String(100))
    standort_adresse = Column(String(200))
    standort_kontakt = Column(String(200))
    standort_telefon = Column(String(50))

    # Besichtigung
    besichtigung_moeglich_ab = Column(Date)
    besichtigung_moeglich_bis = Column(Date)
    besichtigung_zeiten = Column(String(200))

    # Anfrage
    anfrage_gesendet_am = Column(DateTime)
    anfrage_gueltig_bis = Column(Date)
    mindestgebot = Column(Numeric(12, 2))

    # Bilder (IDs der Schadensbilder als JSON)
    bilder_ids_json = Column(Text)

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def status_anzeige(self) -> str:
        """Anzeigetext für Status"""
        return {
            RestwertStatus.ENTWURF: "📝 Entwurf",
            RestwertStatus.ANFRAGE_GESENDET: "📤 Anfrage gesendet",
            RestwertStatus.ANGEBOTE_EINGEGANGEN: "📥 Angebote eingegangen",
            RestwertStatus.ANGEBOT_AKZEPTIERT: "✅ Angebot akzeptiert",
            RestwertStatus.FAHRZEUG_ABGEHOLT: "🚗 Fahrzeug abgeholt",
            RestwertStatus.ABGESCHLOSSEN: "🏁 Abgeschlossen",
            RestwertStatus.ABGEBROCHEN: "❌ Abgebrochen"
        }.get(self.status, "Unbekannt")

    @property
    def bilder_ids(self) -> List[int]:
        """Parsed die Bilder-IDs"""
        try:
            return json.loads(self.bilder_ids_json) if self.bilder_ids_json else []
        except json.JSONDecodeError:
            return []

    @bilder_ids.setter
    def bilder_ids(self, wert: List[int]):
        """Speichert Bilder-IDs als JSON"""
        self.bilder_ids_json = json.dumps(wert)


class RestwertAngebot(Base):
    """Model für eingegangene Restwertangebote"""
    __tablename__ = "restwert_angebot"

    id = Column(Integer, primary_key=True)

    # Anfrage-Zuordnung
    anfrage_id = Column(Integer, ForeignKey("restwert_anfrage.id"), nullable=False)
    anfrage = relationship("RestwertAnfrage", backref="angebote")

    # Anbieter
    anbieter_name = Column(String(200), nullable=False)
    anbieter_firma = Column(String(200))
    anbieter_adresse = Column(String(300))
    anbieter_plz = Column(String(10))
    anbieter_ort = Column(String(100))
    anbieter_telefon = Column(String(50))
    anbieter_email = Column(String(100))

    # Angebot
    gebotener_preis = Column(Numeric(12, 2), nullable=False)
    angebot_gueltig_bis = Column(Date)
    bemerkungen = Column(Text)

    # Konditionen
    abholung_inklusive = Column(Boolean, default=True)
    abholung_kosten = Column(Numeric(10, 2))
    zahlung_bei_abholung = Column(Boolean, default=True)
    zahlungsart = Column(String(100))

    # Status
    ist_akzeptiert = Column(Boolean, default=False)
    akzeptiert_am = Column(DateTime)
    abgelehnt = Column(Boolean, default=False)
    abgelehnt_am = Column(DateTime)
    ablehnungsgrund = Column(Text)

    # Abwicklung
    abholung_datum = Column(Date)
    zahlung_erhalten = Column(Boolean, default=False)
    zahlung_erhalten_am = Column(Date)
    zahlung_betrag = Column(Numeric(12, 2))

    # Metadaten
    eingegangen_am = Column(DateTime, default=datetime.now)

    @property
    def preis_differenz_zum_gutachter(self) -> Optional[Decimal]:
        """Differenz zum Gutachter-Restwert"""
        if self.anfrage and self.anfrage.restwert_gutachter:
            return self.gebotener_preis - self.anfrage.restwert_gutachter
        return None


class RestwertService:
    """Service für Restwertbörsen-Verwaltung"""

    # Liste bekannter Restwertbörsen
    RESTWERBOERSEN = [
        {
            "name": "DAT Restwertbörse",
            "url": "https://www.dat.de",
            "beschreibung": "Deutsche Automobil Treuhand GmbH"
        },
        {
            "name": "Autobid.de",
            "url": "https://www.autobid.de",
            "beschreibung": "Online-Fahrzeughandel"
        },
        {
            "name": "Autorola",
            "url": "https://www.autorola.de",
            "beschreibung": "B2B Remarketing Plattform"
        },
        {
            "name": "CarOnSale",
            "url": "https://www.caronsale.de",
            "beschreibung": "Digitale Fahrzeugbörse"
        }
    ]

    def __init__(self, db_session):
        self.db = db_session

    def anfrage_erstellen(
        self,
        projekt_id: int,
        fahrzeug_id: Optional[int] = None,
        erstellt_von_user_id: Optional[int] = None,
        **kwargs
    ) -> RestwertAnfrage:
        """Erstellt eine neue Restwertanfrage"""

        # Falls Fahrzeug-ID gegeben, Daten übernehmen
        if fahrzeug_id:
            from src.models import Fahrzeug
            fahrzeug = self.db.query(Fahrzeug).get(fahrzeug_id)

            if fahrzeug:
                kwargs.setdefault("kennzeichen", fahrzeug.kennzeichen)
                kwargs.setdefault("hersteller", fahrzeug.hersteller)
                kwargs.setdefault("modell", fahrzeug.modell)
                kwargs.setdefault("erstzulassung", fahrzeug.erstzulassung)
                kwargs.setdefault("hubraum", fahrzeug.hubraum)
                kwargs.setdefault("leistung_kw", fahrzeug.leistung_kw)
                kwargs.setdefault("kraftstoff", fahrzeug.kraftstoff)
                kwargs.setdefault("farbe", fahrzeug.farbe)

        anfrage = RestwertAnfrage(
            projekt_id=projekt_id,
            fahrzeug_id=fahrzeug_id,
            erstellt_von_user_id=erstellt_von_user_id,
            **kwargs
        )

        self.db.add(anfrage)
        self.db.flush()

        return anfrage

    def anfragen_fuer_projekt(self, projekt_id: int) -> List[RestwertAnfrage]:
        """Holt alle Restwertanfragen für ein Projekt"""
        return self.db.query(RestwertAnfrage).filter(
            RestwertAnfrage.projekt_id == projekt_id
        ).order_by(RestwertAnfrage.erstellt_am.desc()).all()

    def angebot_hinzufuegen(
        self,
        anfrage_id: int,
        anbieter_name: str,
        gebotener_preis: Decimal,
        **kwargs
    ) -> RestwertAngebot:
        """Fügt ein Angebot zu einer Anfrage hinzu"""
        anfrage = self.db.query(RestwertAnfrage).get(anfrage_id)

        if not anfrage:
            raise ValueError("Anfrage nicht gefunden")

        angebot = RestwertAngebot(
            anfrage_id=anfrage_id,
            anbieter_name=anbieter_name,
            gebotener_preis=gebotener_preis,
            **kwargs
        )

        self.db.add(angebot)

        # Status der Anfrage aktualisieren
        anfrage.status = RestwertStatus.ANGEBOTE_EINGEGANGEN
        anfrage.aktualisiert_am = datetime.now()

        self.db.flush()

        return angebot

    def angebote_fuer_anfrage(self, anfrage_id: int) -> List[RestwertAngebot]:
        """Holt alle Angebote für eine Anfrage, sortiert nach Preis"""
        return self.db.query(RestwertAngebot).filter(
            RestwertAngebot.anfrage_id == anfrage_id,
            RestwertAngebot.abgelehnt == False
        ).order_by(RestwertAngebot.gebotener_preis.desc()).all()

    def angebot_akzeptieren(self, angebot_id: int) -> Optional[RestwertAngebot]:
        """Akzeptiert ein Angebot"""
        angebot = self.db.query(RestwertAngebot).get(angebot_id)

        if not angebot:
            return None

        # Andere Angebote ablehnen
        andere_angebote = self.db.query(RestwertAngebot).filter(
            RestwertAngebot.anfrage_id == angebot.anfrage_id,
            RestwertAngebot.id != angebot_id
        ).all()

        for anderes in andere_angebote:
            if not anderes.ist_akzeptiert:
                anderes.abgelehnt = True
                anderes.abgelehnt_am = datetime.now()
                anderes.ablehnungsgrund = "Anderes Angebot akzeptiert"

        # Dieses Angebot akzeptieren
        angebot.ist_akzeptiert = True
        angebot.akzeptiert_am = datetime.now()

        # Anfrage-Status aktualisieren
        angebot.anfrage.status = RestwertStatus.ANGEBOT_AKZEPTIERT
        angebot.anfrage.aktualisiert_am = datetime.now()

        self.db.flush()

        return angebot

    def angebot_ablehnen(
        self,
        angebot_id: int,
        grund: Optional[str] = None
    ) -> Optional[RestwertAngebot]:
        """Lehnt ein Angebot ab"""
        angebot = self.db.query(RestwertAngebot).get(angebot_id)

        if not angebot:
            return None

        angebot.abgelehnt = True
        angebot.abgelehnt_am = datetime.now()
        angebot.ablehnungsgrund = grund

        self.db.flush()

        return angebot

    def vergleiche_angebote(self, anfrage_id: int) -> Dict[str, Any]:
        """Erstellt einen Angebotsvergleich"""
        anfrage = self.db.query(RestwertAnfrage).get(anfrage_id)
        angebote = self.angebote_fuer_anfrage(anfrage_id)

        if not angebote:
            return {
                "anzahl_angebote": 0,
                "hoechstes_angebot": None,
                "niedrigstes_angebot": None,
                "durchschnitt": None,
                "differenz_zum_gutachter": None,
                "empfehlung": None
            }

        preise = [float(a.gebotener_preis) for a in angebote]
        hoechstes = max(preise)
        niedrigstes = min(preise)
        durchschnitt = sum(preise) / len(preise)

        hoechstes_angebot = next(a for a in angebote if float(a.gebotener_preis) == hoechstes)

        differenz_zum_gutachter = None
        if anfrage and anfrage.restwert_gutachter:
            differenz_zum_gutachter = hoechstes - float(anfrage.restwert_gutachter)

        # Empfehlung
        if differenz_zum_gutachter and differenz_zum_gutachter > 0:
            empfehlung = f"Höchstes Angebot liegt {differenz_zum_gutachter:.2f} EUR über dem Gutachterwert - Annahme empfohlen"
        elif differenz_zum_gutachter and differenz_zum_gutachter < -500:
            empfehlung = f"Höchstes Angebot liegt {abs(differenz_zum_gutachter):.2f} EUR unter dem Gutachterwert - weitere Angebote einholen"
        else:
            empfehlung = "Höchstes Angebot entspricht etwa dem Gutachterwert"

        return {
            "anzahl_angebote": len(angebote),
            "hoechstes_angebot": {
                "preis": hoechstes,
                "anbieter": hoechstes_angebot.anbieter_name,
                "angebot": hoechstes_angebot
            },
            "niedrigstes_angebot": niedrigstes,
            "durchschnitt": durchschnitt,
            "differenz_zum_gutachter": differenz_zum_gutachter,
            "gutachter_restwert": float(anfrage.restwert_gutachter) if anfrage.restwert_gutachter else None,
            "empfehlung": empfehlung,
            "angebote": angebote
        }

    def generiere_anfrage_text(self, anfrage: RestwertAnfrage) -> str:
        """Generiert einen Anfragetext für manuelle Versendung"""
        text = f"""
RESTWERTANFRAGE
================

Fahrzeugdaten:
- Kennzeichen: {anfrage.kennzeichen or '-'}
- Hersteller/Modell: {anfrage.hersteller or ''} {anfrage.modell or ''}
- Erstzulassung: {anfrage.erstzulassung.strftime('%d.%m.%Y') if anfrage.erstzulassung else '-'}
- Kilometerstand: {anfrage.kilometerstand or '-'} km
- Hubraum: {anfrage.hubraum or '-'} ccm
- Leistung: {anfrage.leistung_kw or '-'} kW
- Kraftstoff: {anfrage.kraftstoff or '-'}
- Getriebe: {anfrage.getriebe or '-'}
- Farbe: {anfrage.farbe or '-'}

Zustand:
- Unfallschaden: {anfrage.unfallschaden_beschreibung or 'Keine Beschreibung'}
- Vorschäden: {'Ja - ' + (anfrage.vorschaeden_beschreibung or '') if anfrage.vorschaeden else 'Nein'}
- TÜV bis: {anfrage.tuev_bis.strftime('%d.%m.%Y') if anfrage.tuev_bis else '-'}
- Fahrbereit: {'Ja' if anfrage.fahrbereit else 'Nein'}
- Schlüssel vorhanden: {'Ja' if anfrage.schluessel_vorhanden else 'Nein'}
- Fahrzeugbrief vorhanden: {'Ja' if anfrage.fahrzeugbrief_vorhanden else 'Nein'}

Gutachterwerte:
- Wiederbeschaffungswert: {anfrage.wiederbeschaffungswert or '-'} EUR
- Reparaturkosten: {anfrage.reparaturkosten or '-'} EUR
- Restwert lt. Gutachter: {anfrage.restwert_gutachter or '-'} EUR

Standort:
{anfrage.standort_adresse or ''}
{anfrage.standort_plz or ''} {anfrage.standort_ort or ''}
Kontakt: {anfrage.standort_kontakt or '-'}
Telefon: {anfrage.standort_telefon or '-'}

Besichtigung möglich:
{anfrage.besichtigung_moeglich_ab.strftime('%d.%m.%Y') if anfrage.besichtigung_moeglich_ab else '-'} bis {anfrage.besichtigung_moeglich_bis.strftime('%d.%m.%Y') if anfrage.besichtigung_moeglich_bis else '-'}
Zeiten: {anfrage.besichtigung_zeiten or 'Nach Vereinbarung'}

Angebotsfrist: {anfrage.anfrage_gueltig_bis.strftime('%d.%m.%Y') if anfrage.anfrage_gueltig_bis else 'Keine Frist'}
{f'Mindestgebot: {anfrage.mindestgebot} EUR' if anfrage.mindestgebot else ''}
"""
        return text

    def abholung_registrieren(
        self,
        angebot_id: int,
        abholung_datum: date
    ) -> Optional[RestwertAngebot]:
        """Registriert die Fahrzeugabholung"""
        angebot = self.db.query(RestwertAngebot).get(angebot_id)

        if not angebot or not angebot.ist_akzeptiert:
            return None

        angebot.abholung_datum = abholung_datum
        angebot.anfrage.status = RestwertStatus.FAHRZEUG_ABGEHOLT
        angebot.anfrage.aktualisiert_am = datetime.now()

        self.db.flush()

        return angebot

    def zahlung_registrieren(
        self,
        angebot_id: int,
        betrag: Decimal,
        zahlungsdatum: Optional[date] = None
    ) -> Optional[RestwertAngebot]:
        """Registriert den Zahlungseingang"""
        angebot = self.db.query(RestwertAngebot).get(angebot_id)

        if not angebot:
            return None

        angebot.zahlung_erhalten = True
        angebot.zahlung_erhalten_am = zahlungsdatum or date.today()
        angebot.zahlung_betrag = betrag

        # Bei vollständiger Abwicklung: Status auf abgeschlossen
        if angebot.abholung_datum:
            angebot.anfrage.status = RestwertStatus.ABGESCHLOSSEN
            angebot.anfrage.aktualisiert_am = datetime.now()

        self.db.flush()

        return angebot
