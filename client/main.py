"""
Точка входа клиента Zapret Manager.

При запуске:
 1. Проверяет права администратора → если нет, перезапускает себя через UAC
 2. Инициализирует логирование в %LOCALAPPDATA%
 3. Запускает GUI
"""

import ctypes
import logging
import os
import sys
from pathlib import Path

# ── Адрес сервера (ИЗМЕНИ НА СВОЙ!) ──────────────────────────────────

SERVER_URL = "http://localhost:8000"

# ── Рабочая директория в AppData ──────────────────────────────────────

APP_DIR = Path(os.environ.get("LOCALAPPDATA", ".")) / "ZapretManager"
APP_DIR.mkdir(parents=True, exist_ok=True)


def is_admin() -> bool:
    """Проверка прав администратора (Windows)."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate():
    """Перезапуск с правами администратора через UAC."""
    # Если мы .exe (PyInstaller) — запускаем сам .exe
    # Если скрипт — запускаем python с этим скриптом
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = " ".join(sys.argv[1:])
    else:
        executable = sys.executable
        params = f'"{os.path.abspath(__file__)}"'

    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, params, None, 1
    )
    sys.exit(0)


def setup_logging():
    """Настройка логирования в файл в AppData."""
    log_file = APP_DIR / "zapret_manager.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )


def main():
    # 1. Проверяем права администратора — если нет, запрашиваем через UAC
    if not is_admin():
        elevate()
        return  # сюда не дойдём (sys.exit в elevate)

    # 2. Логирование
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Zapret Manager запущен с правами администратора")
    logger.info("Рабочая директория: %s", APP_DIR)
    logger.info("Сервер: %s", SERVER_URL)

    # 3. Запускаем GUI
    from gui import App
    app = App(server_url=SERVER_URL, app_dir=APP_DIR)
    app.mainloop()


if __name__ == "__main__":
    main()
