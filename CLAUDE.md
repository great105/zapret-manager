# Zapret Manager

Система автоматического обхода интернет-блокировок на базе zapret2 (winws2).
Пользователь ставит один .exe, нажимает кнопку — всё работает.

## Архитектура

### Клиент v2 — Go + Wails (`client-go/`) — ОСНОВНОЙ
- **Go + Wails v2** — нативный .exe 14 МБ с WebView2 UI
- Бинарники zapret2 встроены через `go:embed`
- Всё хранится в `%LOCALAPPDATA%\ZapretManager\`
- Автопроверка обновлений при запуске

### Клиент v1 — Python (`client/`) — УСТАРЕВШИЙ
- Python + customtkinter + PyInstaller (38 МБ)
- Оставлен для справки, не развивается

### Сервер (`server/`)
- **Python + FastAPI + SQLite** на VPS 5.42.120.247:8000
- Принимает диагностику → подбирает стратегию обхода по ISP
- Раздаёт конфиги, бинарники, обновления
- Автоматически регистрирует неизвестных клиентов

## Ключевые файлы

### Go клиент (`client-go/`)
| Файл | Назначение |
|------|-----------|
| `main.go` | Wails app, окно, embed assets |
| `app.go` | Главная логика: StartBypass, StopBypass |
| `diagnostics.go` | ISP detection, DNS/TCP/TLS проверки |
| `zapret.go` | Извлечение бинарников, запуск/остановка winws2 |
| `api.go` | HTTP-клиент к серверу |
| `updater.go` | Проверка обновлений |
| `services.go` | Список 15 заблокированных сервисов |
| `frontend/` | HTML/CSS/JS — тёмная тема |
| `binaries/` | winws2.exe, WinDivert, cygwin1.dll, lua-скрипты |

### Сервер (`server/`)
| Файл | Назначение |
|------|-----------|
| `main.py` | FastAPI: /api/register, /api/diagnostics, /api/update/* |
| `config_engine.py` | Генерация winws2 аргументов по ISP |
| `database.py` | SQLAlchemy: clients, diagnostics, configs |
| `models.py` | Pydantic модели API |
| `services.py` | Реестр сервисов с доменами |
| `versions.json` | Версии для автообновлений |

## Критические знания о zapret2

- **winws2** на Windows требует **cygwin1.dll** рядом с .exe
- Lua-скрипты загружаются через `--lua-init=@file.lua` (НЕ `--lua=`)
- Порядок: `--lua-init=@zapret-lib.lua` → `--lua-init=@zapret-antidpi.lua` → `--lua-desync=function:params`
- WinDivert фильтры: `--wf-tcp-out=80,443`, `--wf-udp-out=443`
- Профили разделяются через `--new`
- Запуск только с правами администратора

## Сборка Go клиента

```bash
cd client-go
wails build -clean    # → build/bin/ZapretManager.exe (14 МБ)
```

Требуется: Go 1.24+, Node.js, Wails CLI (`go install github.com/wailsapp/wails/v2/cmd/wails@latest`).

## Деплой сервера

```bash
python deploy.py      # полный деплой: clone + venv + systemd
```

Быстрый редеплой (pull + restart):
```bash
python -c "
import paramiko; ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('5.42.120.247',username='root',password='c8,sCBZhqJa*t7')
[print(ssh.exec_command(c)[1].read().decode()) for c in ['cd /opt/zapret-manager && git pull','systemctl restart zapret-manager']]
ssh.close()
"
```

## GitHub

https://github.com/great105/zapret-manager (public)

## Стиль кода

- Go клиент: стандартный Go стиль, минимум зависимостей
- Python сервер: FastAPI, type hints, Pydantic
- Интерфейс и комментарии на русском
- Максимальная простота для пользователя
