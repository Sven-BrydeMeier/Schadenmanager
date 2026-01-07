from src.models.base import Base
from src.models.enums import (
    Rollen, OrgTyp, MeilensteinStatus, KostenKategorie,
    KostenAmpel, KorrespondenzRichtung, DokumentTyp,
    SchreibenTyp, EmpfaengerTyp, ChatNachrichtRolle
)
from src.models.organisation import Organisation
from src.models.user import User
from src.models.fahrzeug import Fahrzeug
from src.models.unfallprojekt import UnfallProjekt
from src.models.dokument import Dokument
from src.models.timeline import TimelineMeilenstein
from src.models.kosten import KostenPosition
from src.models.ersatzwagen import ErsatzwagenAnbieter, MietfahrzeugAngebot
from src.models.gebuehren import GebuehrenBerechnung
from src.models.korrespondenz import Korrespondenz
from src.models.wiedervorlage import Wiedervorlage, WiedervorlageTyp, WiedervorlagePrioritaet
from src.models.audit_log import AuditLog, AktionTyp, AktionKategorie
from src.models.notiz import Notiz, Mahnung
from src.models.checkliste import ChecklistenItem
from src.models.signatur import DigitaleSignatur, SignaturAnforderung
from src.models.unfallaufnahme_beteiligter import UnfallaufnahmeBeteiligter
from src.models.chat_nachricht import ChatNachricht
from src.models.datenschutz import DatenschutzZustimmung, AKTUELLE_VERSIONEN
from src.models.zusatzdaten import (
    TUVDaten, TUVStatus,
    LeasingKreditbank, FinanzierungsTyp,
    PolizeiDienststelle,
    Bankverbindung
)

# Models aus Services (dort definiert wegen komplexer Abhängigkeiten)
from src.services.dsgvo import DSGVOProtokoll, DSGVOAktionTyp
from src.services.ermittlungsakte import Ermittlungsakte, ErmittlungsakteWeitergabe, ErmittlungsakteStatus
from src.services.kalender import Termin, TerminTyp, TerminStatus
from src.services.prozess import Prozess, Schriftsatz, ProzessStatus, SchriftsatzTyp
from src.services.nachrichten import Nachricht, KonversationsTeilnehmer, NachrichtTyp, NachrichtPrioritaet
from src.services.unfallskizze import Unfallskizze, SkizzenElementTyp
from src.services.versicherungen import Versicherung
from src.services.rechnung import Rechnung, RechnungsStatus, RechnungsTyp
from src.services.schadensbilder import Schadensbild, BildKategorie
from src.services.haftungsquote import HaftungsBerechnung, UnfallTyp
from src.services.datev import DATEVExport
from src.services.restwert import RestwertAnfrage, RestwertAngebot, RestwertStatus

# Neue Services (zweite Batch)
from src.services.ki_analyse import DokumentAnalyse, AnalyseTyp
from src.services.fristen import Frist, FristTyp, FristPrioritaet, FristStatus
from src.services.vergleich import Vergleichsangebot, VergleichsStatus
from src.services.email_integration import Email, EmailKonto, EmailVorlage, EmailStatus, EmailPrioritaet
from src.services.fallbericht import Fallbericht, BerichtTyp, BerichtFormat
from src.services.sprachnotizen import Sprachnotiz, SprachnotizStatus, SprachnotizKategorie
from src.services.unfallort_karte import Unfallort, StrassenTyp, UnfallortTyp
from src.services.fahrzeugbewertung import Fahrzeugbewertung, BewertungsAnbieter, BewertungsTyp, ZustandsNote
from src.services.serienbriefe import Dokumentvorlage, GeneriertesDokument, VorlageKategorie
from src.services.api import APIKey, APILog, APIBerechtigung, APIKeyStatus
from src.services.backup import Backup, BackupTyp, BackupStatus, ExportFormat
from src.services.mandanten import Mandant, MandantBenutzer, MandantStatus, LizenzTyp
from src.services.themes import BenutzerTheme, ThemeTyp
from src.services.gutachten_plausibilitaet import GutachtenPruefung, PruefungsSchwere, PruefungsKategorie
from src.services.aktenimport import (
    AktenImport, AktenDokument, AktenBeteiligter, DokumentFreigabe, Einladung,
    EinladungsStatus, BeteiligtenRolle
)

