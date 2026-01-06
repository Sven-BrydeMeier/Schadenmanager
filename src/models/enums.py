from enum import Enum as PyEnum


class Rollen(PyEnum):
    """Benutzerrollen im System"""
    WERKSTATT = "WERKSTATT"
    GUTACHTER = "GUTACHTER"
    VERSICHERUNG_EIGEN = "VERSICHERUNG_EIGEN"
    VERSICHERUNG_GEGNER = "VERSICHERUNG_GEGNER"
    ANWALT = "ANWALT"
    UNFALLOPFER = "UNFALLOPFER"
    ADMIN = "ADMIN"


class OrgTyp(PyEnum):
    """Organisationstypen"""
    KANZLEI = "KANZLEI"
    WERKSTATT = "WERKSTATT"
    VERSICHERUNG = "VERSICHERUNG"
    GUTACHTERBUERO = "GUTACHTERBUERO"
    ERSATZWAGENANBIETER = "ERSATZWAGENANBIETER"


class MeilensteinStatus(PyEnum):
    """Status für Timeline-Meilensteine (Ampel + Workflow)"""
    # Ampel-System
    ROT = "ROT"
    ORANGE = "ORANGE"
    GRUEN = "GRUEN"
    # Workflow-System
    ERLEDIGT = "ERLEDIGT"
    IN_BEARBEITUNG = "IN_BEARBEITUNG"
    AUSSTEHEND = "AUSSTEHEND"


class KostenKategorie(PyEnum):
    """Kategorien für Kostenpositionen"""
    REPARATUR = "REPARATUR"
    GUTACHTEN = "GUTACHTEN"
    ERSATZWAGEN = "ERSATZWAGEN"
    NUTZUNGSAUSFALL = "NUTZUNGSAUSFALL"
    WERTMINDERUNG = "WERTMINDERUNG"
    SONSTIG = "SONSTIG"
    RA_GEBUEHREN = "RA_GEBUEHREN"


class KostenAmpel(PyEnum):
    """Ampelstatus für Kostenpositionen"""
    ROT = "ROT"      # Noch nicht eingereicht
    ORANGE = "ORANGE"  # Eingereicht, Entscheidung offen
    GRUEN = "GRUEN"   # (Teilweise) freigegeben/bezahlt


class KorrespondenzRichtung(PyEnum):
    """Richtung der Korrespondenz"""
    RA_AN_VERSICHERUNG = "RA_AN_VERSICHERUNG"
    VERSICHERUNG_AN_RA = "VERSICHERUNG_AN_RA"
    RA_AN_MANDANT = "RA_AN_MANDANT"
    MANDANT_AN_RA = "MANDANT_AN_RA"
    WERKSTATT_AN_VERSICHERUNG = "WERKSTATT_AN_VERSICHERUNG"
    SONSTIG = "SONSTIG"


class DokumentTyp(PyEnum):
    """Dokumenttypen für OCR-Verarbeitung"""
    FAHRZEUGSCHEIN = "FAHRZEUGSCHEIN"
    PERSONALAUSWEIS = "PERSONALAUSWEIS"
    GUTACHTEN = "GUTACHTEN"
    RECHNUNG = "RECHNUNG"
    VERSICHERUNGSSCHREIBEN = "VERSICHERUNGSSCHREIBEN"
    KUERZUNGSSCHREIBEN = "KUERZUNGSSCHREIBEN"
    ANSPRUCHSSCHREIBEN = "ANSPRUCHSSCHREIBEN"
    VOLLMACHT = "VOLLMACHT"
    SONSTIG = "SONSTIG"


class SchreibenTyp(PyEnum):
    """Typen von generierbaren Schreiben im Dokumenten-Chat"""
    ANSPRUCHSSCHREIBEN = "ANSPRUCHSSCHREIBEN"
    KUERZUNGSERWIDERUNG = "KUERZUNGSERWIDERUNG"
    MAHNUNG = "MAHNUNG"
    MANDANTENINFORMATION = "MANDANTENINFORMATION"
    ANFRAGE = "ANFRAGE"
    STELLUNGNAHME = "STELLUNGNAHME"
    AUFFORDERUNG = "AUFFORDERUNG"
    FREIES_SCHREIBEN = "FREIES_SCHREIBEN"


class EmpfaengerTyp(PyEnum):
    """Mögliche Empfänger von Schreiben"""
    VERSICHERUNG_GEGNER = "VERSICHERUNG_GEGNER"
    VERSICHERUNG_EIGEN = "VERSICHERUNG_EIGEN"
    POLIZEI = "POLIZEI"
    STAATSANWALTSCHAFT = "STAATSANWALTSCHAFT"
    MANDANT = "MANDANT"
    GEGNER = "GEGNER"
    WERKSTATT = "WERKSTATT"
    GUTACHTER = "GUTACHTER"
    GERICHT = "GERICHT"
    SONSTIG = "SONSTIG"


class ChatNachrichtRolle(PyEnum):
    """Rolle in einer Chat-Nachricht"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EmailRichtung(PyEnum):
    """Richtung einer Email"""
    EINGEHEND = "EINGEHEND"
    AUSGEHEND = "AUSGEHEND"


class EmailStatus(PyEnum):
    """Verarbeitungsstatus einer Email"""
    NEU = "NEU"
    ZUGEORDNET = "ZUGEORDNET"
    BEARBEITET = "BEARBEITET"
    ARCHIVIERT = "ARCHIVIERT"


class EmailPrioritaet(PyEnum):
    """Priorität einer Email"""
    NIEDRIG = "NIEDRIG"
    NORMAL = "NORMAL"
    HOCH = "HOCH"
    DRINGEND = "DRINGEND"
