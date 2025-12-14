"""
Prozessmodul/Klagevorbereitung Service
Verwaltung von Klagen, Schriftsätzen und Gerichtskosten
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Date, Numeric
from sqlalchemy.orm import relationship
from src.models.base import Base


class ProzessStatus(str, Enum):
    """Status eines Prozesses"""
    VORBEREITUNG = "VORBEREITUNG"
    KLAGE_EINGEREICHT = "KLAGE_EINGEREICHT"
    GUETEVERHANDLUNG = "GUETEVERHANDLUNG"
    HAUPTVERHANDLUNG = "HAUPTVERHANDLUNG"
    URTEIL = "URTEIL"
    BERUFUNG = "BERUFUNG"
    RECHTSKRAEFTIG = "RECHTSKRAEFTIG"
    VERGLEICH = "VERGLEICH"
    KLAGE_ZURUECKGENOMMEN = "KLAGE_ZURUECKGENOMMEN"


class SchriftsatzTyp(str, Enum):
    """Typen von Schriftsätzen"""
    KLAGESCHRIFT = "KLAGESCHRIFT"
    KLAGEERWIDERUNG = "KLAGEERWIDERUNG"
    REPLIK = "REPLIK"
    DUPLIK = "DUPLIK"
    BEWEISANTRAG = "BEWEISANTRAG"
    STELLUNGNAHME = "STELLUNGNAHME"
    BERUFUNGSSCHRIFT = "BERUFUNGSSCHRIFT"
    BERUFUNGSERWIDERUNG = "BERUFUNGSERWIDERUNG"
    VERGLEICHSVORSCHLAG = "VERGLEICHSVORSCHLAG"
    KOSTENANTRAG = "KOSTENANTRAG"


class Prozess(Base):
    """Model für Gerichtsprozesse"""
    __tablename__ = "prozess"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="prozesse")

    # Gerichtsdaten
    gericht_name = Column(String(200), nullable=False)
    gericht_adresse = Column(String(500))
    aktenzeichen = Column(String(100))  # Gerichtsaktenzeichen

    # Streitwert
    streitwert = Column(Numeric(12, 2))
    streitwert_begruendung = Column(Text)

    # Status
    status = Column(SQLEnum(ProzessStatus), default=ProzessStatus.VORBEREITUNG)

    # Daten
    klage_eingereicht_am = Column(Date)
    klage_zugestellt_am = Column(Date)
    guetetermin = Column(Date)
    haupttermin = Column(Date)
    urteil_datum = Column(Date)
    rechtskraft_datum = Column(Date)

    # Parteien
    klaeger = Column(String(200))
    beklagter = Column(String(200))
    gegnerischer_anwalt = Column(String(200))
    gegnerischer_anwalt_adresse = Column(String(500))

    # Urteil/Ergebnis
    urteil_zusammenfassung = Column(Text)
    zugesprochener_betrag = Column(Numeric(12, 2))
    kostenquote_klaeger = Column(Integer)  # Prozent
    kostenquote_beklagter = Column(Integer)  # Prozent

    # Risikobewertung
    erfolgsaussicht_prozent = Column(Integer)  # 0-100
    risikobewertung = Column(Text)

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def status_anzeige(self) -> str:
        """Anzeigetext für Status"""
        return {
            ProzessStatus.VORBEREITUNG: "📝 Vorbereitung",
            ProzessStatus.KLAGE_EINGEREICHT: "📤 Klage eingereicht",
            ProzessStatus.GUETEVERHANDLUNG: "🤝 Güteverhandlung",
            ProzessStatus.HAUPTVERHANDLUNG: "⚖️ Hauptverhandlung",
            ProzessStatus.URTEIL: "📜 Urteil ergangen",
            ProzessStatus.BERUFUNG: "📑 Berufung",
            ProzessStatus.RECHTSKRAEFTIG: "✅ Rechtskräftig",
            ProzessStatus.VERGLEICH: "🤝 Vergleich",
            ProzessStatus.KLAGE_ZURUECKGENOMMEN: "❌ Zurückgenommen"
        }.get(self.status, "Unbekannt")


class Schriftsatz(Base):
    """Model für Schriftsätze"""
    __tablename__ = "schriftsatz"

    id = Column(Integer, primary_key=True)

    # Prozess-Zuordnung
    prozess_id = Column(Integer, ForeignKey("prozess.id"), nullable=False)
    prozess = relationship("Prozess", backref="schriftsaetze")

    # Schriftsatz-Daten
    typ = Column(SQLEnum(SchriftsatzTyp), nullable=False)
    titel = Column(String(200), nullable=False)
    inhalt = Column(Text)  # Generierter Text

    # Dokument
    dokument_id = Column(Integer, ForeignKey("dokument.id"))  # Verlinktes Dokument

    # Status
    entwurf = Column(Boolean, default=True)
    eingereicht_am = Column(Date)
    frist_antwort = Column(Date)

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)

    @property
    def typ_anzeige(self) -> str:
        """Anzeigetext für Schriftsatztyp"""
        return {
            SchriftsatzTyp.KLAGESCHRIFT: "Klageschrift",
            SchriftsatzTyp.KLAGEERWIDERUNG: "Klageerwiderung",
            SchriftsatzTyp.REPLIK: "Replik",
            SchriftsatzTyp.DUPLIK: "Duplik",
            SchriftsatzTyp.BEWEISANTRAG: "Beweisantrag",
            SchriftsatzTyp.STELLUNGNAHME: "Stellungnahme",
            SchriftsatzTyp.BERUFUNGSSCHRIFT: "Berufungsschrift",
            SchriftsatzTyp.BERUFUNGSERWIDERUNG: "Berufungserwiderung",
            SchriftsatzTyp.VERGLEICHSVORSCHLAG: "Vergleichsvorschlag",
            SchriftsatzTyp.KOSTENANTRAG: "Kostenantrag"
        }.get(self.typ, "Schriftsatz")


class ProzessService:
    """Service für Prozessverwaltung"""

    # Gerichtskostentabelle (GKG) - vereinfacht
    GERICHTSKOSTEN_TABELLE = [
        (500, 38),
        (1000, 58),
        (1500, 78),
        (2000, 98),
        (3000, 119),
        (4000, 140),
        (5000, 161),
        (6000, 182),
        (7000, 203),
        (8000, 224),
        (9000, 245),
        (10000, 266),
        (13000, 295),
        (16000, 324),
        (19000, 353),
        (22000, 382),
        (25000, 411),
        (30000, 449),
        (35000, 487),
        (40000, 525),
        (45000, 563),
        (50000, 601),
        (65000, 733),
        (80000, 865),
        (95000, 997),
        (110000, 1129),
        (125000, 1261),
        (140000, 1393),
        (155000, 1525),
        (170000, 1657),
        (185000, 1789),
        (200000, 1921),
    ]

    def __init__(self, db_session):
        self.db = db_session

    def prozess_erstellen(
        self,
        projekt_id: int,
        gericht_name: str,
        streitwert: Decimal,
        klaeger: str,
        beklagter: str,
        erstellt_von_user_id: Optional[int] = None,
        **kwargs
    ) -> Prozess:
        """Erstellt einen neuen Prozess"""
        prozess = Prozess(
            projekt_id=projekt_id,
            gericht_name=gericht_name,
            streitwert=streitwert,
            klaeger=klaeger,
            beklagter=beklagter,
            erstellt_von_user_id=erstellt_von_user_id,
            **kwargs
        )
        self.db.add(prozess)
        self.db.flush()
        return prozess

    def prozesse_fuer_projekt(self, projekt_id: int) -> List[Prozess]:
        """Holt alle Prozesse für ein Projekt"""
        return self.db.query(Prozess).filter(
            Prozess.projekt_id == projekt_id
        ).order_by(Prozess.erstellt_am.desc()).all()

    def schriftsatz_erstellen(
        self,
        prozess_id: int,
        typ: SchriftsatzTyp,
        titel: str,
        inhalt: Optional[str] = None,
        erstellt_von_user_id: Optional[int] = None
    ) -> Schriftsatz:
        """Erstellt einen neuen Schriftsatz"""
        schriftsatz = Schriftsatz(
            prozess_id=prozess_id,
            typ=typ,
            titel=titel,
            inhalt=inhalt,
            erstellt_von_user_id=erstellt_von_user_id
        )
        self.db.add(schriftsatz)
        self.db.flush()
        return schriftsatz

    def berechne_gerichtskosten(self, streitwert: Decimal) -> Dict[str, Any]:
        """Berechnet Gerichtskosten nach GKG"""
        streitwert_float = float(streitwert)

        # Finde passende Gebühr
        gebuehr = 38  # Mindestgebühr
        for grenze, kosten in self.GERICHTSKOSTEN_TABELLE:
            if streitwert_float <= grenze:
                gebuehr = kosten
                break
        else:
            # Über 200.000 EUR
            ueberschuss = streitwert_float - 200000
            zusatz_stufen = int(ueberschuss / 50000) + 1
            gebuehr = 1921 + (zusatz_stufen * 198)

        # Verschiedene Gebührentypen
        return {
            "streitwert": streitwert_float,
            "einfache_gebuehr": gebuehr,
            "gerichtskosten_vorschuss": gebuehr * 3,  # 3-fache Gebühr als Vorschuss
            "verfahrensgebuehr": gebuehr * 3,
            "beweisaufnahme": gebuehr * 1,  # Optional bei Beweisaufnahme
            "vergleichsgebuehr": 0,  # Bei Vergleich werden Gebühren ermäßigt
            "hinweis": "Die tatsächlichen Kosten können je nach Verfahrensverlauf variieren."
        }

    def berechne_prozessrisiko(
        self,
        streitwert: Decimal,
        erfolgsaussicht_prozent: int,
        eigene_anwaltskosten: Decimal,
        gegnerische_anwaltskosten: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Berechnet das finanzielle Prozessrisiko"""
        if gegnerische_anwaltskosten is None:
            gegnerische_anwaltskosten = eigene_anwaltskosten

        gerichtskosten = self.berechne_gerichtskosten(streitwert)
        gk_vorschuss = Decimal(str(gerichtskosten["gerichtskosten_vorschuss"]))

        # Szenarien
        erfolg_wahrsch = Decimal(str(erfolgsaussicht_prozent)) / 100
        niederlage_wahrsch = 1 - erfolg_wahrsch

        # Bei Erfolg: Streitwert gewonnen, Kosten vom Gegner
        gewinn_bei_erfolg = streitwert

        # Bei Niederlage: Eigene + gegnerische Kosten + Gerichtskosten
        verlust_bei_niederlage = eigene_anwaltskosten + gegnerische_anwaltskosten + gk_vorschuss

        # Erwartungswert
        erwartungswert = (erfolg_wahrsch * gewinn_bei_erfolg) - (niederlage_wahrsch * verlust_bei_niederlage)

        # Empfehlung
        if erwartungswert > streitwert * Decimal("0.3"):
            empfehlung = "Klage empfohlen - Gute Erfolgsaussichten"
            ampel = "gruen"
        elif erwartungswert > 0:
            empfehlung = "Klage möglich - Abwägung erforderlich"
            ampel = "gelb"
        else:
            empfehlung = "Klage riskant - Vergleichsverhandlung empfohlen"
            ampel = "rot"

        return {
            "streitwert": float(streitwert),
            "erfolgsaussicht_prozent": erfolgsaussicht_prozent,
            "gerichtskosten_vorschuss": float(gk_vorschuss),
            "eigene_anwaltskosten": float(eigene_anwaltskosten),
            "gegnerische_anwaltskosten": float(gegnerische_anwaltskosten),
            "gewinn_bei_erfolg": float(gewinn_bei_erfolg),
            "verlust_bei_niederlage": float(verlust_bei_niederlage),
            "erwartungswert": float(erwartungswert),
            "empfehlung": empfehlung,
            "ampel": ampel
        }

    def generiere_klageschrift(self, prozess: Prozess, projekt: Any) -> str:
        """Generiert einen Klageschrift-Entwurf"""
        datum_heute = date.today().strftime("%d.%m.%Y")

        klageschrift = f"""
An das
{prozess.gericht_name}
{prozess.gericht_adresse or "[Adresse des Gerichts]"}

{datum_heute}

KLAGESCHRIFT

In Sachen

{prozess.klaeger}
- Kläger -

Prozessbevollmächtigte: [Kanzlei-Daten]

gegen

{prozess.beklagter}
- Beklagte -

wegen: Schadensersatz aus Verkehrsunfall

Streitwert: {prozess.streitwert:,.2f} EUR

---

Namens und in Vollmacht des Klägers erhebe ich Klage und beantrage:

1. Die Beklagte wird verurteilt, an den Kläger {prozess.streitwert:,.2f} EUR nebst Zinsen
   in Höhe von 5 Prozentpunkten über dem Basiszinssatz seit Rechtshängigkeit zu zahlen.

2. Die Beklagte trägt die Kosten des Rechtsstreits.

3. Das Urteil ist vorläufig vollstreckbar.

---

BEGRÜNDUNG

I. Sachverhalt

Am [UNFALLDATUM] ereignete sich ein Verkehrsunfall an der [UNFALLORT].

[UNFALLHERGANG BESCHREIBUNG]

Der Kläger ist Eigentümer/Halter des Fahrzeugs mit dem amtlichen Kennzeichen
[KENNZEICHEN EIGENES FAHRZEUG].

II. Haftung

Die Beklagte haftet dem Kläger aus §§ 7, 17 StVG, § 115 VVG für den entstandenen Schaden.

[HAFTUNGSBEGRÜNDUNG]

Die Alleinhaftung der Beklagten ergibt sich aus [BEGRÜNDUNG].

III. Schaden

Dem Kläger ist folgender Schaden entstanden:

[KOSTENAUFSTELLUNG]

Summe: {prozess.streitwert:,.2f} EUR

IV. Zinsen

Der Zinsanspruch ergibt sich aus §§ 288, 291 BGB.

---

[ORT], den {datum_heute}

_____________________
Rechtsanwalt/Rechtsanwältin
"""
        return klageschrift

    def generiere_beweisantrag(self, prozess: Prozess, beweisthemen: List[str]) -> str:
        """Generiert einen Beweisantrag"""
        datum_heute = date.today().strftime("%d.%m.%Y")

        beweismittel_text = ""
        for i, thema in enumerate(beweisthemen, 1):
            beweismittel_text += f"\n{i}. {thema}"

        antrag = f"""
An das
{prozess.gericht_name}

Az.: {prozess.aktenzeichen or "[Aktenzeichen]"}

{datum_heute}

In Sachen {prozess.klaeger} ./. {prozess.beklagter}

BEWEISANTRAG

Der Kläger beantragt Beweis zu erheben über folgende Tatsachen:
{beweismittel_text}

durch:

□ Einholung eines Sachverständigengutachtens
□ Vernehmung des Zeugen [NAME, ANSCHRIFT]
□ Parteivernehmung
□ Augenscheinseinnahme
□ Urkundenbeweis

BEGRÜNDUNG

[Begründung des Beweisantrags]

---

[ORT], den {datum_heute}

_____________________
Rechtsanwalt/Rechtsanwältin
"""
        return antrag
