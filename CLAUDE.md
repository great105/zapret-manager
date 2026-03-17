# Zapret Manager

## Описание проекта

Система автоматического обхода интернет-блокировок на базе zapret2 (winws2).
Клиент-серверная архитектура: пользователь ставит один .exe, нажимает кнопку — всё работает.

## Архитектура

### Клиент (`client/`)
- **Python + customtkinter** — GUI с тёмной темой
- **PyInstaller** — сборка в один .exe с встроенными бинарниками zapret2
- Автоматическое повышение прав (UAC) при запуске
- Всё хранится в `%LOCALAPPDATA%\ZapretManager\`
- Автообновление приложения и бинарников

### Сервер (`server/`)
- **Python + FastAPI + SQLite**
- Принимает диагностику → подбирает стратегию обхода по ISP
- Раздаёт конфиги, бинарники, обновления
- `versions.json` — управление версиями для обновлений

## Ключевые файлы

### Клиент
| Файл | Назначение |
|------|-----------|
| `main.py` | Точка входа, UAC elevation |
| `gui.py` | GUI, баннер обновлений |
| `diagnostics.py` | Определение ISP, проверка DNS/TCP/TLS |
| `zapret_manager.py` | Извлечение бинарников, запуск winws2 |
| `updater.py` | Автообновление app + binaries |
| `api_client.py` | HTTP-клиент для сервера |
| `version.py` | Константы версий |
| `download_zapret2.py` | Скачивание бинарников с GitHub (для сборки) |
| `build.bat` | Сборка .exe (скачивает zapret2 + PyInstaller) |

### Сервер
| Файл | Назначение |
|------|-----------|
| `main.py` | FastAPI endpoints |
| `config_engine.py` | Генерация winws2 конфигов по ISP |
| `database.py` | SQLAlchemy модели (clients, diagnostics, configs) |
| `models.py` | Pydantic модели API |
| `services.py` | Реестр 15 заблокированных сервисов |
| `versions.json` | Версии для системы обновлений |

## Технические детали

- **zapret2** использует WinDivert на Windows → нужны права администратора
- Стратегии подбираются по ISP: Ростелеком → fake+disorder, МТС → multidisorder, Билайн → multisplit
- Конфиг = аргументы winws2 + hostlist доменов
- Бинарники: winws2.exe, WinDivert.dll, WinDivert64.sys

## Процесс сборки

```bash
cd client
build.bat   # скачает zapret2, соберёт .exe, скопирует в server/updates/
```

## Процесс обновления

1. Изменить `client/version.py` (APP_VERSION / BINARIES_VERSION)
2. `build.bat`
3. Обновить `server/versions.json`
4. Клиенты получат баннер "Доступно обновление"

## Язык

- Интерфейс и комментарии на русском
- Пользователи из России, ISP: Ростелеком, МТС, Билайн, Мегафон, Теле2, Дом.ру
- Заблокированные сервисы: YouTube, Discord, Facebook, Instagram, X, Signal, Viber, LinkedIn и др.

## Стиль кода

- Python 3.10+, type hints
- Минимум зависимостей
- Всё должно быть максимально просто для конечного пользователя
