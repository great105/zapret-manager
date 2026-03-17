package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
)

type Updater struct {
	serverURL string
	appDir    string
}

type UpdateInfo struct {
	AppUpdate       bool   `json:"app_update"`
	AppNewVersion   string `json:"app_new_version"`
	BinUpdate       bool   `json:"bin_update"`
	BinNewVersion   string `json:"bin_new_version"`
	Changelog       string `json:"changelog"`
}

func NewUpdater(serverURL, appDir string) *Updater {
	return &Updater{serverURL: serverURL, appDir: appDir}
}

// Check — проверить обновления
func (u *Updater) Check(currentAppVersion string) *UpdateInfo {
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(u.serverURL + "/api/update/check")
	if err != nil {
		log.Printf("Update check failed: %v", err)
		return nil
	}
	defer resp.Body.Close()

	var data map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil
	}

	info := &UpdateInfo{
		Changelog: data["changelog"],
	}

	if serverApp, ok := data["app_version"]; ok {
		if versionNewer(serverApp, currentAppVersion) {
			info.AppUpdate = true
			info.AppNewVersion = serverApp
		}
	}

	return info
}

// UpdateBinaries — скачать новые бинарники
func (u *Updater) UpdateBinaries(z *ZapretManager) error {
	z.Stop()
	// Используем серверный эндпоинт /api/download/binaries
	// ZapretManager скачает и распакует
	return fmt.Errorf("not implemented yet")
}

func versionNewer(newV, curV string) bool {
	newParts := parseVersion(newV)
	curParts := parseVersion(curV)
	for i := 0; i < len(newParts) && i < len(curParts); i++ {
		if newParts[i] > curParts[i] {
			return true
		}
		if newParts[i] < curParts[i] {
			return false
		}
	}
	return false
}

func parseVersion(v string) []int {
	parts := strings.Split(v, ".")
	nums := make([]int, len(parts))
	for i, p := range parts {
		nums[i], _ = strconv.Atoi(p)
	}
	return nums
}
