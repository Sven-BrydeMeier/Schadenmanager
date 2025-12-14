"""
Vergleichsrechner Service
Berechnung und Dokumentation von Vergleichsangeboten
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Date, Numeric
from sqlalchemy.orm import relationship
from src.models.base import Base


class VergleichsStatus(str, Enum):
    """Status eines Vergleichs"""
    ENTWURF = "ENTWURF"
    ANGEBOT_ERHALTEN = "ANGEBOT_ERHALTEN"
    GEGENANGEBOT = "GEGENANGEBOT"
    IN_VERHANDLUNG = "IN_VERHANDLUNG"
    ANGENOMMEN = "ANGENOMMEN"
    ABGELEHNT = "ABGELEHNT"
    GESCHLOSSEN = "GESCHLOSSEN"


class Vergleichsangebot(Base):
    """Model für Vergleichsangebote"""
    __tablename__ = "vergleichsangebot"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="vergleichsangebote")

    # Angebotsdaten
    bezeichnung = Column(String(200))
    status = Column(SQLEnum(VergleichsStatus), default=VergleichsStatus.ENTWURF)

    # Angebot von
    angebot_von = Column(String(100))  # "Versicherung", "Mandant", "Gegner"
    angebot_datum = Column(Date)
    gueltig_bis = Column(Date)

    # Beträge - Ursprüngliche Forderung
    urspruengliche_forderung = Column(Numeric(12, 2))
    forderung_positionen_json = Column(Text)

    # Beträge - Vergleichsangebot
    angebotsbetrag = Column(Numeric(12, 2))
    angebot_positionen_json = Column(Text)

    # Berechnung
    differenz_absolut = Column(Numeric(12, 2))
    differenz_prozent = Column(Numeric(5, 2))
    ersparnis_prozesskosten = Column(Numeric(12, 2))

    # Bewertung
    empfehlung = Column(String(50))  # "annehmen", "ablehnen", "verhandeln"
    begruendung = Column(Text)
    risikobewertung = Column(Text)

    # Entscheidung
    entscheidung = Column(String(50))  # "angenommen", "abgelehnt"
    entscheidung_am = Column(DateTime)
    entscheidung_von_user_id = Column(Integer, ForeignKey("user.id"))
    entscheidung_begruendung = Column(Text)

    # Dokumente
    vergleichsvereinbarung_dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def forderung_positionen(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.forderung_positionen_json) if self.forderung_positionen_json else []
        except json.JSONDecodeError:
            return []

    @forderung_positionen.setter
    def forderung_positionen(self, wert: List[Dict[str, Any]]):
        self.forderung_positionen_json = json.dumps(wert)

    @property
    def angebot_positionen(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.angebot_positionen_json) if self.angebot_positionen_json else []
        except json.JSONDecodeError:
            return []

    @angebot_positionen.setter
    def angebot_positionen(self, wert: List[Dict[str, Any]]):
        self.angebot_positionen_json = json.dumps(wert)

    @property
    def status_anzeige(self) -> str:
        return {
            VergleichsStatus.ENTWURF: "📝 Entwurf",
            VergleichsStatus.ANGEBOT_ERHALTEN: "📥 Angebot erhalten",
            VergleichsStatus.GEGENANGEBOT: "📤 Gegenangebot",
            VergleichsStatus.IN_VERHANDLUNG: "🤝 In Verhandlung",
            VergleichsStatus.ANGENOMMEN: "✅ Angenommen",
            VergleichsStatus.ABGELEHNT: "❌ Abgelehnt",
            VergleichsStatus.GESCHLOSSEN: "🔒 Geschlossen"
        }.get(self.status, "Unbekannt")


class VergleichsService:
    """Service für Vergleichsberechnungen"""

    def __init__(self, db_session):
        self.db = db_session

    def vergleich_erstellen(
        self,
        projekt_id: int,
        urspruengliche_forderung: Decimal,
        forderung_positionen: List[Dict[str, Any]],
        angebotsbetrag: Decimal,
        angebot_positionen: Optional[List[Dict[str, Any]]] = None,
        angebot_von: str = "Versicherung",
        bezeichnung: Optional[str] = None,
        erstellt_von_user_id: Optional[int] = None
    ) -> Vergleichsangebot:
        """Erstellt ein neues Vergleichsangebot mit Berechnung"""

        # Differenzen berechnen
        differenz_absolut = urspruengliche_forderung - angebotsbetrag
        differenz_prozent = (differenz_absolut / urspruengliche_forderung * 100) if urspruengliche_forderung > 0 else Decimal("0")

        # Prozesskostenersparnis schätzen
        ersparnis = self._berechne_prozesskosten_ersparnis(urspruengliche_forderung)

        # Empfehlung generieren
        empfehlung, begruendung = self._generiere_empfehlung(
            urspruengliche_forderung, angebotsbetrag, differenz_prozent, ersparnis
        )

        vergleich = Vergleichsangebot(
            projekt_id=projekt_id,
            bezeichnung=bezeichnung or f"Vergleichsangebot vom {date.today().strftime('%d.%m.%Y')}",
            status=VergleichsStatus.ANGEBOT_ERHALTEN,
            angebot_von=angebot_von,
            angebot_datum=date.today(),
            urspruengliche_forderung=urspruengliche_forderung,
            angebotsbetrag=angebotsbetrag,
            differenz_absolut=differenz_absolut,
            differenz_prozent=differenz_prozent,
            ersparnis_prozesskosten=ersparnis,
            empfehlung=empfehlung,
            begruendung=begruendung,
            erstellt_von_user_id=erstellt_von_user_id
        )

        vergleich.forderung_positionen = forderung_positionen
        if angebot_positionen:
            vergleich.angebot_positionen = angebot_positionen

        self.db.add(vergleich)
        self.db.flush()

        return vergleich

    def _berechne_prozesskosten_ersparnis(self, streitwert: Decimal) -> Decimal:
        """Schätzt die Prozesskostenersparnis bei Vergleich"""
        # Vereinfachte Schätzung: Ca. 15-20% des Streitwerts für beide Seiten
        # (Gerichtskosten + 2x Anwaltskosten)
        return streitwert * Decimal("0.18")

    def _generiere_empfehlung(
        self,
        forderung: Decimal,
        angebot: Decimal,
        differenz_prozent: Decimal,
        prozesskosten_ersparnis: Decimal
    ) -> tuple:
        """Generiert eine Empfehlung für das Vergleichsangebot"""

        # Netto-Differenz unter Berücksichtigung der Prozesskosten
        netto_differenz = forderung - angebot - (prozesskosten_ersparnis / 2)  # Halbe Ersparnis für Mandant

        if differenz_prozent <= Decimal("10"):
            empfehlung = "annehmen"
            begruendung = f"""
