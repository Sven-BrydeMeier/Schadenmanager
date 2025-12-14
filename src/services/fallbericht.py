"""
PDF-Fallbericht Generator Service
Generiert umfassende PDF-Berichte für Schadensfälle
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class BerichtTyp(str, Enum):
    """Typen von Berichten"""
    VOLLSTAENDIG = "VOLLSTAENDIG"
    ZUSAMMENFASSUNG = "ZUSAMMENFASSUNG"
    KOSTENAUFSTELLUNG = "KOSTENAUFSTELLUNG"
    TIMELINE = "TIMELINE"
    VERSICHERUNG = "VERSICHERUNG"
    GERICHT = "GERICHT"
    MANDANT = "MANDANT"


class BerichtFormat(str, Enum):
    """Ausgabeformate"""
    PDF = "PDF"
    HTML = "HTML"
    DOCX = "DOCX"


class Fallbericht(Base):
    """Model für generierte Berichte"""
    __tablename__ = "fallbericht"

    id = Column(Integer, primary_key=True)

    # Projekt
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="fallberichte")

    # Bericht
    bezeichnung = Column(String(200), nullable=False)
    bericht_typ = Column(SQLEnum(BerichtTyp), default=BerichtTyp.VOLLSTAENDIG)
    format = Column(SQLEnum(BerichtFormat), default=BerichtFormat.PDF)

    # Inhalt
    _enthaltene_abschnitte = Column("enthaltene_abschnitte", Text)
    _bericht_daten = Column("bericht_daten", Text)

    # Generierung
    generiert_am = Column(DateTime, default=datetime.now)
    generiert_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Datei
    dateiname = Column(String(200))
    dateigroesse = Column(Integer)
    dateipfad = Column(String(500))

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)

    @property
    def enthaltene_abschnitte(self) -> List[str]:
        if self._enthaltene_abschnitte:
            return json.loads(self._enthaltene_abschnitte)
        return []

    @enthaltene_abschnitte.setter
    def enthaltene_abschnitte(self, value: List[str]):
        self._enthaltene_abschnitte = json.dumps(value)

    @property
    def bericht_daten(self) -> Dict:
        if self._bericht_daten:
            return json.loads(self._bericht_daten)
        return {}

    @bericht_daten.setter
    def bericht_daten(self, value: Dict):
        self._bericht_daten = json.dumps(value, default=str)


class FallberichtService:
    """Service für PDF-Fallbericht-Generierung"""

    # Verfügbare Abschnitte
    ABSCHNITTE = {
        'stammdaten': 'Stammdaten & Aktenzeichen',
        'unfallhergang': 'Unfallhergang',
        'beteiligte': 'Beteiligte Parteien',
        'fahrzeuge': 'Fahrzeugdaten',
        'schaeden': 'Schadensübersicht',
        'kosten': 'Kostenaufstellung',
        'forderungen': 'Forderungsübersicht',
        'zahlungen': 'Zahlungseingänge',
        'dokumente': 'Dokumentenliste',
        'timeline': 'Fallverlauf/Timeline',
        'korrespondenz': 'Korrespondenz-Übersicht',
        'gutachten': 'Gutachten-Zusammenfassung',
        'rechtslage': 'Rechtliche Bewertung',
        'fristen': 'Fristen & Termine',
        'notizen': 'Interne Notizen'
    }

    def __init__(self, db_session):
        self.db = db_session

    def bericht_generieren(
        self,
        projekt_id: int,
        bericht_typ: BerichtTyp = BerichtTyp.VOLLSTAENDIG,
        abschnitte: Optional[List[str]] = None,
        format: BerichtFormat = BerichtFormat.PDF,
        generiert_von_user_id: Optional[int] = None
    ) -> Fallbericht:
        """Generiert einen Fallbericht"""
        from src.models import UnfallProjekt

        projekt = self.db.query(UnfallProjekt).get(projekt_id)
        if not projekt:
            raise ValueError("Projekt nicht gefunden")

        # Standard-Abschnitte je nach Typ
        if not abschnitte:
            abschnitte = self._standard_abschnitte(bericht_typ)

        # Daten sammeln
        bericht_daten = self._sammle_daten(projekt, abschnitte)

        # Bericht erstellen
        bericht = Fallbericht(
            projekt_id=projekt_id,
            bezeichnung=f"Fallbericht {projekt.aktenzeichen or projekt.projektnummer}",
            bericht_typ=bericht_typ,
            format=format,
            generiert_von_user_id=generiert_von_user_id
        )
        bericht.enthaltene_abschnitte = abschnitte
        bericht.bericht_daten = bericht_daten

        # Dateiname generieren
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bericht.dateiname = f"Fallbericht_{projekt.projektnummer}_{timestamp}.pdf"

        self.db.add(bericht)
        self.db.flush()

        return bericht

    def _standard_abschnitte(self, bericht_typ: BerichtTyp) -> List[str]:
        """Gibt Standard-Abschnitte für einen Berichtstyp zurück"""
        if bericht_typ == BerichtTyp.VOLLSTAENDIG:
            return list(self.ABSCHNITTE.keys())

        elif bericht_typ == BerichtTyp.ZUSAMMENFASSUNG:
            return ['stammdaten', 'unfallhergang', 'schaeden', 'kosten', 'forderungen']

        elif bericht_typ == BerichtTyp.KOSTENAUFSTELLUNG:
            return ['stammdaten', 'kosten', 'forderungen', 'zahlungen']

        elif bericht_typ == BerichtTyp.TIMELINE:
            return ['stammdaten', 'timeline', 'korrespondenz']

        elif bericht_typ == BerichtTyp.VERSICHERUNG:
            return ['stammdaten', 'unfallhergang', 'beteiligte', 'fahrzeuge',
                    'schaeden', 'kosten', 'forderungen', 'gutachten']

        elif bericht_typ == BerichtTyp.GERICHT:
            return ['stammdaten', 'unfallhergang', 'beteiligte', 'fahrzeuge',
                    'schaeden', 'kosten', 'forderungen', 'rechtslage', 'timeline']

        elif bericht_typ == BerichtTyp.MANDANT:
            return ['stammdaten', 'unfallhergang', 'schaeden', 'kosten',
                    'forderungen', 'zahlungen', 'fristen']

        return ['stammdaten']

    def _sammle_daten(self, projekt, abschnitte: List[str]) -> Dict[str, Any]:
        """Sammelt alle Daten für den Bericht"""
        daten = {}

        if 'stammdaten' in abschnitte:
            daten['stammdaten'] = self._sammle_stammdaten(projekt)

        if 'unfallhergang' in abschnitte:
            daten['unfallhergang'] = self._sammle_unfallhergang(projekt)

        if 'beteiligte' in abschnitte:
            daten['beteiligte'] = self._sammle_beteiligte(projekt)

        if 'fahrzeuge' in abschnitte:
            daten['fahrzeuge'] = self._sammle_fahrzeuge(projekt)

        if 'schaeden' in abschnitte:
            daten['schaeden'] = self._sammle_schaeden(projekt)

        if 'kosten' in abschnitte:
            daten['kosten'] = self._sammle_kosten(projekt)

        if 'forderungen' in abschnitte:
            daten['forderungen'] = self._sammle_forderungen(projekt)

        if 'zahlungen' in abschnitte:
            daten['zahlungen'] = self._sammle_zahlungen(projekt)

        if 'dokumente' in abschnitte:
            daten['dokumente'] = self._sammle_dokumente(projekt)

        if 'timeline' in abschnitte:
            daten['timeline'] = self._sammle_timeline(projekt)

        if 'fristen' in abschnitte:
            daten['fristen'] = self._sammle_fristen(projekt)

        return daten

    def _sammle_stammdaten(self, projekt) -> Dict:
        """Sammelt Stammdaten"""
        return {
            'projektnummer': projekt.projektnummer,
            'aktenzeichen': projekt.aktenzeichen,
            'status': projekt.status.value if projekt.status else None,
            'erstellt_am': projekt.erstellt_am.isoformat() if projekt.erstellt_am else None,
            'unfalldatum': projekt.unfalldatum.isoformat() if projekt.unfalldatum else None,
            'unfallort': projekt.unfallort,
            'kennzeichen_mandant': projekt.kennzeichen_mandant,
            'kennzeichen_gegner': projekt.kennzeichen_gegner
        }

    def _sammle_unfallhergang(self, projekt) -> Dict:
        """Sammelt Unfallhergang"""
        return {
            'datum': projekt.unfalldatum.isoformat() if projekt.unfalldatum else None,
            'uhrzeit': projekt.unfallzeit.isoformat() if hasattr(projekt, 'unfallzeit') and projekt.unfallzeit else None,
            'ort': projekt.unfallort,
            'beschreibung': projekt.unfallhergang if hasattr(projekt, 'unfallhergang') else None,
            'polizei_aufgenommen': getattr(projekt, 'polizei_aufgenommen', None),
            'polizei_aktenzeichen': getattr(projekt, 'polizei_aktenzeichen', None)
        }

    def _sammle_beteiligte(self, projekt) -> List[Dict]:
        """Sammelt Beteiligte"""
        beteiligte = []

        if hasattr(projekt, 'beteiligte'):
            for b in projekt.beteiligte:
                beteiligte.append({
                    'rolle': b.rolle.value if b.rolle else None,
                    'name': f"{b.vorname or ''} {b.nachname or ''}".strip(),
                    'firma': b.firma,
                    'adresse': f"{b.strasse or ''}, {b.plz or ''} {b.ort or ''}".strip(', '),
                    'telefon': b.telefon,
                    'email': b.email
                })

        return beteiligte

    def _sammle_fahrzeuge(self, projekt) -> Dict:
        """Sammelt Fahrzeugdaten"""
        return {
            'mandant': {
                'kennzeichen': projekt.kennzeichen_mandant,
                'fahrzeug': getattr(projekt, 'fahrzeug_mandant', None),
                'erstzulassung': getattr(projekt, 'ez_mandant', None),
                'kilometer': getattr(projekt, 'km_mandant', None)
            },
            'gegner': {
                'kennzeichen': projekt.kennzeichen_gegner,
                'fahrzeug': getattr(projekt, 'fahrzeug_gegner', None)
            }
        }

    def _sammle_schaeden(self, projekt) -> List[Dict]:
        """Sammelt Schadenspositionen"""
        schaeden = []

        if hasattr(projekt, 'schaeden'):
            for s in projekt.schaeden:
                schaeden.append({
                    'kategorie': s.kategorie.value if s.kategorie else None,
                    'bezeichnung': s.bezeichnung,
                    'betrag': float(s.betrag) if s.betrag else 0,
                    'status': s.status.value if s.status else None
                })

        return schaeden

    def _sammle_kosten(self, projekt) -> Dict:
        """Sammelt Kostenübersicht"""
        kosten = {
            'positionen': [],
            'summe': 0
        }

        if hasattr(projekt, 'kosten'):
            for k in projekt.kosten:
                betrag = float(k.betrag) if k.betrag else 0
                kosten['positionen'].append({
                    'kategorie': k.kategorie.value if k.kategorie else None,
                    'bezeichnung': k.bezeichnung,
                    'betrag': betrag,
                    'datum': k.datum.isoformat() if k.datum else None
                })
                kosten['summe'] += betrag

        return kosten

    def _sammle_forderungen(self, projekt) -> Dict:
        """Sammelt Forderungsübersicht"""
        if hasattr(projekt, 'forderung'):
            forderung = projekt.forderung
            return {
                'gesamtforderung': float(forderung.gesamtforderung) if forderung and forderung.gesamtforderung else 0,
                'bezahlt': float(forderung.bezahlt) if forderung and forderung.bezahlt else 0,
                'offen': float(forderung.offen) if forderung and forderung.offen else 0
            }

        return {'gesamtforderung': 0, 'bezahlt': 0, 'offen': 0}

    def _sammle_zahlungen(self, projekt) -> List[Dict]:
        """Sammelt Zahlungseingänge"""
        zahlungen = []

        if hasattr(projekt, 'zahlungen'):
            for z in projekt.zahlungen:
                zahlungen.append({
                    'datum': z.datum.isoformat() if z.datum else None,
                    'betrag': float(z.betrag) if z.betrag else 0,
                    'von': z.von,
                    'verwendungszweck': z.verwendungszweck
                })

        return zahlungen

    def _sammle_dokumente(self, projekt) -> List[Dict]:
        """Sammelt Dokumentenliste"""
        dokumente = []

        if hasattr(projekt, 'dokumente'):
            for d in projekt.dokumente:
                dokumente.append({
                    'name': d.dateiname,
                    'kategorie': d.kategorie.value if d.kategorie else None,
                    'hochgeladen_am': d.erstellt_am.isoformat() if d.erstellt_am else None
                })

        return dokumente

    def _sammle_timeline(self, projekt) -> List[Dict]:
        """Sammelt Timeline-Ereignisse"""
        ereignisse = []

        if hasattr(projekt, 'timeline_eintraege'):
            for t in projekt.timeline_eintraege:
                ereignisse.append({
                    'datum': t.datum.isoformat() if t.datum else None,
                    'typ': t.typ.value if t.typ else None,
                    'titel': t.titel,
                    'beschreibung': t.beschreibung
                })

        return sorted(ereignisse, key=lambda x: x['datum'] or '', reverse=True)

    def _sammle_fristen(self, projekt) -> List[Dict]:
        """Sammelt Fristen"""
        fristen = []

        if hasattr(projekt, 'fristen'):
            for f in projekt.fristen:
                fristen.append({
                    'bezeichnung': f.bezeichnung,
                    'datum': f.frist_datum.isoformat() if f.frist_datum else None,
                    'typ': f.frist_typ.value if f.frist_typ else None,
                    'status': f.status.value if f.status else None,
                    'tage_bis': f.tage_bis_frist if hasattr(f, 'tage_bis_frist') else None
                })

        return sorted(fristen, key=lambda x: x['datum'] or '')

    def generiere_html(self, bericht_id: int) -> str:
        """Generiert HTML-Ausgabe des Berichts"""
        bericht = self.db.query(Fallbericht).get(bericht_id)

        if not bericht:
            return "<html><body>Bericht nicht gefunden</body></html>"

        daten = bericht.bericht_daten
        html_parts = [self._html_header(bericht)]

        if 'stammdaten' in daten:
            html_parts.append(self._render_stammdaten_html(daten['stammdaten']))

        if 'unfallhergang' in daten:
            html_parts.append(self._render_unfallhergang_html(daten['unfallhergang']))

        if 'beteiligte' in daten:
            html_parts.append(self._render_beteiligte_html(daten['beteiligte']))

        if 'kosten' in daten:
            html_parts.append(self._render_kosten_html(daten['kosten']))

        if 'timeline' in daten:
            html_parts.append(self._render_timeline_html(daten['timeline']))

        html_parts.append(self._html_footer())

        return '\n'.join(html_parts)

    def _html_header(self, bericht: Fallbericht) -> str:
        """HTML-Header"""
        return f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>{bericht.bezeichnung}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        .betrag {{ text-align: right; font-family: monospace; }}
        .summe {{ font-weight: bold; background-color: #f9f9f9; }}
    </style>
</head>
<body>
<h1>{bericht.bezeichnung}</h1>
<p class="meta">Erstellt am: {bericht.generiert_am.strftime('%d.%m.%Y %H:%M') if bericht.generiert_am else '-'}</p>
'''

    def _html_footer(self) -> str:
        """HTML-Footer"""
        return '''
<hr>
<p class="meta">Dieser Bericht wurde automatisch generiert vom Schadenmanager.</p>
</body>
</html>'''

    def _render_stammdaten_html(self, daten: Dict) -> str:
        """Rendert Stammdaten als HTML"""
        return f'''
<h2>Stammdaten</h2>
<table>
    <tr><th>Projektnummer</th><td>{daten.get('projektnummer', '-')}</td></tr>
    <tr><th>Aktenzeichen</th><td>{daten.get('aktenzeichen', '-')}</td></tr>
    <tr><th>Unfalldatum</th><td>{daten.get('unfalldatum', '-')}</td></tr>
    <tr><th>Unfallort</th><td>{daten.get('unfallort', '-')}</td></tr>
    <tr><th>Kennzeichen Mandant</th><td>{daten.get('kennzeichen_mandant', '-')}</td></tr>
    <tr><th>Kennzeichen Gegner</th><td>{daten.get('kennzeichen_gegner', '-')}</td></tr>
    <tr><th>Status</th><td>{daten.get('status', '-')}</td></tr>
</table>
'''

    def _render_unfallhergang_html(self, daten: Dict) -> str:
        """Rendert Unfallhergang als HTML"""
        return f'''
<h2>Unfallhergang</h2>
<table>
    <tr><th>Datum</th><td>{daten.get('datum', '-')}</td></tr>
    <tr><th>Ort</th><td>{daten.get('ort', '-')}</td></tr>
    <tr><th>Polizei aufgenommen</th><td>{'Ja' if daten.get('polizei_aufgenommen') else 'Nein'}</td></tr>
    <tr><th>Polizei-Aktenzeichen</th><td>{daten.get('polizei_aktenzeichen', '-')}</td></tr>
</table>
<p>{daten.get('beschreibung', '')}</p>
'''

    def _render_beteiligte_html(self, beteiligte: List[Dict]) -> str:
        """Rendert Beteiligte als HTML"""
        rows = ''
        for b in beteiligte:
            rows += f'''
    <tr>
        <td>{b.get('rolle', '-')}</td>
        <td>{b.get('name', '-')}</td>
        <td>{b.get('firma', '-')}</td>
        <td>{b.get('telefon', '-')}</td>
        <td>{b.get('email', '-')}</td>
    </tr>'''

        return f'''
<h2>Beteiligte</h2>
<table>
    <tr>
        <th>Rolle</th>
        <th>Name</th>
        <th>Firma</th>
        <th>Telefon</th>
        <th>E-Mail</th>
    </tr>
    {rows}
</table>
'''

    def _render_kosten_html(self, kosten: Dict) -> str:
        """Rendert Kosten als HTML"""
        rows = ''
        for k in kosten.get('positionen', []):
            rows += f'''
    <tr>
        <td>{k.get('kategorie', '-')}</td>
        <td>{k.get('bezeichnung', '-')}</td>
        <td>{k.get('datum', '-')}</td>
        <td class="betrag">{k.get('betrag', 0):,.2f} EUR</td>
    </tr>'''

        return f'''
<h2>Kostenaufstellung</h2>
<table>
    <tr>
        <th>Kategorie</th>
        <th>Bezeichnung</th>
        <th>Datum</th>
        <th>Betrag</th>
    </tr>
    {rows}
    <tr class="summe">
        <td colspan="3">Gesamtsumme</td>
        <td class="betrag">{kosten.get('summe', 0):,.2f} EUR</td>
    </tr>
</table>
'''

    def _render_timeline_html(self, ereignisse: List[Dict]) -> str:
        """Rendert Timeline als HTML"""
        rows = ''
        for e in ereignisse:
            rows += f'''
    <tr>
        <td>{e.get('datum', '-')}</td>
        <td>{e.get('typ', '-')}</td>
        <td>{e.get('titel', '-')}</td>
        <td>{e.get('beschreibung', '')}</td>
    </tr>'''

        return f'''
<h2>Fallverlauf</h2>
<table>
    <tr>
        <th>Datum</th>
        <th>Typ</th>
        <th>Titel</th>
        <th>Beschreibung</th>
    </tr>
    {rows}
</table>
'''

    def berichte_fuer_projekt(self, projekt_id: int) -> List[Fallbericht]:
        """Holt alle Berichte für ein Projekt"""
        return self.db.query(Fallbericht).filter(
            Fallbericht.projekt_id == projekt_id
        ).order_by(Fallbericht.generiert_am.desc()).all()
