"""
Datenschutz-Zustimmung Model

Speichert die Zustimmungen der Nutzer zu Datenschutzerklärung,
AGB, Widerrufsbelehrung und Kontakteinwilligung.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from src.models.base import Base


class DatenschutzZustimmung(Base):
    """
    Speichert die Datenschutz-Zustimmungen eines Nutzers.

    Jede Zustimmung wird mit Timestamp und IP-Adresse protokolliert
    für Nachweiszwecke gemäß DSGVO.
    """
    __tablename__ = "datenschutz_zustimmung"

    id = Column(Integer, primary_key=True)

    # Zuordnung zum User
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    # Zustimmungen
    datenschutz_akzeptiert = Column(Boolean, default=False)
    datenschutz_akzeptiert_am = Column(DateTime)
    datenschutz_version = Column(String(20))  # Version der Datenschutzerklärung

    agb_akzeptiert = Column(Boolean, default=False)
    agb_akzeptiert_am = Column(DateTime)
    agb_version = Column(String(20))

    widerrufsbelehrung_akzeptiert = Column(Boolean, default=False)
    widerrufsbelehrung_akzeptiert_am = Column(DateTime)

    kontakt_einwilligung = Column(Boolean, default=False)  # Telefon/E-Mail Kontakt
    kontakt_einwilligung_am = Column(DateTime)

    widerrufsrecht_verzicht = Column(Boolean, default=False)  # Verzicht auf Widerrufsrecht
    widerrufsrecht_verzicht_am = Column(DateTime)

    vertraulichkeit_akzeptiert = Column(Boolean, default=False)  # Keine Weitergabe an Dritte
    vertraulichkeit_akzeptiert_am = Column(DateTime)

    # Technische Daten für Nachweis
    ip_adresse = Column(String(50))
    user_agent = Column(String(500))

    # Widerruf
    widerrufen = Column(Boolean, default=False)
    widerrufen_am = Column(DateTime)
    widerruf_grund = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="datenschutz_zustimmungen")

    def __repr__(self):
        return f"<DatenschutzZustimmung(user_id={self.user_id}, datenschutz={self.datenschutz_akzeptiert})>"

    @property
    def alle_pflicht_akzeptiert(self) -> bool:
        """Prüft ob alle Pflichtfelder akzeptiert wurden"""
        return all([
            self.datenschutz_akzeptiert,
            self.agb_akzeptiert,
            self.widerrufsbelehrung_akzeptiert,
            self.vertraulichkeit_akzeptiert
        ])

    @property
    def status_text(self) -> str:
        """Gibt den Zustimmungsstatus als Text zurück"""
        if self.widerrufen:
            return "Widerrufen"
        elif self.alle_pflicht_akzeptiert:
            return "Vollständig akzeptiert"
        else:
            return "Unvollständig"


# Aktuelle Versionen der Dokumente
AKTUELLE_VERSIONEN = {
    "datenschutz": "1.0",
    "agb": "1.0",
    "widerrufsbelehrung": "1.0"
}


# ============================================
# DATENSCHUTZERKLÄRUNG TEXT
# ============================================

DATENSCHUTZERKLAERUNG = """
# Datenschutzerklärung

## § 1 Information über die Erhebung personenbezogener Daten

**(1)** Im Folgenden informieren wir über die Erhebung personenbezogener Daten bei Nutzung unserer Anwendung Schadenmanager. Personenbezogene Daten sind alle Daten, die auf Sie persönlich beziehbar sind, z. B. Name, Adresse, E-Mail-Adressen, Nutzerverhalten.

**(2)** Verantwortlicher gem. Art. 4 Abs. 7 EU-Datenschutz-Grundverordnung (DS-GVO) ist:

**Schadenmanager.vom GmbH**
[Ihre Adresse]
[PLZ Ort]
E-Mail: datenschutz@schadenmanager.vom

Datenschutzbeauftragter: [Ihr Name]

**(3)** Bei Ihrer Kontaktaufnahme mit uns per E-Mail oder über ein Kontaktformular werden die von Ihnen mitgeteilten Daten (Ihre E-Mail-Adresse, ggf. Ihr Name und Ihre Telefonnummer) von uns gespeichert, um Ihre Fragen zu beantworten. Die in diesem Zusammenhang anfallenden Daten löschen wir, nachdem die Speicherung nicht mehr erforderlich ist, oder schränken die Verarbeitung ein, falls gesetzliche Aufbewahrungspflichten bestehen.

**(4)** Falls wir für einzelne Funktionen unseres Angebots auf beauftragte Dienstleister zurückgreifen oder Ihre Daten für die Schadensabwicklung nutzen, werden wir Sie untenstehend im Detail über die jeweiligen Vorgänge informieren. Dabei nennen wir auch die festgelegten Kriterien der Speicherdauer.

## § 2 Ihre Rechte

**(1)** Sie haben gegenüber uns folgende Rechte hinsichtlich der Sie betreffenden personenbezogenen Daten:

- Recht auf Auskunft (Art. 15 DS-GVO)
- Recht auf Berichtigung (Art. 16 DS-GVO)
- Recht auf Löschung (Art. 17 DS-GVO)
- Recht auf Einschränkung der Verarbeitung (Art. 18 DS-GVO)
- Recht auf Widerspruch gegen die Verarbeitung (Art. 21 DS-GVO)
- Recht auf Datenübertragbarkeit (Art. 20 DS-GVO)

**(2)** Sie haben zudem das Recht, sich bei einer Datenschutz-Aufsichtsbehörde über die Verarbeitung Ihrer personenbezogenen Daten durch uns zu beschweren.

## § 3 Erhebung personenbezogener Daten bei Nutzung der Anwendung

**(1)** Bei der Nutzung unserer Anwendung erheben wir folgende personenbezogene Daten, die für uns technisch erforderlich sind, um Ihnen unseren Service anzubieten und die Stabilität und Sicherheit zu gewährleisten (Rechtsgrundlage ist Art. 6 Abs. 1 S. 1 lit. f DS-GVO):

- IP-Adresse
- Datum und Uhrzeit der Anfrage
- Inhalt der Anforderung (konkrete Seite/Funktion)
- Zugriffsstatus/HTTP-Statuscode
- Browser und Betriebssystem
- Sprache und Version der Software

**(2)** Zusätzlich speichern wir zur Erbringung unserer Dienstleistungen:

- Ihre Kontaktdaten (Name, Adresse, Telefon, E-Mail)
- Daten zum Schadensfall (Unfallort, -datum, beteiligte Fahrzeuge)
- Hochgeladene Dokumente (Gutachten, Rechnungen, Korrespondenz)
- Bankverbindungsdaten für die Schadensregulierung
- Kommunikationsverlauf mit Versicherungen und anderen Beteiligten

## § 4 Zweck der Datenverarbeitung

Wir verarbeiten Ihre Daten ausschließlich für folgende Zwecke:

- Abwicklung Ihres Schadensfalls
- Kommunikation mit Versicherungen, Werkstätten und Gutachtern
- Erstellung von Anspruchsschreiben und rechtlicher Korrespondenz
- Dokumentation des Verfahrensfortschritts
- Erfüllung gesetzlicher Aufbewahrungspflichten

## § 5 Weitergabe von Daten an Dritte

Ihre Daten werden im Rahmen der Schadensabwicklung an folgende Dritte weitergegeben:

- Gegnerische Haftpflichtversicherung (zur Geltendmachung Ihrer Ansprüche)
- Werkstätten (zur Reparaturabwicklung)
- Gutachter (zur Schadensfeststellung)
- Polizei/Staatsanwaltschaft (bei Ermittlungsverfahren)
- Gerichte (bei Rechtsstreitigkeiten)

Eine Weitergabe erfolgt nur, soweit dies für die Durchführung der Schadensabwicklung erforderlich ist.

## § 6 Speicherdauer

Wir speichern Ihre Daten, solange dies für die Abwicklung Ihres Schadensfalls erforderlich ist. Nach Abschluss des Falls werden die Daten gemäß den gesetzlichen Aufbewahrungsfristen aufbewahrt:

- Vertragsunterlagen: 10 Jahre (§ 147 AO)
- Korrespondenz: 6 Jahre (§ 257 HGB)
- Rechnungen: 10 Jahre (§ 14b UStG)

## § 7 Widerspruch oder Widerruf

**(1)** Falls Sie eine Einwilligung zur Verarbeitung Ihrer Daten erteilt haben, können Sie diese jederzeit widerrufen. Ein solcher Widerruf beeinflusst die Zulässigkeit der Verarbeitung Ihrer personenbezogenen Daten, nachdem Sie ihn gegenüber uns ausgesprochen haben.

**(2)** Selbstverständlich können Sie der Verarbeitung Ihrer personenbezogenen Daten für Zwecke der Werbung jederzeit widersprechen.

Kontakt für Widerspruch/Widerruf:

**Schadenmanager.vom GmbH**
E-Mail: datenschutz@schadenmanager.vom

## § 8 Datensicherheit

Wir verwenden innerhalb des Website-Besuchs das verbreitete SSL-Verfahren (Secure Socket Layer) in Verbindung mit der jeweils höchsten Verschlüsselungsstufe, die von Ihrem Browser unterstützt wird. Alle von Ihnen übermittelten Daten werden verschlüsselt übertragen.

---

*Stand: Januar 2026*
*Version: 1.0*
"""


# ============================================
# AGB TEXT
# ============================================

AGB_TEXT = """
# Allgemeine Geschäftsbedingungen (AGB)

## § 1 Geltungsbereich

Diese Allgemeinen Geschäftsbedingungen gelten für alle Dienstleistungen der Schadenmanager.vom GmbH im Rahmen der Unfallschadensabwicklung.

## § 2 Vertragsgegenstand

**(1)** Wir unterstützen Sie bei der Abwicklung Ihres Verkehrsunfallschadens gegenüber der gegnerischen Haftpflichtversicherung.