**Empfehlung: Vergleich annehmen**

Das Angebot liegt nur {differenz_prozent:.1f}% unter der ursprünglichen Forderung.

**Vorteile der Annahme:**
- Sofortige Zahlung
- Keine Prozesskosten (geschätzte Ersparnis: {prozesskosten_ersparnis:.2f} EUR)
- Kein Prozessrisiko
- Zeitersparnis

**Netto-Betrachtung:**
Bei einem Prozess würden ca. {prozesskosten_ersparnis/2:.2f} EUR an eigenen Kosten entstehen.
Der effektive Unterschied zum Prozess beträgt damit nur ca. {netto_differenz:.2f} EUR.
"""
        elif differenz_prozent <= Decimal("25"):
            empfehlung = "verhandeln"
            begruendung = f"""
**Empfehlung: Nachverhandeln**

Das Angebot liegt {differenz_prozent:.1f}% unter der ursprünglichen Forderung.
Eine Nachverhandlung erscheint sinnvoll.

**Vorgeschlagenes Gegenangebot:**
Empfehlung: {(forderung * Decimal('0.9')):.2f} EUR (10% Nachlass)

**Argumente für die Verhandlung:**
- Kosten sind belegt und angemessen
- Angebot berücksichtigt nicht alle Positionen
- Prozessrisiko für Versicherung höher

