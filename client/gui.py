"""
Графический интерфейс клиента Zapret Manager.
Максимально простой: одна кнопка → всё работает.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import customtkinter as ctk

from api_client import ApiClient
from diagnostics import get_system_info, run_full_diagnostics
from zapret_manager import ZapretManager
from updater import Updater, UpdateInfo
from version import APP_VERSION

logger = logging.getLogger(__name__)

# ── Цвета ─────────────────────────────────────────────────────────────

C = {
    "bg": "#0d1117",
    "card": "#161b22",
    "border": "#30363d",
    "green": "#3fb950",
    "red": "#f85149",
    "yellow": "#d29922",
    "orange": "#db6d28",
    "blue": "#58a6ff",
    "text": "#e6edf3",
    "dim": "#8b949e",
    "white": "#ffffff",
    "btn": "#238636",
    "btn_hover": "#2ea043",
    "btn_stop": "#da3633",
    "btn_stop_hover": "#b62324",
}

# Встроенный список сервисов (если сервер недоступен)
DEFAULT_SERVICES = [
    {"id": "youtube", "name": "YouTube", "test_domain": "youtube.com",
     "ports": {"tcp": [443, 80], "udp": [443]}, "blocking_type": "throttle"},
    {"id": "discord", "name": "Discord", "test_domain": "discord.com",
     "ports": {"tcp": [443, 80], "udp": [443]}, "blocking_type": "full"},
    {"id": "facebook", "name": "Facebook", "test_domain": "facebook.com",
     "ports": {"tcp": [443, 80]}, "blocking_type": "full"},
    {"id": "instagram", "name": "Instagram", "test_domain": "instagram.com",
     "ports": {"tcp": [443, 80]}, "blocking_type": "full"},
    {"id": "twitter", "name": "X (Twitter)", "test_domain": "x.com",
     "ports": {"tcp": [443, 80]}, "blocking_type": "full"},
    {"id": "telegram_calls", "name": "Telegram (звонки)", "test_domain": "telegram.org",
     "ports": {"tcp": [443, 80], "udp": [443]}, "blocking_type": "partial"},
    {"id": "signal", "name": "Signal", "test_domain": "signal.org",
     "ports": {"tcp": [443]}, "blocking_type": "full"},
    {"id": "viber", "name": "Viber", "test_domain": "viber.com",
     "ports": {"tcp": [443, 80]}, "blocking_type": "full"},
    {"id": "linkedin", "name": "LinkedIn", "test_domain": "linkedin.com",
     "ports": {"tcp": [443, 80]}, "blocking_type": "full"},
    {"id": "snapchat", "name": "Snapchat", "test_domain": "snapchat.com",
     "ports": {"tcp": [443]}, "blocking_type": "full"},
    {"id": "whatsapp_calls", "name": "WhatsApp (звонки)", "test_domain": "web.whatsapp.com",
     "ports": {"tcp": [443], "udp": [443]}, "blocking_type": "partial"},
    {"id": "chatgpt", "name": "ChatGPT", "test_domain": "chat.openai.com",
     "ports": {"tcp": [443]}, "blocking_type": "throttle"},
    {"id": "roblox", "name": "Roblox", "test_domain": "roblox.com",
     "ports": {"tcp": [443, 80]}, "blocking_type": "full"},
    {"id": "twitch", "name": "Twitch", "test_domain": "twitch.tv",
     "ports": {"tcp": [443, 80]}, "blocking_type": "partial"},
    {"id": "soundcloud", "name": "SoundCloud", "test_domain": "soundcloud.com",
     "ports": {"tcp": [443]}, "blocking_type": "partial"},
]


class ServiceRow(ctk.CTkFrame):
    """Строка одного сервиса."""

    def __init__(self, master, name: str, **kwargs):
        super().__init__(master, fg_color="transparent", height=32, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self.dot = ctk.CTkLabel(self, text="", font=("Segoe UI", 10), width=20,
                                text_color=C["dim"])
        self.dot.grid(row=0, column=0, padx=(8, 4))

        self.name_lbl = ctk.CTkLabel(self, text=name, font=("Segoe UI", 12),
                                     text_color=C["text"], anchor="w")
        self.name_lbl.grid(row=0, column=1, sticky="w")

        self.status_lbl = ctk.CTkLabel(self, text="", font=("Segoe UI", 11),
                                       text_color=C["dim"], anchor="e")
        self.status_lbl.grid(row=0, column=2, padx=(4, 8), sticky="e")

    def set(self, state: str, text: str = ""):
        colors = {
            "ok":       (C["green"],  "Доступен"),
            "blocked":  (C["red"],    "Заблокирован"),
            "bypass":   (C["green"],  "Обход активен"),
            "check":    (C["yellow"], "Проверка..."),
            "partial":  (C["orange"], "Частично"),
            "idle":     (C["dim"],    ""),
        }
        color, default_text = colors.get(state, (C["dim"], ""))
        self.dot.configure(text="●" if state != "idle" else "", text_color=color)
        self.status_lbl.configure(text=text or default_text, text_color=color)


class App(ctk.CTk):
    """Главное окно."""

    def __init__(self, server_url: str, app_dir: Path):
        super().__init__()

        self.server_url = server_url
        self.api = ApiClient(server_url)
        self.zapret = ZapretManager(app_dir, server_url)
        self.updater = Updater(server_url, app_dir)
        self.rows: dict[str, ServiceRow] = {}
        self.services: list[dict] = []
        self.active = False

        ctk.set_appearance_mode("dark")
        self.title("Zapret Manager")
        self.geometry("420x660")
        self.minsize(380, 520)
        self.configure(fg_color=C["bg"])
        self._center()
        self._build()
        self._load_services()

        # Проверяем обновления в фоне при запуске
        threading.Thread(target=self._check_updates_bg, daemon=True).start()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 420) // 2
        y = (self.winfo_screenheight() - 660) // 2
        self.geometry(f"+{x}+{y}")

    # ── UI ────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Заголовок
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="ew")

        ctk.CTkLabel(hdr, text="Zapret Manager", font=("Segoe UI", 22, "bold"),
                     text_color=C["white"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Обход интернет-блокировок", font=("Segoe UI", 12),
                     text_color=C["dim"]).pack(anchor="w")

        # Статус-бар
        self.status_bar = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=10, height=40)
        self.status_bar.grid(row=1, column=0, padx=20, pady=(12, 0), sticky="ew")
        self.status_bar.grid_columnconfigure(1, weight=1)

        self.status_dot = ctk.CTkLabel(self.status_bar, text="", font=("Segoe UI", 11),
                                       text_color=C["dim"], width=20)
        self.status_dot.grid(row=0, column=0, padx=(12, 4), pady=8)

        self.status_text = ctk.CTkLabel(self.status_bar, text="Готов к работе",
                                        font=("Segoe UI", 12), text_color=C["dim"], anchor="w")
        self.status_text.grid(row=0, column=1, pady=8, sticky="w")

        self.isp_lbl = ctk.CTkLabel(self.status_bar, text="", font=("Segoe UI", 11),
                                    text_color=C["dim"])
        self.isp_lbl.grid(row=0, column=2, padx=(4, 12), pady=8)

        # Кнопка
        self.btn = ctk.CTkButton(
            self, text="Обойти блокировки", font=("Segoe UI", 16, "bold"),
            height=52, corner_radius=12,
            fg_color=C["btn"], hover_color=C["btn_hover"],
            command=self._on_click,
        )
        self.btn.grid(row=2, column=0, padx=20, pady=16, sticky="ew")

        # Прогресс (скрыт)
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, mode="determinate",
                                                progress_color=C["blue"], height=3)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20)
        self.progress_lbl = ctk.CTkLabel(self.progress_frame, text="",
                                         font=("Segoe UI", 11), text_color=C["dim"])
        self.progress_lbl.pack(anchor="w", padx=20, pady=(2, 0))

        # Список сервисов
        ctk.CTkLabel(self, text="Сервисы", font=("Segoe UI", 13, "bold"),
                     text_color=C["text"]).grid(row=4, column=0, padx=24, pady=(4, 2), sticky="w")

        self.svc_frame = ctk.CTkScrollableFrame(self, fg_color=C["card"], corner_radius=10)
        self.svc_frame.grid(row=5, column=0, padx=16, pady=(0, 8), sticky="nsew")
        self.svc_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Баннер обновления (скрыт по умолчанию)
        self.update_banner = ctk.CTkFrame(self, fg_color="#1c3a13", corner_radius=8, height=36)
        self.update_banner.grid_columnconfigure(1, weight=1)

        self.update_text = ctk.CTkLabel(
            self.update_banner, text="", font=("Segoe UI", 11),
            text_color=C["green"], anchor="w",
        )
        self.update_text.grid(row=0, column=0, padx=(12, 4), pady=6, sticky="w")

        self.update_btn = ctk.CTkButton(
            self.update_banner, text="Обновить", font=("Segoe UI", 11),
            width=90, height=26, corner_radius=6,
            fg_color=C["btn"], hover_color=C["btn_hover"],
            command=self._on_update_click,
        )
        self.update_btn.grid(row=0, column=1, padx=(4, 8), pady=6, sticky="e")

        # Футер
        self.footer_lbl = ctk.CTkLabel(
            self, text=f"v{APP_VERSION}  |  zapret2 engine",
            font=("Segoe UI", 10), text_color=C["dim"],
        )
        self.footer_lbl.grid(row=7, column=0, pady=(0, 6))

    def _load_services(self):
        try:
            svcs = self.api.get_services()
            self.services = svcs if svcs else DEFAULT_SERVICES
        except Exception:
            self.services = DEFAULT_SERVICES

        for svc in self.services:
            row = ServiceRow(self.svc_frame, svc["name"])
            row.grid(sticky="ew", pady=1)
            self.rows[svc["id"]] = row

    # ── Статус ────────────────────────────────────────────────────────

    def _status(self, text: str, color: str = C["dim"], dot: str = ""):
        self.status_text.configure(text=text, text_color=color)
        self.status_dot.configure(text=dot, text_color=color)

    def _show_progress(self, show: bool):
        if show:
            self.progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        else:
            self.progress_frame.grid_forget()

    def _progress(self, value: float, text: str):
        self.after(0, lambda: self.progress_bar.set(value))
        self.after(0, lambda: self.progress_lbl.configure(text=text))

    # ── Главная кнопка ────────────────────────────────────────────────

    def _on_click(self):
        if self.active:
            self._do_stop()
        else:
            self._do_start()

    def _do_start(self):
        self.btn.configure(state="disabled", text="Подключение...")
        self._show_progress(True)
        self._status("Настройка...", C["yellow"], "◌")
        for row in self.rows.values():
            row.set("check")
        threading.Thread(target=self._worker, daemon=True).start()

    def _do_stop(self):
        self.zapret.stop()
        self.active = False
        self.btn.configure(text="Обойти блокировки", fg_color=C["btn"],
                           hover_color=C["btn_hover"])
        self._status("Остановлен", C["dim"], "")
        self._show_progress(False)
        for row in self.rows.values():
            row.set("idle")

    # ── Рабочий поток ─────────────────────────────────────────────────

    def _worker(self):
        try:
            self._step_binaries()
            self._step_register()
            self._step_diagnose()
            self._step_config()
            self._step_launch()
        except _Abort:
            pass
        except Exception as e:
            logger.exception("worker error")
            self._fail(f"Ошибка: {e}")

    def _step_binaries(self):
        """Шаг 1: Убедиться, что бинарники на месте."""
        self._progress(0.05, "Проверка компонентов...")
        ok = self.zapret.ensure_binaries(
            progress_callback=lambda msg: self._progress(0.1, msg)
        )
        if not ok:
            self._fail(
                "Не удалось загрузить компоненты zapret2.\n"
                "Проверьте подключение к интернету и доступность сервера."
            )
            raise _Abort

    def _step_register(self):
        """Шаг 2: Регистрация на сервере."""
        self._progress(0.15, "Подключение к серверу...")
        sys_info = get_system_info()
        try:
            self.api.register(sys_info["os_version"], sys_info["hostname"])
        except Exception as e:
            self._fail(f"Сервер недоступен:\n{e}")
            raise _Abort

    def _step_diagnose(self):
        """Шаг 3: Диагностика сети."""
        total = len(self.services)

        def on_progress(i, tot, name):
            pct = 0.2 + 0.5 * (i / max(tot, 1))
            self._progress(pct, f"Проверка: {name}")
            for svc in self.services:
                if svc["name"] == name:
                    self.after(0, lambda s=svc["id"]: (
                        self.rows[s].set("check") if s in self.rows else None
                    ))

        self._diag = run_full_diagnostics(self.services, on_progress)

        # Показываем ISP
        isp = self._diag["isp"].get("isp_name", "")
        self.after(0, lambda: self.isp_lbl.configure(text=isp))

        # Обновляем статусы
        for d in self._diag["services"]:
            sid = d["service_id"]
            blocked = not d["tcp_connect"] or not d["tls_handshake"] or d["timeout"]
            self.after(0, lambda s=sid, b=blocked: (
                self.rows[s].set("blocked" if b else "ok") if s in self.rows else None
            ))

    def _step_config(self):
        """Шаг 4: Получить конфиг с сервера."""
        self._progress(0.75, "Получение конфигурации...")
        report = {
            "client_id": self.api.client_id,
            "isp": self._diag["isp"],
            "services": self._diag["services"],
        }
        try:
            self._config = self.api.send_diagnostics(report)
        except Exception as e:
            self._fail(f"Ошибка конфигурации:\n{e}")
            raise _Abort

        self.zapret.write_hostlist(self._config.get("hostlist", []))
        self.zapret.write_config(self._config)

    def _step_launch(self):
        """Шаг 5: Запуск winws2."""
        self._progress(0.9, "Запуск обхода...")

        args = self._config.get("winws2_args", [])
        ok, msg = self.zapret.start(args)

        if not ok:
            self._fail(f"Не удалось запустить:\n{msg}")
            raise _Abort

        # Успех!
        self._progress(1.0, "")

        def on_success():
            self.active = True
            self._show_progress(False)
            self.btn.configure(
                state="normal", text="Остановить",
                fg_color=C["btn_stop"], hover_color=C["btn_stop_hover"],
            )
            self._status("Обход активен", C["green"], "●")

            # Все заблокированные → "обход активен"
            for svc_st in self._config.get("services", []):
                sid = svc_st.get("service_id", "")
                if sid in self.rows and svc_st.get("blocked"):
                    self.rows[sid].set("bypass")

        self.after(0, on_success)

    # ── Ошибки ────────────────────────────────────────────────────────

    def _fail(self, message: str):
        """Показать ошибку и вернуть кнопку."""
        def update():
            self._show_progress(False)
            self.btn.configure(
                state="normal", text="Обойти блокировки",
                fg_color=C["btn"], hover_color=C["btn_hover"],
            )
            self._status("Ошибка", C["red"], "●")
            self._show_error_dialog(message)

        self.after(0, update)

    def _show_error_dialog(self, msg: str):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Ошибка")
        dlg.geometry("380x180")
        dlg.configure(fg_color=C["bg"])
        dlg.transient(self)
        dlg.grab_set()
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 380) // 2
        y = self.winfo_y() + (self.winfo_height() - 180) // 2
        dlg.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dlg, text=msg, font=("Segoe UI", 12), text_color=C["text"],
                     wraplength=340, justify="left").pack(padx=20, pady=(20, 10), fill="both", expand=True)
        ctk.CTkButton(dlg, text="OK", width=80, command=dlg.destroy).pack(pady=(0, 16))


    # ── Обновления ───────────────────────────────────────────────────

    def _check_updates_bg(self):
        """Фоновая проверка обновлений при запуске."""
        info = self.updater.check()
        self._pending_update = info

        if info.app_update or info.binaries_update:
            parts = []
            if info.app_update:
                parts.append(f"Приложение {info.app_new_version}")
            if info.binaries_update:
                parts.append(f"Zapret2 {info.binaries_new_version}")
            text = "Доступно обновление: " + ", ".join(parts)

            def show():
                self.update_text.configure(text=text)
                self.update_banner.grid(row=6, column=0, padx=16, pady=(0, 4), sticky="ew")

            self.after(0, show)

    def _on_update_click(self):
        """Нажатие на кнопку обновления."""
        self.update_btn.configure(state="disabled", text="...")
        threading.Thread(target=self._do_update, daemon=True).start()

    def _do_update(self):
        """Выполнить обновление."""
        info = self._pending_update

        try:
            # Сначала обновляем бинарники (не требует перезапуска)
            if info.binaries_update:
                self.after(0, lambda: self.update_text.configure(
                    text="Обновление zapret2..."))
                ok = self.updater.update_binaries(
                    self.zapret,
                    progress_callback=lambda msg: self.after(
                        0, lambda m=msg: self.update_text.configure(text=m)),
                )
                if ok:
                    logger.info("Бинарники обновлены")

            # Затем обновляем приложение (перезапуск)
            if info.app_update:
                self.after(0, lambda: self.update_text.configure(
                    text="Скачивание новой версии..."))
                # Останавливаем обход перед обновлением
                if self.active:
                    self.zapret.stop()
                self.updater.update_app(
                    progress_callback=lambda msg: self.after(
                        0, lambda m=msg: self.update_text.configure(text=m)),
                )
                # Сюда не дойдём — update_app вызывает sys.exit

            # Если обновились только бинарники — скрываем баннер
            def done():
                self.update_banner.grid_forget()
                self._status("Обновлено", C["green"], "●")
            self.after(0, done)

        except Exception as e:
            logger.exception("Ошибка обновления")
            def err():
                self.update_text.configure(text=f"Ошибка: {e}")
                self.update_btn.configure(state="normal", text="Повторить")
            self.after(0, err)


class _Abort(Exception):
    """Прерывание рабочего потока (не ошибка)."""
    pass
