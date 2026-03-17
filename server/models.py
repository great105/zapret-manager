"""
Pydantic-модели для API запросов и ответов.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Регистрация клиента ──────────────────────────────────────────────

class ClientRegisterRequest(BaseModel):
    """Первый запрос при установке приложения."""
    os_version: str = Field(..., examples=["Windows 11 Home 10.0.26200"])
    hostname: str = Field(..., examples=["DESKTOP-ABC123"])


class ClientRegisterResponse(BaseModel):
    client_id: str
    created_at: datetime


# ── Диагностика ──────────────────────────────────────────────────────

class ServiceDiagnostic(BaseModel):
    """Результат проверки одного сервиса на стороне клиента."""
    service_id: str
    domain: str
    dns_resolved: bool = True
    dns_ip: Optional[str] = None
    tcp_connect: bool = False
    tcp_latency_ms: Optional[float] = None
    tls_handshake: bool = False
    tls_error: Optional[str] = None
    http_status: Optional[int] = None
    http_redirect_to: Optional[str] = None
    rst_received: bool = False
    timeout: bool = False
    speed_kbps: Optional[float] = None


class ISPInfo(BaseModel):
    """Информация об интернет-провайдере клиента."""
    ip: str
    isp_name: str
    region: str
    city: str
    asn: Optional[str] = None


class DiagnosticReport(BaseModel):
    """Полный отчёт диагностики от клиента."""
    client_id: str
    isp: ISPInfo
    services: list[ServiceDiagnostic]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Конфигурация ─────────────────────────────────────────────────────

class ServiceStatus(BaseModel):
    """Статус конкретного сервиса в ответе."""
    service_id: str
    name: str
    icon: str
    blocked: bool
    bypass_supported: bool = True


class ConfigResponse(BaseModel):
    """Ответ сервера с конфигурацией для winws2."""
    client_id: str
    # Аргументы командной строки для winws2
    winws2_args: list[str]
    # Список доменов для hostlist
    hostlist: list[str]
    # Рекомендуемый DNS
    dns_servers: list[str] = ["8.8.8.8", "1.1.1.1"]
    # Статусы сервисов
    services: list[ServiceStatus]
    # Версия конфига (для отслеживания обновлений)
    config_version: int = 1
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Статистика ────────────────────────────────────────────────────────

class ClientStats(BaseModel):
    """Обратная связь от клиента — работает ли обход."""
    client_id: str
    service_id: str
    success: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