**Prozesskosten-Betrachtung:**
Geschätzte Prozesskosten: {prozesskosten_ersparnis:.2f} EUR
Bei Obsiegen: Volle Erstattung
Bei Unterliegen: Doppelte Kosten
"""
        else:
            empfehlung = "ablehnen"
            begruendung = f"""
**Empfehlung: Angebot ablehnen**

Das Angebot liegt {differenz_prozent:.1f}% unter der ursprünglichen Forderung.
Dies entspricht nicht einer fairen Regulierung.

**Gründe für Ablehnung:**
- Unangemessen niedriges Angebot
- Differenz von {forderung - angebot:.2f} EUR zu groß
- Selbst bei Prozessrisiko bessere Aussichten

**Empfohlenes Vorgehen:**
1. Schriftliche Ablehnung mit Begründung
2. Fristsetzung für angemessenes Angebot (2 Wochen)
3. Bei Ablehnung: Klageerhebung vorbereiten

**Prozessrisikoabwägung:**
Bei 60% Erfolgsaussicht ist der Erwartungswert höher als das Angebot.
"""

        return empfehlung, begruendung

    def vergleiche_fuer_projekt(self, projekt_id: int) -> List[Vergleichsangebot]:
        """Holt alle Vergleichsangebote für ein Projekt"""
        return self.db.query(Vergleichsangebot).filter(
            Vergleichsangebot.projekt_id == projekt_id
        ).order_by(Vergleichsangebot.erstellt_am.desc()).all()

    def vergleich_annehmen(
        self,
        vergleich_id: int,
        user_id: int,
        begruendung: Optional[str] = None
    ) -> Optional[Vergleichsangebot]:
        """Nimmt ein Vergleichsangebot an"""
        vergleich = self.db.query(Vergleichsangebot).get(vergleich_id)

        if vergleich:
            vergleich.status = VergleichsStatus.ANGENOMMEN
            vergleich.entscheidung = "angenommen"
            vergleich.entscheidung_am = datetime.now()
            vergleich.entscheidung_von_user_id = user_id
            vergleich.entscheidung_begruendung = begruendung
            self.db.flush()

        return vergleich

    def vergleich_ablehnen(
        self,
        vergleich_id: int,
        user_id: int,
        begruendung: Optional[str] = None
    ) -> Optional[Vergleichsangebot]:
        """Lehnt ein Vergleichsangebot ab"""
        vergleich = self.db.query(Vergleichsangebot).get(vergleich_id)

        if vergleich:
            vergleich.status = VergleichsStatus.ABGELEHNT
            vergleich.entscheidung = "abgelehnt"
            vergleich.entscheidung_am = datetime.now()
            vergleich.entscheidung_von_user_id = user_id
            vergleich.entscheidung_begruendung = begruendung
            self.db.flush()

        return vergleich

    def erstelle_gegenangebot(
        self,
        original_vergleich_id: int,
        neuer_betrag: Decimal,
        begruendung: str,
        erstellt_von_user_id: Optional[int] = None
    ) -> Optional[Vergleichsangebot]:
        """Erstellt ein Gegenangebot basierend auf einem erhaltenen Angebot"""
        original = self.db.query(Vergleichsangebot).get(original_vergleich_id)

        if not original:
            return None

        # Original auf "In Verhandlung" setzen
        original.status = VergleichsStatus.IN_VERHANDLUNG

        # Neues Gegenangebot erstellen
        gegenangebot = Vergleichsangebot(
            projekt_id=original.projekt_id,
            bezeichnung=f"Gegenangebot zu {original.bezeichnung}",
            status=VergleichsStatus.GEGENANGEBOT,
            angebot_von="Mandant",
            angebot_datum=date.today(),
            urspruengliche_forderung=original.urspruengliche_forderung,
            angebotsbetrag=neuer_betrag,
            begruendung=begruendung,
            erstellt_von_user_id=erstellt_von_user_id
        )

        gegenangebot.forderung_positionen = original.forderung_positionen

        # Differenz berechnen
        gegenangebot.differenz_absolut = original.urspruengliche_forderung - neuer_betrag
        if original.urspruengliche_forderung > 0:
            gegenangebot.differenz_prozent = (gegenangebot.differenz_absolut / original.urspruengliche_forderung * 100)

        self.db.add(gegenangebot)
        self.db.flush()

        return gegenangebot

    def generiere_vergleichsvereinbarung(self, vergleich: Vergleichsangebot) -> str:
        """Generiert einen Text für eine Vergleichsvereinbarung"""
        text = f"""
