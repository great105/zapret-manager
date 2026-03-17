"""
Управление процессом winws2 (zapret2 для Windows).

Бинарники берутся из трёх источников (в порядке приоритета):
 1. Встроены в .exe (PyInstaller _MEIPASS) → извлекаются в AppData
 2. Уже извлечены ранее в AppData
 3. Скачиваются с сервера Zapret Manager (/api/download/binaries)
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any

import psutil
import requests

logger = logging.getLogger(__name__)


def _get_bundled_dir() -> Path | None:
    """Путь к бинарникам, встроенным PyInstaller."""
    if getattr(__import__("sys"), "frozen", False):
        base = Path(getattr(__import__("sys"), "_MEIPASS"))
        bundled = base / "binaries"
        if bundled.exists():
            return bundled
    return None


class ZapretManager:
    """Управляет бинарниками и процессом winws2."""

    def __init__(self, app_dir: Path, server_url: str):
        self.app_dir = app_dir
        self.server_url = server_url.rstrip("/")

        # Рабочая директория для zapret2
        self.zapret_dir = app_dir / "zapret2"
        self.zapret_dir.mkdir(parents=True, exist_ok=True)

        # Пути к файлам
        self.winws2_exe = self.zapret_dir / "winws2.exe"
        self.windivert_dll = self.zapret_dir / "WinDivert.dll"
        self.windivert_sys = self.zapret_dir / "WinDivert64.sys"
        self.hostlist_file = self.zapret_dir / "hostlist.txt"
        self.config_file = self.zapret_dir / "current_config.json"

        self.process: subprocess.Popen | None = None

    # ── Проверка и установка бинарников ───────────────────────────────

    def check_binaries(self) -> dict[str, bool]:
        return {
            "winws2.exe": self.winws2_exe.exists(),
            "WinDivert.dll": self.windivert_dll.exists(),
            "WinDivert64.sys": self.windivert_sys.exists(),
        }

    def is_ready(self) -> bool:
        return all(self.check_binaries().values())

    def ensure_binaries(self, progress_callback=None) -> bool:
        """
        Убедиться, что бинарники на месте.
        Пробует: встроенные → уже установленные → скачать с сервера.
        Возвращает True если всё ок.
        """
        if self.is_ready():
            logger.info("Бинарники уже установлены")
            return True

        # 1. Извлечь из PyInstaller-бандла (встроены при сборке)
        bundled = _get_bundled_dir()
        if bundled:
            if progress_callback:
                progress_callback("Извлечение компонентов...")
            logger.info("Извлекаю бинарники из бандла: %s", bundled)
            for item in bundled.iterdir():
                dst = self.zapret_dir / item.name
                if not dst.exists():
                    shutil.copy2(str(item), str(dst))
                    logger.info("  + %s", item.name)
            if self.is_ready():
                logger.info("Бинарники извлечены из бандла")
                return True

        # 2. Скачать с сервера (фоллбек)
        if progress_callback:
            progress_callback("Загрузка компонентов...")
        return self._download_from_server(progress_callback)

    def _download_from_server(self, progress_callback=None) -> bool:
        """Скачать бинарники zapret2 с сервера (ZIP-архив)."""
        url = f"{self.server_url}/api/download/binaries"
        logger.info("Скачиваю бинарники с %s", url)

        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            chunks = []

            for chunk in resp.iter_content(chunk_size=65536):
                chunks.append(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    pct = int(downloaded / total * 100)
                    progress_callback(f"Загрузка: {pct}%")

            data = b"".join(chunks)

            # Распаковываем ZIP — извлекаем все файлы (exe, dll, sys, lua)
            allowed_ext = {".exe", ".dll", ".sys", ".lua"}
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for name in zf.namelist():
                    basename = Path(name).name
                    ext = Path(basename).suffix.lower()
                    if ext in allowed_ext and basename:
                        target = self.zapret_dir / basename
                        with zf.open(name) as src, open(str(target), "wb") as dst:
                            dst.write(src.read())
                        logger.info("Извлечён: %s", basename)

            if self.is_ready():
                logger.info("Бинарники успешно загружены")
                return True
            else:
                missing = [k for k, v in self.check_binaries().items() if not v]
                logger.error("После загрузки отсутствуют: %s", missing)
                return False

        except requests.RequestException as e:
            logger.error("Ошибка загрузки бинарников: %s", e)
            return False
        except zipfile.BadZipFile:
            logger.error("Сервер вернул невалидный ZIP")
            return False

    # ── Управление конфигурацией ──────────────────────────────────────

    def write_hostlist(self, domains: list[str]):
        content = "\n".join(sorted(set(domains)))
        self.hostlist_file.write_text(content, encoding="utf-8")
        logger.info("Hostlist: %d доменов", len(domains))

    def write_config(self, config: dict[str, Any]):
        self.config_file.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def load_last_config(self) -> dict[str, Any] | None:
        """Загрузить последний сохранённый конфиг (для быстрого перезапуска)."""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    # ── Управление процессом winws2 ───────────────────────────────────

    def is_running(self) -> bool:
        if self.process and self.process.poll() is None:
            return True
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and "winws2" in proc.info["name"].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def start(self, winws2_args: list[str]) -> tuple[bool, str]:
        """
        Запустить winws2. Возвращает (success, message).
        """
        if self.is_running():
            self.stop()
            time.sleep(1)

        if not self.is_ready():
            missing = [k for k, v in self.check_binaries().items() if not v]
            return False, f"Отсутствуют: {', '.join(missing)}"

        cmd = [str(self.winws2_exe)] + winws2_args
        logger.info("Запуск: %s", " ".join(cmd))

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.zapret_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time.sleep(1.5)

            if self.process.poll() is not None:
                stderr = self.process.stderr.read().decode("utf-8", errors="replace")
                logger.error("winws2 упал: %s", stderr)
                return False, f"winws2 завершился с ошибкой:\n{stderr[:200]}"

            logger.info("winws2 PID=%d", self.process.pid)
            return True, "OK"

        except PermissionError:
            return False, "Нет прав администратора"
        except FileNotFoundError:
            return False, "winws2.exe не найден"
        except Exception as e:
            return False, str(e)

    def stop(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if proc.info["name"] and "winws2" in proc.info["name"].lower():
                    proc.terminate()
                    logger.info("Остановлен winws2 PID=%d", proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
