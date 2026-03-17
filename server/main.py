"""
Сервер Zapret Manager — FastAPI.

Принимает диагностику от клиентов, генерирует конфигурации winws2,
раздаёт обновления и собирает обратную связь.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Client, DiagnosticRecord, IssuedConfig, StrategyFeedback, get_db, init_db
from models import (
    ClientRegisterRequest,
    ClientRegisterResponse,
    ClientStats,
    ConfigResponse,
    DiagnosticReport,
)
from config_engine import generate_config
from services import get_all_services

app = FastAPI(
    title="Zapret Manager Server",
    description="Сервер управления конфигурациями zapret2 для обхода блокировок",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ── Регистрация ──────────────────────────────────────────────────────

@app.post("/api/register", response_model=ClientRegisterResponse)
def register_client(req: ClientRegisterRequest, db: Session = Depends(get_db)):
    """Регистрация нового клиента. Возвращает уникальный client_id."""
    client_id = str(uuid.uuid4())
    client = Client(
        id=client_id,
        os_version=req.os_version,
        hostname=req.hostname,
        created_at=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )
    db.add(client)
    db.commit()
    return ClientRegisterResponse(client_id=client_id, created_at=client.created_at)


# ── Приём диагностики и выдача конфига ────────────────────────────────

@app.post("/api/diagnostics", response_model=ConfigResponse)
def submit_diagnostics(report: DiagnosticReport, db: Session = Depends(get_db)):
    """
    Клиент отправляет результаты диагностики.
    Сервер генерирует и возвращает конфигурацию winws2.
    """
    # Находим или автоматически регистрируем клиента
    client = db.query(Client).filter(Client.id == report.client_id).first()
    if not client:
        client = Client(
            id=report.client_id,
            os_version="auto-registered",
            hostname="unknown",
            created_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        db.add(client)

    # Обновляем информацию о клиенте
    client.isp_name = report.isp.isp_name
    client.isp_ip = report.isp.ip
    client.region = report.isp.region
    client.city = report.isp.city
    client.asn = report.isp.asn
    client.last_seen = datetime.utcnow()

    # Сохраняем диагностику
    diag_record = DiagnosticRecord(
        client_id=report.client_id,
        isp_name=report.isp.isp_name,
        region=report.isp.region,
        services_json=json.dumps([s.model_dump() for s in report.services], default=str),
        created_at=datetime.utcnow(),
    )
    db.add(diag_record)

    # Генерируем конфиг
    config = generate_config(report)

    # Сохраняем выданный конфиг
    issued = IssuedConfig(
        client_id=report.client_id,
        winws2_args_json=json.dumps(config.winws2_args),
        hostlist_json=json.dumps(config.hostlist),
        config_version=config.config_version,
        created_at=datetime.utcnow(),
    )
    db.add(issued)
    db.commit()

    return config


# ── Обратная связь ────────────────────────────────────────────────────

@app.post("/api/feedback")
def submit_feedback(stats: ClientStats, db: Session = Depends(get_db)):
    """Клиент сообщает, работает ли обход для конкретного сервиса."""
    client = db.query(Client).filter(Client.id == stats.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    feedback = StrategyFeedback(
        client_id=stats.client_id,
        isp_name=client.isp_name or "unknown",
        region=client.region or "unknown",
        service_id=stats.service_id,
        strategy_hash="",  # TODO: добавить хеш текущей стратегии
        success=stats.success,
        latency_ms=stats.latency_ms,
        created_at=datetime.utcnow(),
    )
    db.add(feedback)
    db.commit()

    return {"status": "ok"}


# ── Информационные эндпоинты ─────────────────────────────────────────

@app.get("/api/services")
def list_services():
    """Список всех сервисов для проверки."""
    return get_all_services()


@app.get("/api/config/{client_id}", response_model=ConfigResponse | None)
def get_last_config(client_id: str, db: Session = Depends(get_db)):
    """Получить последний выданный конфиг для клиента."""
    issued = (
        db.query(IssuedConfig)
        .filter(IssuedConfig.client_id == client_id)
        .order_by(IssuedConfig.created_at.desc())
        .first()
    )
    if not issued:
        raise HTTPException(status_code=404, detail="Конфиг не найден. Запустите диагностику.")

    # Восстанавливаем ConfigResponse из сохранённых данных
    from services import get_all_services
    from models import ServiceStatus

    services_status = []
    hostlist = issued.get_hostlist()
    for svc in get_all_services():
        has_blocked_domain = any(d in hostlist for d in svc["domains"])
        services_status.append(ServiceStatus(
            service_id=svc["id"],
            name=svc["name"],
            icon=svc["icon"],
            blocked=has_blocked_domain,
            bypass_supported=True,
        ))

    return ConfigResponse(
        client_id=client_id,
        winws2_args=issued.get_args(),
        hostlist=hostlist,
        dns_servers=["8.8.8.8", "1.1.1.1"],
        services=services_status,
        config_version=issued.config_version,
        updated_at=issued.created_at,
    )


# ── Админ-статистика ─────────────────────────────────────────────────

@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(get_db)):
    """Базовая статистика для админки."""
    total_clients = db.query(Client).count()
    total_diagnostics = db.query(DiagnosticRecord).count()
    total_configs = db.query(IssuedConfig).count()
    total_feedback = db.query(StrategyFeedback).count()
    success_feedback = db.query(StrategyFeedback).filter(StrategyFeedback.success == True).count()

    return {
        "total_clients": total_clients,
        "total_diagnostics": total_diagnostics,
        "total_configs_issued": total_configs,
        "total_feedback": total_feedback,
        "success_rate": round(success_feedback / total_feedback * 100, 1) if total_feedback > 0 else 0,
    }


# ── Раздача файлов и обновления ────────────────────────────────────────

import io
import zipfile
from pathlib import Path
from fastapi.responses import StreamingResponse, FileResponse

SERVER_DIR = Path(__file__).parent
BINARIES_DIR = SERVER_DIR / "binaries"        # winws2.exe, WinDivert.dll, ...
UPDATES_DIR = SERVER_DIR / "updates"          # ZapretManager.exe (новые версии)
VERSIONS_FILE = SERVER_DIR / "versions.json"  # {"app_version": "1.0.0", ...}


def _load_versions() -> dict:
    if VERSIONS_FILE.exists():
        return json.loads(VERSIONS_FILE.read_text(encoding="utf-8"))
    return {"app_version": "1.0.0", "binaries_version": "1.0.0", "changelog": ""}


# ── Проверка обновлений ──────────────────────────────────────────────

@app.get("/api/update/check")
def check_update():
    """
    Клиент вызывает при запуске. Возвращает актуальные версии.
    Клиент сравнивает со своими и решает, нужно ли обновляться.
    """
    return _load_versions()


# ── Скачивание нового .exe ───────────────────────────────────────────

@app.get("/api/update/app")
def download_app_update():
    """
    Отдаёт новый ZapretManager.exe.
    Положите новую сборку в server/updates/ZapretManager.exe
    и обновите app_version в versions.json.
    """
    exe_path = UPDATES_DIR / "ZapretManager.exe"
    if not exe_path.exists():
        raise HTTPException(status_code=404, detail="Обновление приложения не найдено")

    return FileResponse(
        str(exe_path),
        media_type="application/octet-stream",
        filename="ZapretManager.exe",
    )


# ── Скачивание бинарников zapret2 ────────────────────────────────────

@app.get("/api/download/binaries")
def download_binaries():
    """
    ZIP-архив с winws2.exe, WinDivert.dll, WinDivert64.sys + lua-скрипты.
    Клиент скачивает при первом запуске или обновлении.
    """
    required = ["winws2.exe", "WinDivert.dll", "WinDivert64.sys"]

    for fname in required:
        if not (BINARIES_DIR / fname).exists():
            raise HTTPException(
                status_code=503,
                detail=f"{fname} не найден на сервере. Поместите в {BINARIES_DIR}",
            )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in required:
            zf.write(str(BINARIES_DIR / fname), fname)
        for lua_file in BINARIES_DIR.glob("*.lua"):
            zf.write(str(lua_file), lua_file.name)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=zapret2.zip",
            "Content-Length": str(buf.getbuffer().nbytes),
        },
    )


# ── Запуск ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    UPDATES_DIR.mkdir(parents=True, exist_ok=True)

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