__all__ = [
    'Base',
    'Rollen', 'OrgTyp', 'MeilensteinStatus', 'KostenKategorie',
    'KostenAmpel', 'KorrespondenzRichtung', 'DokumentTyp',
    'SchreibenTyp', 'EmpfaengerTyp', 'ChatNachrichtRolle', 'ChatNachricht',
    'Organisation', 'User', 'Fahrzeug', 'UnfallProjekt',
    'Dokument', 'TimelineMeilenstein', 'KostenPosition',
    'ErsatzwagenAnbieter', 'MietfahrzeugAngebot',
    'GebuehrenBerechnung', 'Korrespondenz',
    'Wiedervorlage', 'WiedervorlageTyp', 'WiedervorlagePrioritaet',
    'AuditLog', 'AktionTyp', 'AktionKategorie',
    'Notiz', 'Mahnung', 'ChecklistenItem',
    'DigitaleSignatur', 'SignaturAnforderung',
    'UnfallaufnahmeBeteiligter',
    'DSGVOProtokoll', 'DSGVOAktionTyp',
    'Ermittlungsakte', 'ErmittlungsakteWeitergabe', 'ErmittlungsakteStatus',
    # Neue Models
    'Termin', 'TerminTyp', 'TerminStatus',
    'Prozess', 'Schriftsatz', 'ProzessStatus', 'SchriftsatzTyp',
    'Nachricht', 'KonversationsTeilnehmer', 'NachrichtTyp', 'NachrichtPrioritaet',
    'Unfallskizze', 'SkizzenElementTyp',
    'Versicherung',
    'Rechnung', 'RechnungsStatus', 'RechnungsTyp',
    'Schadensbild', 'BildKategorie',
    'HaftungsBerechnung', 'UnfallTyp',
    'DATEVExport',
    'RestwertAnfrage', 'RestwertAngebot', 'RestwertStatus',
    # Zweite Batch neue Models
    'DokumentAnalyse', 'AnalyseTyp',
    'Frist', 'FristTyp', 'FristPrioritaet', 'FristStatus',
    'Vergleichsangebot', 'VergleichsStatus',
    'Email', 'EmailKonto', 'EmailVorlage', 'EmailStatus', 'EmailPrioritaet',
    'Fallbericht', 'BerichtTyp', 'BerichtFormat',
    'Sprachnotiz', 'SprachnotizStatus', 'SprachnotizKategorie',
    'Unfallort', 'StrassenTyp', 'UnfallortTyp',
    'Fahrzeugbewertung', 'BewertungsAnbieter', 'BewertungsTyp', 'ZustandsNote',
    'Dokumentvorlage', 'GeneriertesDokument', 'VorlageKategorie',
    'APIKey', 'APILog', 'APIBerechtigung', 'APIKeyStatus',
    'Backup', 'BackupTyp', 'BackupStatus', 'ExportFormat',
    'Mandant', 'MandantBenutzer', 'MandantStatus', 'LizenzTyp',
    'BenutzerTheme', 'ThemeTyp',
    # Gutachten-Plausibilitätsprüfung
    'GutachtenPruefung', 'PruefungsSchwere', 'PruefungsKategorie',
    # Aktenimport
    'AktenImport', 'AktenDokument', 'AktenBeteiligter', 'DokumentFreigabe', 'Einladung',
    'EinladungsStatus', 'BeteiligtenRolle',
    # Zusatzdaten (TÜV, Leasing, Polizei, Bank)
    'TUVDaten', 'TUVStatus',
    'LeasingKreditbank', 'FinanzierungsTyp',
    'PolizeiDienststelle',
    'Bankverbindung',
    # Datenschutz
    'DatenschutzZustimmung', 'AKTUELLE_VERSIONEN'
]
