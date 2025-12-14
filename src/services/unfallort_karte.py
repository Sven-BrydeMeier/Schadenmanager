"""
Unfallort-Karte Service
Geolocation und Kartenvisualisierung für Unfallorte
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import json
import math
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class StrassenTyp(str, Enum):
    """Typ der Straße"""
    AUTOBAHN = "AUTOBAHN"
    BUNDESSTRASSE = "BUNDESSTRASSE"
    LANDESSTRASSE = "LANDESSTRASSE"
    KREISSTRASSE = "KREISSTRASSE"
    INNERORTS = "INNERORTS"
    PARKPLATZ = "PARKPLATZ"
    PRIVATGELAENDE = "PRIVATGELAENDE"
    SONSTIGE = "SONSTIGE"


class UnfallortTyp(str, Enum):
    """Typ des Unfallorts"""
    KREUZUNG = "KREUZUNG"
    EINMUENDUNG = "EINMUENDUNG"
    GERADE = "GERADE"
    KURVE = "KURVE"
    KREISVERKEHR = "KREISVERKEHR"
    AUFFAHRT = "AUFFAHRT"
    ABFAHRT = "ABFAHRT"
    BAUSTELLE = "BAUSTELLE"
    SONSTIGE = "SONSTIGE"


class Unfallort(Base):
    """Model für Unfallorte mit Geodaten"""
    __tablename__ = "unfallort"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False, unique=True)
    projekt = relationship("UnfallProjekt", backref="unfallort_details")

    # Koordinaten
    latitude = Column(Float)
    longitude = Column(Float)
    genauigkeit_meter = Column(Float)

    # Adresse
    strasse = Column(String(200))
    hausnummer = Column(String(20))
    plz = Column(String(10))
    ort = Column(String(100))
    bundesland = Column(String(50))
    land = Column(String(50), default="Deutschland")

    # Straßendetails
    strassen_typ = Column(SQLEnum(StrassenTyp))
    unfallort_typ = Column(SQLEnum(UnfallortTyp))
    strassen_name = Column(String(200))
    strassen_nummer = Column(String(20))  # z.B. B1, A7
    kilometer = Column(Float)  # Bei Autobahn/Bundesstraße

    # Kreuzung/Einmündung
    kreuzende_strasse = Column(String(200))

    # Zusätzliche Infos
    richtungsfahrbahn = Column(String(100))
    fahrstreifen = Column(Integer)
    tempolimit = Column(Integer)
    beschreibung = Column(Text)

    # Wetter/Bedingungen (zum Unfallzeitpunkt)
    _wetterbedingungen = Column("wetterbedingungen", Text)
    _strassenzustand = Column("strassenzustand", Text)
    beleuchtung = Column(String(50))  # Tageslicht, Dämmerung, Dunkel

    # Referenzen
    google_place_id = Column(String(200))
    openstreetmap_id = Column(String(200))

    # Metadaten
    erfasst_am = Column(DateTime, default=datetime.now)
    erfasst_von_user_id = Column(Integer, ForeignKey("user.id"))
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def wetterbedingungen(self) -> List[str]:
        if self._wetterbedingungen:
            return json.loads(self._wetterbedingungen)
        return []

    @wetterbedingungen.setter
    def wetterbedingungen(self, value: List[str]):
        self._wetterbedingungen = json.dumps(value)

    @property
    def strassenzustand(self) -> List[str]:
        if self._strassenzustand:
            return json.loads(self._strassenzustand)
        return []

    @strassenzustand.setter
    def strassenzustand(self, value: List[str]):
        self._strassenzustand = json.dumps(value)

    @property
    def vollstaendige_adresse(self) -> str:
        """Gibt die vollständige Adresse zurück"""
        teile = []
        if self.strasse:
            addr = self.strasse
            if self.hausnummer:
                addr += f" {self.hausnummer}"
            teile.append(addr)
        if self.plz or self.ort:
            teile.append(f"{self.plz or ''} {self.ort or ''}".strip())
        return ", ".join(teile) if teile else "Unbekannt"

    @property
    def koordinaten_string(self) -> str:
        """Koordinaten als String"""
        if self.latitude and self.longitude:
            return f"{self.latitude:.6f}, {self.longitude:.6f}"
        return "Nicht erfasst"


class UnfallortService:
    """Service für Unfallort-Verwaltung"""

    # Wetter-Optionen
    WETTER_OPTIONEN = [
        "Sonnig/Klar", "Bewölkt", "Leichter Regen", "Starker Regen",
        "Schnee", "Nebel", "Hagel", "Gewitter", "Wind"
    ]

    # Straßenzustand-Optionen
    STRASSEN_OPTIONEN = [
        "Trocken", "Nass", "Feucht", "Schnee", "Eis/Glätte",
        "Schlaglöcher", "Baustelle", "Verschmutzt", "Laub"
    ]

    def __init__(self, db_session):
        self.db = db_session

    def unfallort_erfassen(
        self,
        projekt_id: int,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        strasse: Optional[str] = None,
        hausnummer: Optional[str] = None,
        plz: Optional[str] = None,
        ort: Optional[str] = None,
        strassen_typ: Optional[StrassenTyp] = None,
        unfallort_typ: Optional[UnfallortTyp] = None,
        erfasst_von_user_id: Optional[int] = None,
        **kwargs
    ) -> Unfallort:
        """Erfasst einen Unfallort"""
        # Prüfen ob bereits vorhanden
        existiert = self.db.query(Unfallort).filter(
            Unfallort.projekt_id == projekt_id
        ).first()

        if existiert:
            # Aktualisieren
            return self.unfallort_aktualisieren(
                existiert.id,
                latitude=latitude,
                longitude=longitude,
                strasse=strasse,
                hausnummer=hausnummer,
                plz=plz,
                ort=ort,
                strassen_typ=strassen_typ,
                unfallort_typ=unfallort_typ,
                **kwargs
            )

        unfallort = Unfallort(
            projekt_id=projekt_id,
            latitude=latitude,
            longitude=longitude,
            strasse=strasse,
            hausnummer=hausnummer,
            plz=plz,
            ort=ort,
            strassen_typ=strassen_typ,
            unfallort_typ=unfallort_typ,
            erfasst_von_user_id=erfasst_von_user_id
        )

        # Zusätzliche Felder
        for key, value in kwargs.items():
            if hasattr(unfallort, key):
                setattr(unfallort, key, value)

        self.db.add(unfallort)
        self.db.flush()

        return unfallort

    def unfallort_aktualisieren(
        self,
        unfallort_id: int,
        **kwargs
    ) -> Optional[Unfallort]:
        """Aktualisiert einen Unfallort"""
        unfallort = self.db.query(Unfallort).get(unfallort_id)

        if unfallort:
            for key, value in kwargs.items():
                if hasattr(unfallort, key) and value is not None:
                    setattr(unfallort, key, value)
            self.db.flush()

        return unfallort

    def unfallort_fuer_projekt(self, projekt_id: int) -> Optional[Unfallort]:
        """Holt den Unfallort für ein Projekt"""
        return self.db.query(Unfallort).filter(
            Unfallort.projekt_id == projekt_id
        ).first()

    def koordinaten_aus_adresse(self, adresse: str) -> Optional[Tuple[float, float]]:
        """
        Geocoding: Adresse zu Koordinaten
        In Produktion: Google Maps, OpenStreetMap Nominatim, etc.
        """
        # Simulierte Geocoding-Ergebnisse für Demo
        # In Produktion würde hier eine echte API aufgerufen
        demo_orte = {
            'berlin': (52.5200, 13.4050),
            'münchen': (48.1351, 11.5820),
            'hamburg': (53.5511, 9.9937),
            'köln': (50.9375, 6.9603),
            'frankfurt': (50.1109, 8.6821),
            'stuttgart': (48.7758, 9.1829),
            'düsseldorf': (51.2277, 6.7735),
            'leipzig': (51.3397, 12.3731),
            'dortmund': (51.5136, 7.4653),
            'essen': (51.4556, 7.0116)
        }

        adresse_lower = adresse.lower()
        for stadt, coords in demo_orte.items():
            if stadt in adresse_lower:
                return coords

        return None

    def adresse_aus_koordinaten(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, str]]:
        """
        Reverse Geocoding: Koordinaten zu Adresse
        In Produktion: Google Maps, OpenStreetMap Nominatim, etc.
        """
        # Simuliertes Reverse Geocoding für Demo
        return {
            'strasse': 'Beispielstraße',
            'hausnummer': '1',
            'plz': '10115',
            'ort': 'Berlin',
            'bundesland': 'Berlin',
            'land': 'Deutschland'
        }

    def entfernung_berechnen(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Berechnet Entfernung in km (Haversine-Formel)"""
        R = 6371  # Erdradius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def unfallorte_in_umkreis(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10
    ) -> List[Unfallort]:
        """Findet Unfallorte im Umkreis"""
        alle_orte = self.db.query(Unfallort).filter(
            Unfallort.latitude.isnot(None),
            Unfallort.longitude.isnot(None)
        ).all()

        im_umkreis = []
        for ort in alle_orte:
            entfernung = self.entfernung_berechnen(
                latitude, longitude,
                ort.latitude, ort.longitude
            )
            if entfernung <= radius_km:
                im_umkreis.append(ort)

        return im_umkreis

    def generiere_karten_url(
        self,
        unfallort: Unfallort,
        anbieter: str = "openstreetmap"
    ) -> str:
        """Generiert eine Karten-URL"""
        if not unfallort.latitude or not unfallort.longitude:
            return ""

        if anbieter == "google":
            return f"https://www.google.com/maps?q={unfallort.latitude},{unfallort.longitude}"
        elif anbieter == "openstreetmap":
            return f"https://www.openstreetmap.org/?mlat={unfallort.latitude}&mlon={unfallort.longitude}&zoom=17"
        elif anbieter == "bing":
            return f"https://www.bing.com/maps?cp={unfallort.latitude}~{unfallort.longitude}&lvl=17"

        return ""

    def generiere_embed_html(
        self,
        unfallort: Unfallort,
        breite: int = 600,
        hoehe: int = 400
    ) -> str:
        """Generiert HTML für eingebettete Karte"""
        if not unfallort.latitude or not unfallort.longitude:
            return "<p>Keine Koordinaten verfügbar</p>"

        # OpenStreetMap Embed
        return f'''
<iframe
    width="{breite}"
    height="{hoehe}"
    frameborder="0"
    scrolling="no"
    marginheight="0"
    marginwidth="0"
    src="https://www.openstreetmap.org/export/embed.html?bbox={unfallort.longitude-0.01}%2C{unfallort.latitude-0.01}%2C{unfallort.longitude+0.01}%2C{unfallort.latitude+0.01}&amp;layer=mapnik&amp;marker={unfallort.latitude}%2C{unfallort.longitude}"
    style="border: 1px solid #ccc; border-radius: 4px;">
</iframe>
'''

    def unfallort_statistik(self) -> Dict[str, Any]:
        """Erstellt eine Statistik der Unfallorte"""
        alle_orte = self.db.query(Unfallort).all()

        return {
            'gesamt': len(alle_orte),
            'mit_koordinaten': len([o for o in alle_orte if o.latitude and o.longitude]),
            'nach_strassen_typ': self._zaehle_nach_attribut(alle_orte, 'strassen_typ'),
            'nach_unfallort_typ': self._zaehle_nach_attribut(alle_orte, 'unfallort_typ'),
            'nach_bundesland': self._zaehle_nach_attribut(alle_orte, 'bundesland'),
            'nach_wetter': self._zaehle_wetter(alle_orte)
        }

    def _zaehle_nach_attribut(self, orte: List[Unfallort], attribut: str) -> Dict[str, int]:
        """Zählt nach einem Attribut"""
        zaehler = {}
        for o in orte:
            wert = getattr(o, attribut, None)
            if wert:
                key = wert.value if hasattr(wert, 'value') else str(wert)
                zaehler[key] = zaehler.get(key, 0) + 1
        return zaehler

    def _zaehle_wetter(self, orte: List[Unfallort]) -> Dict[str, int]:
        """Zählt Wetterbedingungen"""
        zaehler = {}
        for o in orte:
            for wetter in o.wetterbedingungen:
                zaehler[wetter] = zaehler.get(wetter, 0) + 1
        return zaehler

    def generiere_geojson(self, unfallorte: List[Unfallort]) -> Dict:
        """Generiert GeoJSON für mehrere Unfallorte"""
        features = []

        for ort in unfallorte:
            if ort.latitude and ort.longitude:
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [ort.longitude, ort.latitude]
                    },
                    "properties": {
                        "id": ort.id,
                        "projekt_id": ort.projekt_id,
                        "adresse": ort.vollstaendige_adresse,
                        "strassen_typ": ort.strassen_typ.value if ort.strassen_typ else None,
                        "unfallort_typ": ort.unfallort_typ.value if ort.unfallort_typ else None
                    }
                }
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }
