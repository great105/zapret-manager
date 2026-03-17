"""
Система автообновления Zapret Manager.

Обновляет:
 1. Само приложение (.exe) — скачивает новый .exe, подменяет, перезапускает
 2. Бинарники zapret2 — скачивает новый ZIP, распаковывает

Версии хранятся:
 - Текущие: client/version.py (вкомпилены в .exe)
 - Локально установленные бинарники: %LOCALAPPDATA%/ZapretManager/version.json
 - Актуальные на сервере: /api/update/check
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import requests

from version import APP_VERSION, BINARIES_VERSION

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class UpdateInfo:
    """Результат проверки обновлений."""

    def __init__(self):
        self.app_update: bool = False
        self.app_new_version: str = ""
        self.binaries_update: bool = False
        self.binaries_new_version: str = ""
        self.changelog: str = ""
        self.error: str | None = None


class Updater:
    """Менеджер обновлений."""

    def __init__(self, server_url: str, app_dir: Path):
        self.server_url = server_url.rstrip("/")
        self.app_dir = app_dir
        self.update_dir = app_dir / "update"
        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.local_version_file = app_dir / "version.json"

    # ── Проверка обновлений ───────────────────────────────────────────

    def check(self) -> UpdateInfo:
        """Проверить наличие обновлений на сервере."""
        info = UpdateInfo()
        try:
            resp = requests.get(
                f"{self.server_url}/api/update/check",
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            server_app = data.get("app_version", APP_VERSION)
            server_bin = data.get("binaries_version", BINARIES_VERSION)
            info.changelog = data.get("changelog", "")

            # Сравниваем версии
            if _version_newer(server_app, APP_VERSION):
                info.app_update = True
                info.app_new_version = server_app
                logger.info("Доступно обновление приложения: %s → %s", APP_VERSION, server_app)

            local_bin = self._get_local_binaries_version()
            if _version_newer(server_bin, local_bin):
                info.binaries_update = True
                info.binaries_new_version = server_bin
                logger.info("Доступно обновление zapret2: %s → %s", local_bin, server_bin)

        except requests.RequestException as e:
            info.error = str(e)
            logger.warning("Не удалось проверить обновления: %s", e)

        return info

    # ── Обновление приложения (.exe) ──────────────────────────────────

    def update_app(self, progress_callback=None) -> bool:
        """
        Скачать новый .exe и перезапустить приложение.
        Работает только в режиме PyInstaller (.exe).
        """
        if not getattr(sys, "frozen", False):
            logger.warning("Обновление приложения доступно только для .exe сборки")
            return False

        current_exe = Path(sys.executable)
        new_exe = self.update_dir / "ZapretManager_new.exe"

        # 1. Скачиваем новый .exe
        try:
            if progress_callback:
                progress_callback("Скачивание обновления...")

            resp = requests.get(
                f"{self.server_url}/api/update/app",
                timeout=120,
                stream=True,
            )
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(str(new_exe), "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        pct = int(downloaded / total * 100)
                        progress_callback(f"Скачивание: {pct}%")

        except requests.RequestException as e:
            logger.error("Ошибка скачивания обновления: %s", e)
            return False

        # 2. Создаём батник для замены и перезапуска
        bat_path = self.update_dir / "update.bat"
        bat_content = f'''@echo off
chcp 65001 >nul
echo Обновление Zapret Manager...
timeout /t 2 /nobreak >nul
copy /y "{new_exe}" "{current_exe}"
del "{new_exe}"
start "" "{current_exe}"
del "%~f0"
'''
        bat_path.write_text(bat_content, encoding="utf-8")

        # 3. Запускаем батник и выходим
        if progress_callback:
            progress_callback("Перезапуск...")

        subprocess.Popen(
            ["cmd", "/c", str(bat_path)],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        sys.exit(0)

    # ── Обновление бинарников zapret2 ─────────────────────────────────

    def update_binaries(self, zapret_manager, progress_callback=None) -> bool:
        """
        Скачать новые бинарники zapret2 с сервера.
        Использует ZapretManager._download_from_server().
        """
        # Останавливаем winws2 перед обновлением
        if zapret_manager.is_running():
            zapret_manager.stop()

        ok = zapret_manager._download_from_server(progress_callback)
        if ok:
            # Сохраняем новую версию
            try:
                resp = requests.get(
                    f"{self.server_url}/api/update/check",
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                server_bin = resp.json().get("binaries_version", BINARIES_VERSION)
                self._save_local_binaries_version(server_bin)
            except requests.RequestException:
                pass
        return ok

    # ── Локальное версионирование бинарников ──────────────────────────

    def _get_local_binaries_version(self) -> str:
        """Получить версию локально установленных бинарников."""
        if self.local_version_file.exists():
            try:
                data = json.loads(self.local_version_file.read_text(encoding="utf-8"))
                return data.get("binaries_version", BINARIES_VERSION)
            except (json.JSONDecodeError, OSError):
                pass
        return BINARIES_VERSION

    def _save_local_binaries_version(self, version: str):
        """Сохранить версию бинарников после обновления."""
        data = {"binaries_version": version, "app_version": APP_VERSION}
        self.local_version_file.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def save_initial_version(self):
        """Сохранить версию при первом запуске (после извлечения из бандла)."""
        if not self.local_version_file.exists():
            self._save_local_binaries_version(BINARIES_VERSION)


def _version_newer(new: str, current: str) -> bool:
    """Сравнить версии формата X.Y.Z. True если new > current."""
    try:
        new_parts = [int(x) for x in new.split(".")]
        cur_parts = [int(x) for x in current.split(".")]
        return new_parts > cur_parts
    except (ValueError, AttributeError):
        return False
