"""
Terminkalender/Gerichtstermine Service
Verwaltung von Terminen mit Kalenderansicht und iCal-Export
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Date, Time
from sqlalchemy.orm import relationship
from src.models.base import Base


class TerminTyp(str, Enum):
    """Typen von Terminen"""
    GERICHTSTERMIN = "GERICHTSTERMIN"
    GUTACHTERTERMIN = "GUTACHTERTERMIN"
    MANDANTENBESPRECHUNG = "MANDANTENBESPRECHUNG"
    WERKSTATTTERMIN = "WERKSTATTTERMIN"
    VERSICHERUNGSTERMIN = "VERSICHERUNGSTERMIN"
    ORTSBESICHTIGUNG = "ORTSBESICHTIGUNG"
    TELEFONTERMIN = "TELEFONTERMIN"
    FRIST = "FRIST"
    SONSTIGER = "SONSTIGER"


class TerminStatus(str, Enum):
    """Status eines Termins"""
    GEPLANT = "GEPLANT"
    BESTAETIGT = "BESTAETIGT"
    VERSCHOBEN = "VERSCHOBEN"
    ABGESAGT = "ABGESAGT"
    WAHRGENOMMEN = "WAHRGENOMMEN"


class Termin(Base):
    """Model für Termine"""
    __tablename__ = "termin"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="termine")

    # Termin-Daten
    titel = Column(String(200), nullable=False)
    beschreibung = Column(Text)
    termin_typ = Column(SQLEnum(TerminTyp), default=TerminTyp.SONSTIGER)
    status = Column(SQLEnum(TerminStatus), default=TerminStatus.GEPLANT)

    # Datum und Zeit
    datum = Column(Date, nullable=False)
    uhrzeit_von = Column(Time)
    uhrzeit_bis = Column(Time)
    ganztaegig = Column(Boolean, default=False)

    # Ort
    ort = Column(String(300))
    adresse = Column(String(500))
    online_link = Column(String(500))  # Für Video-Calls

    # Gericht (bei Gerichtsterminen)
    gericht_name = Column(String(200))
    gericht_aktenzeichen = Column(String(100))
    gericht_saal = Column(String(50))

    # Teilnehmer
    teilnehmer_intern = Column(Text)  # JSON-Liste interner Teilnehmer
    teilnehmer_extern = Column(Text)  # JSON-Liste externer Teilnehmer

    # Erinnerungen
    erinnerung_minuten = Column(Integer, default=60)  # Minuten vor Termin
    erinnerung_gesendet = Column(Boolean, default=False)

    # Notizen
    vorbereitungsnotizen = Column(Text)
    nachbereitungsnotizen = Column(Text)

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def termin_typ_anzeige(self) -> str:
        """Anzeigetext für Termintyp"""
        return {
            TerminTyp.GERICHTSTERMIN: "Gerichtstermin",
            TerminTyp.GUTACHTERTERMIN: "Gutachtertermin",
            TerminTyp.MANDANTENBESPRECHUNG: "Mandantenbesprechung",
            TerminTyp.WERKSTATTTERMIN: "Werkstatttermin",
            TerminTyp.VERSICHERUNGSTERMIN: "Versicherungstermin",
            TerminTyp.ORTSBESICHTIGUNG: "Ortsbesichtigung",
            TerminTyp.TELEFONTERMIN: "Telefontermin",
            TerminTyp.FRIST: "Frist",
            TerminTyp.SONSTIGER: "Sonstiger Termin"
        }.get(self.termin_typ, "Termin")

    @property
    def status_anzeige(self) -> str:
        """Anzeigetext für Status"""
        return {
            TerminStatus.GEPLANT: "🟡 Geplant",
            TerminStatus.BESTAETIGT: "🟢 Bestätigt",
            TerminStatus.VERSCHOBEN: "🟠 Verschoben",
            TerminStatus.ABGESAGT: "🔴 Abgesagt",
            TerminStatus.WAHRGENOMMEN: "✅ Wahrgenommen"
        }.get(self.status, "Unbekannt")

    @property
    def ist_heute(self) -> bool:
        """Prüft ob der Termin heute ist"""
        return self.datum == date.today()

    @property
    def ist_vergangen(self) -> bool:
        """Prüft ob der Termin vergangen ist"""
        return self.datum < date.today()

    @property
    def tage_bis_termin(self) -> int:
        """Berechnet Tage bis zum Termin"""
        return (self.datum - date.today()).days


class KalenderService:
    """Service für Kalenderverwaltung"""

    def __init__(self, db_session):
        self.db = db_session

    def termin_erstellen(
        self,
        projekt_id: int,
        titel: str,
        datum: date,
        termin_typ: TerminTyp = TerminTyp.SONSTIGER,
        uhrzeit_von: Optional[Any] = None,
        uhrzeit_bis: Optional[Any] = None,
        ganztaegig: bool = False,
        ort: Optional[str] = None,
        beschreibung: Optional[str] = None,
        erstellt_von_user_id: Optional[int] = None,
        **kwargs
    ) -> Termin:
        """Erstellt einen neuen Termin"""
        termin = Termin(
            projekt_id=projekt_id,
            titel=titel,
            datum=datum,
            termin_typ=termin_typ,
            uhrzeit_von=uhrzeit_von,
            uhrzeit_bis=uhrzeit_bis,
            ganztaegig=ganztaegig,
            ort=ort,
            beschreibung=beschreibung,
            erstellt_von_user_id=erstellt_von_user_id,
            **kwargs
        )
        self.db.add(termin)
        self.db.flush()
        return termin

    def termine_fuer_projekt(self, projekt_id: int) -> List[Termin]:
        """Holt alle Termine für ein Projekt"""
        return self.db.query(Termin).filter(
            Termin.projekt_id == projekt_id
        ).order_by(Termin.datum, Termin.uhrzeit_von).all()

    def termine_fuer_zeitraum(
        self,
        start_datum: date,
        end_datum: date,
        projekt_id: Optional[int] = None
    ) -> List[Termin]:
        """Holt alle Termine für einen Zeitraum"""
        query = self.db.query(Termin).filter(
            Termin.datum >= start_datum,
            Termin.datum <= end_datum,
            Termin.status.notin_([TerminStatus.ABGESAGT])
        )

        if projekt_id:
            query = query.filter(Termin.projekt_id == projekt_id)

        return query.order_by(Termin.datum, Termin.uhrzeit_von).all()

    def anstehende_termine(self, tage: int = 7, projekt_id: Optional[int] = None) -> List[Termin]:
        """Holt anstehende Termine der nächsten X Tage"""
        heute = date.today()
        end_datum = heute + timedelta(days=tage)
        return self.termine_fuer_zeitraum(heute, end_datum, projekt_id)

    def heute_termine(self, projekt_id: Optional[int] = None) -> List[Termin]:
        """Holt alle Termine für heute"""
        heute = date.today()
        return self.termine_fuer_zeitraum(heute, heute, projekt_id)

    def gerichtstermine(self, projekt_id: Optional[int] = None) -> List[Termin]:
        """Holt alle Gerichtstermine"""
        query = self.db.query(Termin).filter(
            Termin.termin_typ == TerminTyp.GERICHTSTERMIN,
            Termin.status.notin_([TerminStatus.ABGESAGT])
        )

        if projekt_id:
            query = query.filter(Termin.projekt_id == projekt_id)

        return query.order_by(Termin.datum).all()

    def termin_aktualisieren(self, termin_id: int, **kwargs) -> Optional[Termin]:
        """Aktualisiert einen Termin"""
        termin = self.db.query(Termin).get(termin_id)
        if termin:
            for key, value in kwargs.items():
                if hasattr(termin, key):
                    setattr(termin, key, value)
            termin.aktualisiert_am = datetime.now()
            self.db.flush()
        return termin

    def termin_loeschen(self, termin_id: int) -> bool:
        """Löscht einen Termin"""
        termin = self.db.query(Termin).get(termin_id)
        if termin:
            self.db.delete(termin)
            self.db.flush()
            return True
        return False

    def generiere_ical(self, termine: List[Termin]) -> str:
        """Generiert iCal-Format für Export"""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Schadenmanager//Kalender//DE",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH"
        ]

        for termin in termine:
            lines.append("BEGIN:VEVENT")

            # UID
            lines.append(f"UID:termin-{termin.id}@schadenmanager")

            # Datum/Zeit
            if termin.ganztaegig:
                lines.append(f"DTSTART;VALUE=DATE:{termin.datum.strftime('%Y%m%d')}")
                lines.append(f"DTEND;VALUE=DATE:{(termin.datum + timedelta(days=1)).strftime('%Y%m%d')}")
            else:
                if termin.uhrzeit_von:
                    dt_start = datetime.combine(termin.datum, termin.uhrzeit_von)
                    lines.append(f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}")

                    if termin.uhrzeit_bis:
                        dt_end = datetime.combine(termin.datum, termin.uhrzeit_bis)
                        lines.append(f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}")

            # Details
            lines.append(f"SUMMARY:{termin.titel}")

            if termin.beschreibung:
                lines.append(f"DESCRIPTION:{termin.beschreibung.replace(chr(10), '\\n')}")

            if termin.ort:
                lines.append(f"LOCATION:{termin.ort}")

            # Erinnerung
            if termin.erinnerung_minuten:
                lines.append("BEGIN:VALARM")
                lines.append("ACTION:DISPLAY")
                lines.append(f"TRIGGER:-PT{termin.erinnerung_minuten}M")
                lines.append(f"DESCRIPTION:Erinnerung: {termin.titel}")
                lines.append("END:VALARM")

            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    def kalender_wochen_uebersicht(self, start_datum: date) -> Dict[str, List[Termin]]:
        """Erstellt eine Wochenübersicht mit Terminen pro Tag"""
        end_datum = start_datum + timedelta(days=6)
        termine = self.termine_fuer_zeitraum(start_datum, end_datum)

        wochen_uebersicht = {}
        for i in range(7):
            tag = start_datum + timedelta(days=i)
            tag_key = tag.strftime("%Y-%m-%d")
            wochen_uebersicht[tag_key] = [
                t for t in termine if t.datum == tag
            ]

        return wochen_uebersicht

    def kalender_monats_uebersicht(self, jahr: int, monat: int) -> Dict[str, List[Termin]]:
        """Erstellt eine Monatsübersicht mit Terminen pro Tag"""
        import calendar

        _, letzter_tag = calendar.monthrange(jahr, monat)
        start_datum = date(jahr, monat, 1)
        end_datum = date(jahr, monat, letzter_tag)

        termine = self.termine_fuer_zeitraum(start_datum, end_datum)

        monats_uebersicht = {}
        for tag_num in range(1, letzter_tag + 1):
            tag = date(jahr, monat, tag_num)
            tag_key = tag.strftime("%Y-%m-%d")
            monats_uebersicht[tag_key] = [
                t for t in termine if t.datum == tag
            ]

        return monats_uebersicht
