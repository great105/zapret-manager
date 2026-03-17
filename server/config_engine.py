"""
Движок генерации конфигурации zapret2 (winws2) для Windows.

На основе диагностики клиента подбирает стратегии обхода DPI:
 - multidisorder / multisplit для TLS (HTTPS)
 - fake-пакеты для сложных DPI
 - ipfrag для фрагментации
 - http_hostcase / multisplit для HTTP
 - UDP desync для QUIC (YouTube, Discord voice)

Стратегии ранжируются по ISP и типу блокировки.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from models import DiagnosticReport, ServiceDiagnostic, ConfigResponse, ServiceStatus
from services import get_all_services, get_all_domains, get_service_by_id


# ── Предопределённые стратегии ────────────────────────────────────────

@dataclass
class Strategy:
    """Набор аргументов winws2 для одного профиля."""
    name: str
    description: str
    args: list[str]
    priority: int = 0  # чем выше, тем приоритетнее


# Стратегии для TLS (HTTPS) — порт 443
TLS_STRATEGIES = [
    Strategy(
        name="tls_multidisorder",
        description="Переупорядочивание TCP-сегментов TLS ClientHello",
        args=[
            "--filter-tcp=443",
            "--filter-l7=tls",
            "--payload=tls_client_hello",
            "--out-range=-s32768",
            "--lua-desync=multidisorder:strategy=2",
        ],
        priority=100,
    ),
    Strategy(
        name="tls_multisplit",
        description="Разделение TLS ClientHello на сегменты",
        args=[
            "--filter-tcp=443",
            "--filter-l7=tls",
            "--payload=tls_client_hello",
            "--out-range=-s32768",
            "--lua-desync=multisplit",
        ],
        priority=90,
    ),
    Strategy(
        name="tls_fake_disorder",
        description="Fake-пакет + disorder для обхода сложного DPI",
        args=[
            "--filter-tcp=443",
            "--filter-l7=tls",
            "--payload=tls_client_hello",
            "--out-range=-s32768",
            "--lua-desync=fake:blob=fake_tls:strategy=1",
            "--lua-desync=multidisorder:strategy=2",
        ],
        priority=80,
    ),
    Strategy(
        name="tls_fake_only",
        description="Fake TLS пакет с плохой контрольной суммой",
        args=[
            "--filter-tcp=443",
            "--filter-l7=tls",
            "--payload=tls_client_hello",
            "--lua-desync=fake:blob=fake_tls:badsum:strategy=1",
        ],
        priority=70,
    ),
]

# Стратегии для HTTP — порт 80
HTTP_STRATEGIES = [
    Strategy(
        name="http_multisplit",
        description="Разделение HTTP-запроса",
        args=[
            "--filter-tcp=80",
            "--filter-l7=http",
            "--payload=http_req",
            "--lua-desync=multisplit",
        ],
        priority=100,
    ),
    Strategy(
        name="http_fake_split",
        description="Fake + split HTTP-запроса",
        args=[
            "--filter-tcp=80",
            "--filter-l7=http",
            "--payload=http_req",
            "--lua-desync=fake:blob=fake_http:strategy=1",
            "--lua-desync=multisplit",
        ],
        priority=90,
    ),
    Strategy(
        name="http_hostcase",
        description="Изменение регистра Host-заголовка",
        args=[
            "--filter-tcp=80",
            "--filter-l7=http",
            "--payload=http_req",
            "--lua-desync=http_hostcase",
        ],
        priority=80,
    ),
]

# Стратегии для QUIC (UDP 443) — YouTube, Discord голос
QUIC_STRATEGIES = [
    Strategy(
        name="quic_fake",
        description="Fake-пакет для QUIC Initial",
        args=[
            "--filter-udp=443",
            "--filter-l7=quic",
            "--lua-desync=fake:strategy=1",
        ],
        priority=100,
    ),
]


# ── Профили ISP ───────────────────────────────────────────────────────
# Какие стратегии лучше работают для конкретных провайдеров.
# Ключ — подстрока в названии ISP (lowercase).

ISP_STRATEGY_OVERRIDES: dict[str, dict[str, str]] = {
    "rostelecom": {
        "tls": "tls_fake_disorder",
        "http": "http_fake_split",
        "quic": "quic_fake",
    },
    "ростелеком": {
        "tls": "tls_fake_disorder",
        "http": "http_fake_split",
        "quic": "quic_fake",
    },
    "mts": {
        "tls": "tls_multidisorder",
        "http": "http_multisplit",
        "quic": "quic_fake",
    },
    "мтс": {
        "tls": "tls_multidisorder",
        "http": "http_multisplit",
        "quic": "quic_fake",
    },
    "beeline": {
        "tls": "tls_multisplit",
        "http": "http_multisplit",
        "quic": "quic_fake",
    },
    "билайн": {
        "tls": "tls_multisplit",
        "http": "http_multisplit",
        "quic": "quic_fake",
    },
    "megafon": {
        "tls": "tls_multidisorder",
        "http": "http_hostcase",
        "quic": "quic_fake",
    },
    "мегафон": {
        "tls": "tls_multidisorder",
        "http": "http_hostcase",
        "quic": "quic_fake",
    },
    "tele2": {
        "tls": "tls_multidisorder",
        "http": "http_multisplit",
        "quic": "quic_fake",
    },
    "теле2": {
        "tls": "tls_multidisorder",
        "http": "http_multisplit",
        "quic": "quic_fake",
    },
    "dom.ru": {
        "tls": "tls_fake_disorder",
        "http": "http_fake_split",
        "quic": "quic_fake",
    },
    "дом.ru": {
        "tls": "tls_fake_disorder",
        "http": "http_fake_split",
        "quic": "quic_fake",
    },
}


def _find_strategy(strategies: list[Strategy], name: str) -> Strategy | None:
    for s in strategies:
        if s.name == name:
            return s
    return None


def _best_strategy(strategies: list[Strategy]) -> Strategy:
    return max(strategies, key=lambda s: s.priority)


def _select_tls_strategy(isp_name: str) -> Strategy:
    isp_lower = isp_name.lower()
    for key, overrides in ISP_STRATEGY_OVERRIDES.items():
        if key in isp_lower:
            found = _find_strategy(TLS_STRATEGIES, overrides["tls"])
            if found:
                return found
    return _best_strategy(TLS_STRATEGIES)


def _select_http_strategy(isp_name: str) -> Strategy:
    isp_lower = isp_name.lower()
    for key, overrides in ISP_STRATEGY_OVERRIDES.items():
        if key in isp_lower:
            found = _find_strategy(HTTP_STRATEGIES, overrides["http"])
            if found:
                return found
    return _best_strategy(HTTP_STRATEGIES)


def _select_quic_strategy(isp_name: str) -> Strategy:
    isp_lower = isp_name.lower()
    for key, overrides in ISP_STRATEGY_OVERRIDES.items():
        if key in isp_lower:
            found = _find_strategy(QUIC_STRATEGIES, overrides["quic"])
            if found:
                return found
    return _best_strategy(QUIC_STRATEGIES)


# ── Основная функция генерации конфига ────────────────────────────────

def generate_config(report: DiagnosticReport) -> ConfigResponse:
    """
    Принимает DiagnosticReport, возвращает ConfigResponse с аргументами winws2.

    Логика:
    1. Определяем, какие сервисы заблокированы (по результатам диагностики).
    2. Собираем все домены заблокированных сервисов в hostlist.
    3. Определяем, нужны ли TCP 443 (TLS), TCP 80 (HTTP), UDP 443 (QUIC).
    4. Подбираем стратегии в зависимости от ISP.
    5. Собираем аргументы winws2 для Windows.
    """

    isp_name = report.isp.isp_name
    blocked_service_ids: set[str] = set()
    needs_tls = False
    needs_http = False
    needs_quic = False

    # Анализ диагностики — определяем, что заблокировано
    for diag in report.services:
        is_blocked = _is_service_blocked(diag)
        if is_blocked:
            blocked_service_ids.add(diag.service_id)
            svc = get_service_by_id(diag.service_id)
            if svc:
                ports = svc.get("ports", {})
                if 443 in ports.get("tcp", []):
                    needs_tls = True
                if 80 in ports.get("tcp", []):
                    needs_http = True
                if 443 in ports.get("udp", []):
                    needs_quic = True

    # Если ничего не заблокировано — всё равно даём базовый конфиг
    if not blocked_service_ids:
        # Добавляем все известные заблокированные сервисы
        for svc in get_all_services():
            blocked_service_ids.add(svc["id"])
        needs_tls = True
        needs_http = True
        needs_quic = True

    # Собираем hostlist — все домены заблокированных сервисов
    hostlist: list[str] = []
    for svc in get_all_services():
        if svc["id"] in blocked_service_ids:
            hostlist.extend(svc["domains"])
    hostlist = sorted(set(hostlist))

    # Собираем аргументы winws2
    winws2_args: list[str] = []

    # Lua-скрипты (обязательно первыми! @ = загрузка из файла)
    winws2_args.append("--lua-init=@zapret-lib.lua")
    winws2_args.append("--lua-init=@zapret-antidpi.lua")

    # WinDivert фильтры (Windows-специфичные)
    wf_parts = []
    if needs_tls:
        wf_parts.append("--wf-tcp-out=80,443")
    elif needs_http:
        wf_parts.append("--wf-tcp-out=80")
    if needs_quic:
        wf_parts.append("--wf-udp-out=443")

    winws2_args.extend(wf_parts)

    # Hostlist файл (будет записан клиентом)
    winws2_args.append("--hostlist=hostlist.txt")

    # TLS стратегия
    if needs_tls:
        tls_strategy = _select_tls_strategy(isp_name)
        winws2_args.extend(tls_strategy.args)

    # HTTP стратегия (через --new для нового профиля)
    if needs_http:
        winws2_args.append("--new")
        http_strategy = _select_http_strategy(isp_name)
        winws2_args.extend(http_strategy.args)

    # QUIC стратегия
    if needs_quic:
        winws2_args.append("--new")
        quic_strategy = _select_quic_strategy(isp_name)
        winws2_args.extend(quic_strategy.args)

    # Статусы сервисов
    services_status: list[ServiceStatus] = []
    for svc in get_all_services():
        services_status.append(ServiceStatus(
            service_id=svc["id"],
            name=svc["name"],
            icon=svc["icon"],
            blocked=svc["id"] in blocked_service_ids,
            bypass_supported=True,
        ))

    # Версия конфига — хеш от аргументов
    config_hash = hashlib.md5(json.dumps(winws2_args).encode()).hexdigest()
    config_version = int(config_hash[:8], 16) % 100000

    return ConfigResponse(
        client_id=report.client_id,
        winws2_args=winws2_args,
        hostlist=hostlist,
        dns_servers=["8.8.8.8", "1.1.1.1"],
        services=services_status,
        config_version=config_version,
    )


def _is_service_blocked(diag: ServiceDiagnostic) -> bool:
    """Определяем, заблокирован ли сервис по результатам проверки."""
    # Если DNS не резолвится — блокировка на уровне DNS
    if not diag.dns_resolved:
        return True
    # Если TCP не подключается
    if not diag.tcp_connect:
        return True
    # Если TLS handshake не прошёл
    if not diag.tls_handshake:
        return True
    # Если получили RST — DPI сбрасывает соединение
    if diag.rst_received:
        return True
    # Если таймаут — замедление/блокировка
    if diag.timeout:
        return True
    # Если HTTP redirect на другой домен (страница блокировки)
    if diag.http_redirect_to and diag.http_status in (301, 302, 307):
        return True
    # Если скорость очень низкая — замедление (< 100 кбит/с)
    if diag.speed_kbps is not None and diag.speed_kbps < 100:
        return True
    return False
