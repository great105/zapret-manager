"""
Скрипт для скачивания бинарников zapret2 с GitHub.

Запусти перед сборкой .exe:
    python download_zapret2.py

Скачает winws2.exe, WinDivert.dll, WinDivert64.sys в папку binaries/
"""

import io
import os
import sys
import zipfile
from pathlib import Path

import requests

GITHUB_API = "https://api.github.com/repos/bol-van/zapret2/releases/latest"
BINARIES_DIR = Path(__file__).parent / "binaries"

# Файлы, которые нужны для Windows
NEEDED_FILES = {
    "winws2.exe",
    "WinDivert.dll",
    "WinDivert64.sys",
}


def get_latest_release() -> dict:
    """Получить информацию о последнем релизе zapret2."""
    print("Запрос последнего релиза zapret2...")
    resp = requests.get(GITHUB_API, timeout=30)
    resp.raise_for_status()
    return resp.json()


def find_windows_asset(release: dict) -> str | None:
    """Найти ссылку на Windows-архив в релизе."""
    for asset in release.get("assets", []):
        name = asset["name"].lower()
        # Ищем архив для Windows (обычно содержит win или x86_64-w64)
        if ("win" in name or "w64" in name) and name.endswith(".zip"):
            return asset["browser_download_url"]
    return None


def download_and_extract(url: str):
    """Скачать ZIP и извлечь нужные файлы."""
    print(f"Скачиваю: {url}")
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    chunks = []

    for chunk in resp.iter_content(chunk_size=65536):
        chunks.append(chunk)
        downloaded += len(chunk)
        if total:
            pct = int(downloaded / total * 100)
            print(f"\r  Прогресс: {pct}% ({downloaded // 1024} KB)", end="", flush=True)

    print()
    data = b"".join(chunks)

    BINARIES_DIR.mkdir(parents=True, exist_ok=True)

    print("Распаковка...")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        extracted = 0
        for name in zf.namelist():
            basename = Path(name).name
            if basename in NEEDED_FILES:
                target = BINARIES_DIR / basename
                with zf.open(name) as src, open(str(target), "wb") as dst:
                    dst.write(src.read())
                print(f"  + {basename} ({target.stat().st_size // 1024} KB)")
                extracted += 1

            # Также извлекаем .lua файлы (стратегии)
            if basename.endswith(".lua"):
                target = BINARIES_DIR / basename
                with zf.open(name) as src, open(str(target), "wb") as dst:
                    dst.write(src.read())
                print(f"  + {basename}")

        if extracted == 0:
            print("\nВНИМАНИЕ: нужные файлы не найдены в архиве!")
            print("Содержимое архива:")
            for name in zf.namelist():
                print(f"  {name}")


def main():
    print("=" * 50)
    print("  Скачивание бинарников zapret2 для Windows")
    print("=" * 50)
    print()

    try:
        release = get_latest_release()
        tag = release.get("tag_name", "unknown")
        print(f"Последний релиз: {tag}")
        print()

        url = find_windows_asset(release)
        if not url:
            print("Не найден Windows-архив в релизе.")
            print("Доступные файлы:")
            for asset in release.get("assets", []):
                print(f"  {asset['name']} — {asset['browser_download_url']}")
            print()
            print("Скачайте нужный архив вручную и распакуйте в:")
            print(f"  {BINARIES_DIR}")
            sys.exit(1)

        download_and_extract(url)

        print()
        # Проверяем
        missing = []
        for f in NEEDED_FILES:
            if not (BINARIES_DIR / f).exists():
                missing.append(f)

        if missing:
            print(f"ОШИБКА: не найдены: {', '.join(missing)}")
            print("Скачайте их вручную и положите в:")
            print(f"  {BINARIES_DIR}")
            sys.exit(1)
        else:
            print("Все файлы на месте!")
            print(f"Папка: {BINARIES_DIR}")
            print()
            print("Теперь можно собирать .exe:")
            print("  build.bat")

    except requests.RequestException as e:
        print(f"Ошибка сети: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
