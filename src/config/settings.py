import os
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Anwendungskonfiguration"""

    # Datenbank
    database_url: str = Field(
        default="sqlite:///./schadenmanager.db",
        description="Datenbank-Verbindungsstring"
    )

    # Sicherheit
    secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION",
        description="Geheimer Schlüssel für Tokens"
    )
    password_min_length: int = Field(default=8)
    session_timeout_minutes: int = Field(default=60)

    # Twilio (SMS/2FA)
    twilio_account_sid: Optional[str] = Field(default=None)
    twilio_auth_token: Optional[str] = Field(default=None)
    twilio_phone_number: Optional[str] = Field(default=None)

    # KI-APIs
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    ki_provider: str = Field(default="openai", description="openai oder anthropic")

    # OCR
    tesseract_cmd: str = Field(default="/usr/bin/tesseract")

    # Upload
    upload_folder: str = Field(default="./uploads")
    max_upload_size_mb: int = Field(default=50)
    allowed_extensions: str = Field(default="pdf,png,jpg,jpeg,tiff,doc,docx")

    # E-Mail (SMTP)
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    smtp_from_email: str = Field(default="noreply@schadenmanager.de")
    smtp_use_tls: bool = Field(default=True)
    email_notifications_enabled: bool = Field(default=True)

    # App
    debug: bool = Field(default=False)
    app_name: str = Field(default="Schadenmanager")
    app_version: str = Field(default="1.0.0")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Gibt die gecachten Einstellungen zurück"""
    return Settings()
