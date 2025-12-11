from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.config.settings import get_settings
from src.models.base import Base


# Engine und Session-Factory als globale Variablen
_engine = None
_SessionLocal = None


def get_engine():
    """Gibt die Datenbank-Engine zurück (erstellt sie bei Bedarf)"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True
        )
    return _engine


def get_session_factory():
    """Gibt die Session-Factory zurück"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _SessionLocal


def init_db():
    """Initialisiert die Datenbank (erstellt alle Tabellen)"""
    # Importiere alle Modelle, damit sie registriert werden
    from src.models import (
        Organisation, User, Fahrzeug, UnfallProjekt,
        Dokument, TimelineMeilenstein, KostenPosition,
        ErsatzwagenAnbieter, MietfahrzeugAngebot,
        GebuehrenBerechnung, Korrespondenz
    )

    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Generator für Datenbank-Sessions (für Dependency Injection)"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context Manager für Datenbank-Sessions"""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
