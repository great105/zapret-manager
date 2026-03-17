"""
HTTP-клиент для взаимодействия с сервером Zapret Manager.
Хранит client_id в %LOCALAPPDATA%/ZapretManager/.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Данные хранятся в AppData, не рядом со скриптом
APP_DIR = Path(os.environ.get("LOCALAPPDATA", ".")) / "ZapretManager"
CLIENT_ID_FILE = APP_DIR / "client_id.txt"

REQUEST_TIMEOUT = 30


class ApiClient:
    """Обёртка над REST API сервера."""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "ZapretManager/1.0",
        })
        self.client_id: str | None = self._load_client_id()

    def _load_client_id(self) -> str | None:
        if CLIENT_ID_FILE.exists():
            cid = CLIENT_ID_FILE.read_text().strip()
            return cid if cid else None
        return None

    def _save_client_id(self, client_id: str):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CLIENT_ID_FILE.write_text(client_id)
        self.client_id = client_id

    def register(self, os_version: str, hostname: str) -> str:
        """Регистрация (или возврат уже имеющегося ID)."""
        if self.client_id:
            return self.client_id

        resp = self.session.post(
            f"{self.server_url}/api/register",
            json={"os_version": os_version, "hostname": hostname},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        self._save_client_id(data["client_id"])
        logger.info("Зарегистрирован: %s", self.client_id)
        return self.client_id

    def send_diagnostics(self, report: dict[str, Any]) -> dict[str, Any]:
        """Отправить диагностику → получить конфиг."""
        resp = self.session.post(
            f"{self.server_url}/api/diagnostics",
            json=report,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def get_last_config(self) -> dict[str, Any] | None:
        if not self.client_id:
            return None
        try:
            resp = self.session.get(
                f"{self.server_url}/api/config/{self.client_id}",
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return None

    def send_feedback(self, service_id: str, success: bool, latency_ms: float | None = None):
        if not self.client_id:
            return
        try:
            self.session.post(
                f"{self.server_url}/api/feedback",
                json={
                    "client_id": self.client_id,
                    "service_id": service_id,
                    "success": success,
                    "latency_ms": latency_ms,
                },
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            pass

    def get_services(self) -> list[dict]:
        try:
            resp = self.session.get(
                f"{self.server_url}/api/services",
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return []
