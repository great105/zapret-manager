package main

import (
	"embed"
	"fmt"
	"io/fs"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"time"
)

// ZapretManager — управление winws2
type ZapretManager struct {
	appDir    string
	zapretDir string
	binFS     embed.FS
	cmd       *exec.Cmd
}

// Необходимые файлы
var requiredBinaries = []string{
	"winws2.exe", "WinDivert.dll", "WinDivert64.sys", "cygwin1.dll",
}

func NewZapretManager(appDir string, binFS embed.FS) *ZapretManager {
	zDir := filepath.Join(appDir, "zapret2")
	os.MkdirAll(zDir, 0755)
	return &ZapretManager{
		appDir:    appDir,
		zapretDir: zDir,
		binFS:     binFS,
	}
}

// EnsureBinaries — извлечь бинарники из встроенной FS
func (z *ZapretManager) EnsureBinaries() error {
	if z.isReady() {
		return nil
	}

	log.Println("Extracting embedded binaries...")
	return fs.WalkDir(z.binFS, "binaries", func(path string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		data, err := z.binFS.ReadFile(path)
		if err != nil {
			return fmt.Errorf("read embedded %s: %w", path, err)
		}
		target := filepath.Join(z.zapretDir, d.Name())
		if err := os.WriteFile(target, data, 0755); err != nil {
			return fmt.Errorf("write %s: %w", target, err)
		}
		log.Printf("  + %s (%d KB)", d.Name(), len(data)/1024)
		return nil
	})
}

func (z *ZapretManager) isReady() bool {
	for _, f := range requiredBinaries {
		if _, err := os.Stat(filepath.Join(z.zapretDir, f)); os.IsNotExist(err) {
			return false
		}
	}
	return true
}

// WriteHostlist — записать список доменов
func (z *ZapretManager) WriteHostlist(domains []string) {
	unique := make(map[string]bool)
	for _, d := range domains {
		unique[d] = true
	}
	sorted := make([]string, 0, len(unique))
	for d := range unique {
		sorted = append(sorted, d)
	}
	sort.Strings(sorted)
	content := strings.Join(sorted, "\n")
	path := filepath.Join(z.zapretDir, "hostlist.txt")
	os.WriteFile(path, []byte(content), 0644)
	log.Printf("Hostlist: %d domains", len(sorted))
}

// Start — запустить winws2
func (z *ZapretManager) Start(args []string) error {
	z.Stop()
	time.Sleep(500 * time.Millisecond)

	exe := filepath.Join(z.zapretDir, "winws2.exe")
	if _, err := os.Stat(exe); os.IsNotExist(err) {
		return fmt.Errorf("winws2.exe not found")
	}

	z.cmd = exec.Command(exe, args...)
	z.cmd.Dir = z.zapretDir
	z.cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow:    true,
		CreationFlags: 0x08000000, // CREATE_NO_WINDOW
	}

	if err := z.cmd.Start(); err != nil {
		return fmt.Errorf("start winws2: %w", err)
	}

	// Даём время на инициализацию
	time.Sleep(1500 * time.Millisecond)

	// Проверяем, не упал ли
	if z.cmd.ProcessState != nil && z.cmd.ProcessState.Exited() {
		return fmt.Errorf("winws2 exited immediately")
	}

	log.Printf("winws2 started, PID=%d", z.cmd.Process.Pid)
	return nil
}

// Stop — остановить winws2
func (z *ZapretManager) Stop() {
	if z.cmd != nil && z.cmd.Process != nil {
		z.cmd.Process.Kill()
		z.cmd.Wait()
		z.cmd = nil
		log.Println("winws2 stopped")
	}

	// Убиваем все процессы winws2 (на случай зависших)
	killCmd := exec.Command("taskkill", "/F", "/IM", "winws2.exe")
	killCmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	killCmd.Run()
}

// IsRunning — работает ли winws2
func (z *ZapretManager) IsRunning() bool {
	if z.cmd != nil && z.cmd.Process != nil {
		// Попытка signal 0 — проверка жив ли процесс
		if err := z.cmd.Process.Signal(syscall.Signal(0)); err == nil {
			return true
		}
	}
	return false
}
