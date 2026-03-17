"""
Движок генерации конфигурации zapret2 (winws2) для Windows.

Подбирает стратегии обхода DPI по ISP и типу блокировки.
Честно помечает сервисы с IP-блокировкой как неподдерживаемые.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from models import DiagnosticReport, ServiceDiagnostic, ConfigResponse, ServiceStatus
from services import get_all_services, get_service_by_id


@dataclass
class Strategy:
    name: str
    args: list[str]
    priority: int = 0


# ── TLS стратегии (TCP 443) ──────────────────────────────────────────

TLS_STRATEGIES = [
    # Агрессивный: fake + multidisorder (лучше для Discord, сложных блокировок)
    Strategy("tls_aggressive", [
        "--filter-tcp=443",
        "--filter-l7=tls",
        "--payload=tls_client_hello",
        "--out-range=-s32768",
        "--lua-desync=fake:blob=fake_tls:strategy=1",
        "--lua-desync=multidisorder:strategy=2",
    ], priority=100),

    Strategy("tls_multidisorder", [
        "--filter-tcp=443",
        "--filter-l7=tls",
        "--payload=tls_client_hello",
        "--out-range=-s32768",
        "--lua-desync=multidisorder:strategy=2",
    ], priority=90),

    Strategy("tls_multisplit", [
        "--filter-tcp=443",
        "--filter-l7=tls",
        "--payload=tls_client_hello",
        "--out-range=-s32768",
        "--lua-desync=multisplit",
    ], priority=80),

    Strategy("tls_fake_badsum", [
        "--filter-tcp=443",
        "--filter-l7=tls",
        "--payload=tls_client_hello",
        "--lua-desync=fake:blob=fake_tls:badsum:strategy=1",
    ], priority=70),
]

# ── HTTP стратегии (TCP 80) ──────────────────────────────────────────

HTTP_STRATEGIES = [
    Strategy("http_fake_split", [
        "--filter-tcp=80",
        "--filter-l7=http",
        "--payload=http_req",
        "--lua-desync=fake:blob=fake_http:strategy=1",
        "--lua-desync=multisplit",
    ], priority=100),

    Strategy("http_multisplit", [
        "--filter-tcp=80",
        "--filter-l7=http",
        "--payload=http_req",
        "--lua-desync=multisplit",
    ], priority=90),

    Strategy("http_hostcase", [
        "--filter-tcp=80",
        "--filter-l7=http",
        "--payload=http_req",
        "--lua-desync=http_hostcase",
    ], priority=80),
]

# ── QUIC стратегии (UDP 443) — YouTube, Discord voice ────────────────

QUIC_STRATEGIES = [
    Strategy("quic_fake", [
        "--filter-udp=443",
        "--filter-l7=quic",
        "--lua-desync=fake:strategy=1",
    ], priority=100),
]

# ── Профили ISP ───────────────────────────────────────────────────────

ISP_OVERRIDES = {
    "rostelecom":  {"tls": "tls_aggressive"},
    "ростелеком":  {"tls": "tls_aggressive"},
    "mts":         {"tls": "tls_aggressive"},
    "мтс":         {"tls": "tls_aggressive"},
    "beeline":     {"tls": "tls_multisplit"},
    "билайн":      {"tls": "tls_multisplit"},
    "megafon":     {"tls": "tls_multidisorder"},
    "мегафон":     {"tls": "tls_multidisorder"},
    "tele2":       {"tls": "tls_multidisorder"},
    "теле2":       {"tls": "tls_multidisorder"},
    "dom.ru":      {"tls": "tls_aggressive"},
    "дом.ru":      {"tls": "tls_aggressive"},
}


def _find(strategies, name):
    for s in strategies:
        if s.name == name:
            return s
    return max(strategies, key=lambda s: s.priority)


def _pick_tls(isp):
    isp_l = isp.lower()
    for key, ov in ISP_OVERRIDES.items():
        if key in isp_l and "tls" in ov:
            return _find(TLS_STRATEGIES, ov["tls"])
    return _find(TLS_STRATEGIES, "tls_aggressive")  # default: aggressive


# ── Генерация конфига ─────────────────────────────────────────────────

def generate_config(report: DiagnosticReport) -> ConfigResponse:
    isp_name = report.isp.isp_name
    blocked_ids: set[str] = set()

    for diag in report.services:
        if _is_blocked(diag):
            blocked_ids.add(diag.service_id)

    # Если ничего не заблокировано — добавляем все
    if not blocked_ids:
        for svc in get_all_services():
            blocked_ids.add(svc["id"])

    # Собираем hostlist только из DPI-обходимых сервисов
    hostlist = []
    needs_tls = False
    needs_http = False
    needs_quic = False

    for svc in get_all_services():
        if svc["id"] not in blocked_ids:
            continue
        bypass = svc.get("bypass_method", "dpi")
        if bypass in ("dpi", "mixed"):
            hostlist.extend(svc["domains"])
            ports = svc.get("ports", {})
            if 443 in ports.get("tcp", []):
                needs_tls = True
            if 80 in ports.get("tcp", []):
                needs_http = True
            if 443 in ports.get("udp", []):
                needs_quic = True

    hostlist = sorted(set(hostlist))

    # Если нет DPI-обходимых сервисов, всё равно даём базовый конфиг
    if not hostlist:
        needs_tls = True
        needs_http = True
        needs_quic = True
        for svc in get_all_services():
            hostlist.extend(svc["domains"])
        hostlist = sorted(set(hostlist))

    # Собираем аргументы winws2
    args = []

    # Lua-скрипты
    args.append("--lua-init=@zapret-lib.lua")
    args.append("--lua-init=@zapret-antidpi.lua")

    # WinDivert фильтры
    if needs_tls or needs_http:
        ports = set()
        if needs_tls:
            ports.update([80, 443])
        elif needs_http:
            ports.add(80)
        args.append(f"--wf-tcp-out={','.join(str(p) for p in sorted(ports))}")
    if needs_quic:
        args.append("--wf-udp-out=443")

    # Hostlist
    args.append("--hostlist=hostlist.txt")

    # Профиль 1: TLS (основной — Discord, YouTube, и др.)
    if needs_tls:
        tls = _pick_tls(isp_name)
        args.extend(tls.args)

    # Профиль 2: HTTP
    if needs_http:
        args.append("--new")
        http = _find(HTTP_STRATEGIES, "http_fake_split")
        args.extend(http.args)

    # Профиль 3: QUIC/UDP (YouTube video, Discord voice)
    if needs_quic:
        args.append("--new")
        quic = _find(QUIC_STRATEGIES, "quic_fake")
        args.extend(quic.args)

    # Статусы сервисов — честно помечаем что можно обойти
    services_status = []
    for svc in get_all_services():
        bypass = svc.get("bypass_method", "dpi")
        is_blocked = svc["id"] in blocked_ids
        can_bypass = bypass in ("dpi", "mixed")

        services_status.append(ServiceStatus(
            service_id=svc["id"],
            name=svc["name"],
            icon=svc.get("icon", ""),
            blocked=is_blocked,
            bypass_supported=can_bypass,
        ))

    config_hash = hashlib.md5(json.dumps(args).encode()).hexdigest()

    return ConfigResponse(
        client_id=report.client_id,
        winws2_args=args,
        hostlist=hostlist,
        dns_servers=["8.8.8.8", "1.1.1.1"],
        services=services_status,
        config_version=int(config_hash[:8], 16) % 100000,
    )


def _is_blocked(diag: ServiceDiagnostic) -> bool:
    if not diag.dns_resolved:
        return True
    if not diag.tcp_connect:
        return True
    if not diag.tls_handshake:
        return True
    if diag.rst_received:
        return True
    if diag.timeout:
        return True
    if diag.http_redirect_to and diag.http_status in (301, 302, 307):
        return True
    if diag.speed_kbps is not None and diag.speed_kbps < 100:
        return True
    return False
