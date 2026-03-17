"""
Сбор сетевой диагностики на стороне клиента.

Определяет:
 - ISP (провайдер, IP, регион)
 - Доступность DNS
 - TCP-соединения с заблокированными сервисами
 - TLS handshake
 - Наличие RST / таймаутов
"""

from __future__ import annotations

import logging
import platform
import socket
import ssl
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Таймаут для отдельных проверок (секунды)
CHECK_TIMEOUT = 5


def get_system_info() -> dict[str, str]:
    """Информация об ОС и хосте."""
    return {
        "os_version": f"{platform.system()} {platform.version()}",
        "hostname": platform.node(),
    }


def detect_isp() -> dict[str, Any]:
    """
    Определяем ISP через публичный API.
    Возвращает ISPInfo-совместимый словарь.
    """
    try:
        resp = requests.get("http://ip-api.com/json/?lang=ru", timeout=CHECK_TIMEOUT)
        data = resp.json()
        return {
            "ip": data.get("query", "unknown"),
            "isp_name": data.get("isp", "unknown"),
            "region": data.get("regionName", "unknown"),
            "city": data.get("city", "unknown"),
            "asn": data.get("as", "").split()[0] if data.get("as") else None,
        }
    except Exception as e:
        logger.warning("Не удалось определить ISP: %s", e)
        return {
            "ip": "unknown",
            "isp_name": "unknown",
            "region": "unknown",
            "city": "unknown",
            "asn": None,
        }


def check_dns(domain: str) -> tuple[bool, str | None]:
    """
    Проверка DNS-резолвинга.
    Возвращает (resolved: bool, ip: str | None).
    """
    try:
        ip = socket.gethostbyname(domain)
        return True, ip
    except socket.gaierror:
        return False, None


def check_tcp(domain: str, port: int = 443) -> tuple[bool, float | None]:
    """
    Проверка TCP-соединения.
    Возвращает (connected: bool, latency_ms: float | None).
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(CHECK_TIMEOUT)
        start = time.monotonic()
        result = sock.connect_ex((domain, port))
        elapsed = (time.monotonic() - start) * 1000
        sock.close()
        if result == 0:
            return True, round(elapsed, 1)
        return False, None
    except (socket.timeout, OSError):
        return False, None


def check_tls(domain: str, port: int = 443) -> tuple[bool, str | None]:
    """
    Проверка TLS handshake.
    Возвращает (success: bool, error: str | None).
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=CHECK_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                ssock.do_handshake()
                return True, None
    except ssl.SSLError as e:
        return False, f"SSL: {e.reason}"
    except (socket.timeout, ConnectionResetError):
        return False, "timeout/reset"
    except OSError as e:
        return False, str(e)


def check_http(domain: str) -> tuple[int | None, str | None, bool]:
    """
    Проверка HTTP(S) запроса.
    Возвращает (status_code, redirect_url, timeout).
    """
    try:
        resp = requests.get(
            f"https://{domain}",
            timeout=CHECK_TIMEOUT,
            allow_redirects=False,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        redirect_to = None
        if resp.status_code in (301, 302, 307, 308):
            redirect_to = resp.headers.get("Location", "")
        return resp.status_code, redirect_to, False
    except requests.Timeout:
        return None, None, True
    except requests.ConnectionError:
        return None, None, False
    except Exception:
        return None, None, False


def check_service(service: dict) -> dict[str, Any]:
    """
    Полная проверка одного сервиса.
    Принимает словарь сервиса из services.py.
    Возвращает ServiceDiagnostic-совместимый словарь.
    """
    domain = service["test_domain"]
    service_id = service["id"]

    logger.info("Проверяю %s (%s)...", service["name"], domain)

    # DNS
    dns_ok, dns_ip = check_dns(domain)

    # TCP
    tcp_ok, tcp_latency = False, None
    if dns_ok:
        tcp_ok, tcp_latency = check_tcp(domain, 443)

    # TLS
    tls_ok, tls_error = False, None
    if tcp_ok:
        tls_ok, tls_error = check_tls(domain, 443)

    # HTTP
    http_status, redirect_to, is_timeout = None, None, False
    if dns_ok:
        http_status, redirect_to, is_timeout = check_http(domain)

    # Определяем RST (если TCP не подключился, но DNS работает)
    rst_received = dns_ok and not tcp_ok and not is_timeout

    return {
        "service_id": service_id,
        "domain": domain,
        "dns_resolved": dns_ok,
        "dns_ip": dns_ip,
        "tcp_connect": tcp_ok,
        "tcp_latency_ms": tcp_latency,
        "tls_handshake": tls_ok,
        "tls_error": tls_error,
        "http_status": http_status,
        "http_redirect_to": redirect_to,
        "rst_received": rst_received,
        "timeout": is_timeout,
        "speed_kbps": None,  # TODO: добавить тест скорости для YouTube
    }


def run_full_diagnostics(services: list[dict], progress_callback=None) -> dict[str, Any]:
    """
    Запуск полной диагностики по всем сервисам.

    Args:
        services: список сервисов из services.py
        progress_callback: функция(current, total, service_name) для обновления прогресса

    Returns:
        Словарь, совместимый с DiagnosticReport (без client_id — добавляется позже).
    """
    sys_info = get_system_info()
    isp_info = detect_isp()

    results = []
    total = len(services)
    for i, svc in enumerate(services):
        if progress_callback:
            progress_callback(i, total, svc["name"])
        result = check_service(svc)
        results.append(result)

    if progress_callback:
        progress_callback(total, total, "Готово")

    return {
        "isp": isp_info,
        "services": results,
        "system": sys_info,
    }
