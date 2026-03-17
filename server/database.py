"""
База данных — SQLAlchemy + SQLite.
Хранит клиентов, их диагностики и выданные конфигурации.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class Client(Base):
    """Зарегистрированный клиент."""
    __tablename__ = "clients"

    id = Column(String(36), primary_key=True)             # UUID
    os_version = Column(String(128))
    hostname = Column(String(128))
    isp_name = Column(String(128), nullable=True)
    isp_ip = Column(String(45), nullable=True)
    region = Column(String(128), nullable=True)
    city = Column(String(128), nullable=True)
    asn = Column(String(32), nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class DiagnosticRecord(Base):
    """Одна запись диагностики (один отчёт от клиента)."""
    __tablename__ = "diagnostics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(36), index=True)
    isp_name = Column(String(128))
    region = Column(String(128))
    # JSON-массив ServiceDiagnostic
    services_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def get_services(self) -> list[dict]:
        return json.loads(self.services_json) if self.services_json else []


class IssuedConfig(Base):
    """Конфигурация, выданная клиенту."""
    __tablename__ = "issued_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(36), index=True)
    winws2_args_json = Column(Text)           # JSON-массив аргументов
    hostlist_json = Column(Text)              # JSON-массив доменов
    config_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    def get_args(self) -> list[str]:
        return json.loads(self.winws2_args_json) if self.winws2_args_json else []

    def get_hostlist(self) -> list[str]:
        return json.loads(self.hostlist_json) if self.hostlist_json else []


class StrategyFeedback(Base):
    """Обратная связь — сработала ли стратегия."""
    __tablename__ = "strategy_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(36), index=True)
    isp_name = Column(String(128))
    region = Column(String(128))
    service_id = Column(String(64))
    strategy_hash = Column(String(64))        # хеш конфига для группировки
    success = Column(Boolean)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Инициализация БД ─────────────────────────────────────────────────

DATABASE_URL = "sqlite:///./zapret_server.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Создать все таблицы."""
    Base.metadata.create_all(engine)


def get_db() -> Session:
    """Получить сессию БД (для FastAPI Depends)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