**(2)** Die Dienstleistung umfasst:
- Dokumentation des Schadensfalls
- Kommunikation mit Versicherungen
- Koordination von Werkstätten und Gutachtern
- Überwachung der Schadensregulierung

## § 3 Vertraulichkeit

**(1)** Alle uns übermittelten Informationen und Dokumente werden streng vertraulich behandelt.

**(2)** Eine Weitergabe an Dritte erfolgt nur mit Ihrer ausdrücklichen Zustimmung oder soweit dies für die Schadensabwicklung erforderlich ist.

## § 4 Haftung

**(1)** Wir haften für Schäden, die durch vorsätzliche oder grob fahrlässige Pflichtverletzung entstehen.

**(2)** Bei leichter Fahrlässigkeit haften wir nur bei Verletzung wesentlicher Vertragspflichten (Kardinalpflichten).

## § 5 Datenschutz

Die Verarbeitung Ihrer personenbezogenen Daten erfolgt gemäß unserer Datenschutzerklärung und den Bestimmungen der DS-GVO.

## § 6 Schlussbestimmungen

**(1)** Es gilt das Recht der Bundesrepublik Deutschland.

**(2)** Sollten einzelne Bestimmungen dieser AGB unwirksam sein, bleibt die Wirksamkeit der übrigen Bestimmungen unberührt.

---

*Stand: Januar 2026*
*Version: 1.0*
"""


# ============================================
# WIDERRUFSBELEHRUNG TEXT
# ============================================

WIDERRUFSBELEHRUNG = """
# Widerrufsbelehrung

## Widerrufsrecht

Sie haben das Recht, binnen vierzehn Tagen ohne Angabe von Gründen diesen Vertrag zu widerrufen.

Die Widerrufsfrist beträgt vierzehn Tage ab dem Tag des Vertragsabschlusses.

Um Ihr Widerrufsrecht auszuüben, müssen Sie uns

**Schadenmanager.vom GmbH**
[Ihre Adresse]
[PLZ Ort]
E-Mail: widerruf@schadenmanager.vom

mittels einer eindeutigen Erklärung (z. B. ein mit der Post versandter Brief oder E-Mail) über Ihren Entschluss, diesen Vertrag zu widerrufen, informieren.

Zur Wahrung der Widerrufsfrist reicht es aus, dass Sie die Mitteilung über die Ausübung des Widerrufsrechts vor Ablauf der Widerrufsfrist absenden.

## Folgen des Widerrufs

Wenn Sie diesen Vertrag widerrufen, haben wir Ihnen alle Zahlungen, die wir von Ihnen erhalten haben, unverzüglich und spätestens binnen vierzehn Tagen ab dem Tag zurückzuzahlen, an dem die Mitteilung über Ihren Widerruf dieses Vertrags bei uns eingegangen ist.

## Besondere Hinweise

Haben Sie verlangt, dass die Dienstleistung während der Widerrufsfrist beginnen soll, so haben Sie uns einen angemessenen Betrag zu zahlen, der dem Anteil der bis zu dem Zeitpunkt, zu dem Sie uns von der Ausübung des Widerrufsrechts hinsichtlich dieses Vertrags unterrichten, bereits erbrachten Dienstleistungen im Vergleich zum Gesamtumfang der im Vertrag vorgesehenen Dienstleistungen entspricht.

---

## Muster-Widerrufsformular

*(Wenn Sie den Vertrag widerrufen wollen, dann füllen Sie bitte dieses Formular aus und senden Sie es zurück.)*

An:
Schadenmanager.vom GmbH
[Adresse]
E-Mail: widerruf@schadenmanager.vom

Hiermit widerrufe(n) ich/wir (*) den von mir/uns (*) abgeschlossenen Vertrag über die Erbringung der folgenden Dienstleistung:

_________________________________

Bestellt am: _________________________________

Name des/der Verbraucher(s): _________________________________

Anschrift des/der Verbraucher(s): _________________________________

Unterschrift des/der Verbraucher(s) (nur bei Mitteilung auf Papier): _________________________________

Datum: _________________________________

(*) Unzutreffendes streichen.

---

*Stand: Januar 2026*
"""


# ============================================
# VERTRAULICHKEITSHINWEIS TEXT
# ============================================

VERTRAULICHKEITSHINWEIS = """
# Vertraulichkeitsvereinbarung

## Persönliche Nutzung der Daten

Die Ihnen über unsere Plattform zur Verfügung gestellten Informationen, Dokumente und Daten zu Ihrem Schadensfall sind ausschließlich für Sie persönlich bestimmt.

## Weitergabe an Dritte

Eine Weitergabe dieser Daten an Dritte ist nur mit unserer ausdrücklichen schriftlichen Zustimmung gestattet.

Bei Zuwiderhandlung behalten wir uns rechtliche Schritte vor.

## Gesprächsführung

Alle Gespräche und Verhandlungen bezüglich Ihres Schadensfalls sind über uns zu führen, um eine konsistente und erfolgreiche Abwicklung zu gewährleisten.
"""