VERGLEICHSVEREINBARUNG

Zwischen

[Geschädigter/Mandant]
- nachfolgend "Anspruchsteller" genannt -

und

{vergleich.angebot_von or "[Versicherung/Schädiger]"}
- nachfolgend "Anspruchsgegner" genannt -

wird folgende Vereinbarung geschlossen:

§ 1 Gegenstand

Die Parteien streiten über Schadensersatzansprüche aus dem Verkehrsunfall
vom [Unfalldatum].

Der Anspruchsteller macht folgende Forderungen geltend:
{vergleich.urspruengliche_forderung:,.2f} EUR

Der Anspruchsgegner bietet zur Abgeltung aller Ansprüche:
{vergleich.angebotsbetrag:,.2f} EUR

§ 2 Vergleich

Zur Beilegung des Rechtsstreits vereinbaren die Parteien:

1. Der Anspruchsgegner zahlt an den Anspruchsteller einen Betrag von
   {vergleich.angebotsbetrag:,.2f} EUR (in Worten: [BETRAG IN WORTEN] Euro).

2. Mit Zahlung dieses Betrages sind sämtliche Ansprüche des Anspruchstellers
   aus dem streitgegenständlichen Unfallereignis abgegolten und erledigt.

3. Die Zahlung erfolgt innerhalb von 14 Tagen nach Unterzeichnung dieser
   Vereinbarung auf das Konto:
   IBAN: [IBAN]
   BIC: [BIC]

§ 3 Ausgleichsklausel

Mit Erfüllung dieser Vereinbarung sind sämtliche gegenseitigen Ansprüche
der Parteien aus dem streitgegenständlichen Unfallereignis, gleich aus
welchem Rechtsgrund, abgegolten. Dies gilt auch für derzeit unbekannte
Ansprüche.

§ 4 Kosten

Jede Partei trägt ihre eigenen außergerichtlichen Kosten.

§ 5 Schlussbestimmungen

Diese Vereinbarung enthält alle Abreden der Parteien. Änderungen und
Ergänzungen bedürfen der Schriftform.

___________________                    ___________________
Ort, Datum                             Ort, Datum

___________________                    ___________________
Anspruchsteller                        Anspruchsgegner
"""
        return text

    def vergleichs_statistik(self, projekt_id: Optional[int] = None) -> Dict[str, Any]:
        """Erstellt Statistiken zu Vergleichen"""
        query = self.db.query(Vergleichsangebot)

        if projekt_id:
            query = query.filter(Vergleichsangebot.projekt_id == projekt_id)

        vergleiche = query.all()

        if not vergleiche:
            return {"anzahl": 0}

        angenommene = [v for v in vergleiche if v.status == VergleichsStatus.ANGENOMMEN]
        abgelehnte = [v for v in vergleiche if v.status == VergleichsStatus.ABGELEHNT]

        durchschnittliche_differenz = sum(
            float(v.differenz_prozent or 0) for v in vergleiche
        ) / len(vergleiche) if vergleiche else 0

        return {
            "anzahl": len(vergleiche),
            "angenommen": len(angenommene),
            "abgelehnt": len(abgelehnte),
            "in_verhandlung": len([v for v in vergleiche if v.status == VergleichsStatus.IN_VERHANDLUNG]),
            "durchschnittliche_differenz_prozent": durchschnittliche_differenz,
            "gesamtvolumen_forderungen": sum(float(v.urspruengliche_forderung or 0) for v in vergleiche),
            "gesamtvolumen_vergleiche": sum(float(v.angebotsbetrag or 0) for v in angenommene)
        }
