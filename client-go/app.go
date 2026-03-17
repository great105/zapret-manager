package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

const ServerURL = "https://5.42.120.247"
const AppVersion = "2.0.0"

// App — главная структура приложения
type App struct {
	ctx     context.Context
	api     *APIClient
	zapret  *ZapretManager
	updater *Updater
	active  bool
	appDir  string
}

func NewApp() *App {
	appDir := filepath.Join(os.Getenv("LOCALAPPDATA"), "ZapretManager")
	os.MkdirAll(appDir, 0755)

	return &App{
		api:    NewAPIClient(ServerURL, appDir),
		appDir: appDir,
	}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	a.zapret = NewZapretManager(a.appDir, binariesFS)
	a.updater = NewUpdater(ServerURL, a.appDir)
	log.Printf("Zapret Manager v%s started, appDir=%s", AppVersion, a.appDir)
}

func (a *App) shutdown(ctx context.Context) {
	if a.active {
		a.zapret.Stop()
	}
}

// ── Методы, доступные из JS ──────────────────────────────────────────

// GetServices — список сервисов для UI
func (a *App) GetServices() []ServiceInfo {
	return DefaultServices
}

// StartBypass — главная кнопка: диагностика → конфиг → запуск
// selectedIDs — список ID сервисов, выбранных пользователем
func (a *App) StartBypass(selectedIDs []string) error {
	// Фильтруем сервисы по выбору пользователя
	selected := make(map[string]bool)
	for _, id := range selectedIDs {
		selected[id] = true
	}
	var services []ServiceInfo
	for _, svc := range DefaultServices {
		if selected[svc.ID] {
			services = append(services, svc)
		}
	}
	if len(services) == 0 {
		return fmt.Errorf("Не выбрано ни одного сервиса")
	}

	// 1. Извлечь/проверить бинарники
	a.emit("progress", map[string]interface{}{"step": "binaries", "pct": 5, "text": "Проверка компонентов..."})
	if err := a.zapret.EnsureBinaries(); err != nil {
		return fmt.Errorf("Не удалось подготовить компоненты: %w", err)
	}

	// 2. Регистрация
	a.emit("progress", map[string]interface{}{"step": "register", "pct": 15, "text": "Подключение к серверу..."})
	if err := a.api.Register(); err != nil {
		return fmt.Errorf("Сервер недоступен: %w", err)
	}

	// 3. Диагностика только выбранных
	results := make([]ServiceDiagResult, 0, len(services))
	for i, svc := range services {
		pct := 20 + int(float64(i)/float64(len(services))*50)
		a.emit("progress", map[string]interface{}{
			"step": "diagnose", "pct": pct,
			"text":      fmt.Sprintf("Проверка: %s", svc.Name),
			"serviceId": svc.ID,
		})
		result := CheckService(svc)
		results = append(results, result)

		status := "ok"
		if !result.TCPConnect || !result.TLSHandshake || result.Timeout {
			status = "blocked"
		}
		a.emit("serviceStatus", map[string]interface{}{
			"id": svc.ID, "status": status,
		})
	}

	// Определяем ISP
	isp := DetectISP()
	a.emit("isp", map[string]interface{}{"name": isp.ISPName})

	// 4. Отправить диагностику, получить конфиг
	a.emit("progress", map[string]interface{}{"step": "config", "pct": 75, "text": "Получение конфигурации..."})
	config, err := a.api.SendDiagnostics(isp, results)
	if err != nil {
		return fmt.Errorf("Ошибка конфигурации: %w", err)
	}

	// 5. Записать hostlist и конфиг
	a.zapret.WriteHostlist(config.Hostlist)

	// 6. Запуск winws2
	a.emit("progress", map[string]interface{}{"step": "launch", "pct": 90, "text": "Запуск обхода..."})
	if err := a.zapret.Start(config.Winws2Args); err != nil {
		return fmt.Errorf("Не удалось запустить: %w", err)
	}

	a.active = true
	a.emit("progress", map[string]interface{}{"step": "done", "pct": 100, "text": ""})

	// Помечаем заблокированные как "обход активен"
	for _, s := range config.Services {
		if s.Blocked {
			a.emit("serviceStatus", map[string]interface{}{
				"id": s.ServiceID, "status": "bypass",
			})
		}
	}

	return nil
}

// StopBypass — остановить обход
func (a *App) StopBypass() {
	a.zapret.Stop()
	a.active = false
}

// IsActive — работает ли обход
func (a *App) IsActive() bool {
	return a.active
}

// CheckUpdate — проверить обновления
func (a *App) CheckUpdate() *UpdateInfo {
	return a.updater.Check(AppVersion)
}

// DoUpdate — выполнить обновление бинарников
func (a *App) DoUpdate() error {
	return a.updater.UpdateBinaries(a.zapret)
}

// GetISP — определить ISP
func (a *App) GetISP() ISPInfo {
	return DetectISP()
}

func (a *App) emit(event string, data map[string]interface{}) {
	if a.ctx != nil {
		runtime.EventsEmit(a.ctx, event, data)
	}
}
