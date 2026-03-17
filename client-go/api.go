package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

// APIClient — клиент для сервера Zapret Manager
type APIClient struct {
	serverURL  string
	clientID   string
	idFile     string
	httpClient *http.Client
}

// ConfigResponse — ответ сервера с конфигурацией
type ConfigResponse struct {
	ClientID      string          `json:"client_id"`
	Winws2Args    []string        `json:"winws2_args"`
	Hostlist      []string        `json:"hostlist"`
	DNSServers    []string        `json:"dns_servers"`
	Services      []ServiceStatus `json:"services"`
	ConfigVersion int             `json:"config_version"`
}

type ServiceStatus struct {
	ServiceID      string `json:"service_id"`
	Name           string `json:"name"`
	Blocked        bool   `json:"blocked"`
	BypassSupported bool  `json:"bypass_supported"`
}

func NewAPIClient(serverURL, appDir string) *APIClient {
	idFile := filepath.Join(appDir, "client_id.txt")
	clientID := ""
	if data, err := os.ReadFile(idFile); err == nil {
		clientID = string(data)
	}

	return &APIClient{
		serverURL: serverURL,
		clientID:  clientID,
		idFile:    idFile,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Register — регистрация на сервере
func (c *APIClient) Register() error {
	if c.clientID != "" {
		return nil
	}

	osVer, hostname := GetSystemInfo()
	body := map[string]string{
		"os_version": osVer,
		"hostname":   hostname,
	}

	resp, err := c.post("/api/register", body)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return err
	}

	id, ok := result["client_id"].(string)
	if !ok {
		return fmt.Errorf("invalid response: no client_id")
	}

	c.clientID = id
	os.WriteFile(c.idFile, []byte(id), 0644)
	log.Printf("Registered: %s", id)
	return nil
}

// SendDiagnostics — отправить диагностику, получить конфиг
func (c *APIClient) SendDiagnostics(isp ISPInfo, services []ServiceDiagResult) (*ConfigResponse, error) {
	body := map[string]interface{}{
		"client_id": c.clientID,
		"isp":       isp,
		"services":  services,
	}

	resp, err := c.post("/api/diagnostics", body)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var config ConfigResponse
	if err := json.NewDecoder(resp.Body).Decode(&config); err != nil {
		return nil, fmt.Errorf("decode config: %w", err)
	}

	return &config, nil
}

// SendFeedback — обратная связь
func (c *APIClient) SendFeedback(serviceID string, success bool) {
	body := map[string]interface{}{
		"client_id":  c.clientID,
		"service_id": serviceID,
		"success":    success,
	}
	resp, err := c.post("/api/feedback", body)
	if err == nil {
		resp.Body.Close()
	}
}

func (c *APIClient) post(path string, body interface{}) (*http.Response, error) {
	data, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Post(
		c.serverURL+path,
		"application/json",
		bytes.NewReader(data),
	)
	if err != nil {
		return nil, fmt.Errorf("request %s: %w", path, err)
	}

	if resp.StatusCode >= 400 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("server error %d: %s", resp.StatusCode, string(bodyBytes))
	}

	return resp, nil
}
