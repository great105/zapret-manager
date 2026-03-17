package main

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"runtime"
	"time"
)

const checkTimeout = 5 * time.Second

// ISPInfo — информация о провайдере
type ISPInfo struct {
	IP      string `json:"ip"`
	ISPName string `json:"isp_name"`
	Region  string `json:"region"`
	City    string `json:"city"`
	ASN     string `json:"asn,omitempty"`
}

// ServiceDiagResult — результат проверки одного сервиса
type ServiceDiagResult struct {
	ServiceID    string  `json:"service_id"`
	Domain       string  `json:"domain"`
	DNSResolved  bool    `json:"dns_resolved"`
	DNSIP        string  `json:"dns_ip,omitempty"`
	TCPConnect   bool    `json:"tcp_connect"`
	TCPLatencyMs float64 `json:"tcp_latency_ms,omitempty"`
	TLSHandshake bool    `json:"tls_handshake"`
	TLSError     string  `json:"tls_error,omitempty"`
	RSTReceived  bool    `json:"rst_received"`
	Timeout      bool    `json:"timeout"`
}

// DetectISP — определяет ISP через ip-api.com
func DetectISP() ISPInfo {
	client := &http.Client{Timeout: checkTimeout}
	resp, err := client.Get("http://ip-api.com/json/?lang=ru")
	if err != nil {
		return ISPInfo{IP: "unknown", ISPName: "unknown", Region: "unknown", City: "unknown"}
	}
	defer resp.Body.Close()

	var data map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return ISPInfo{IP: "unknown", ISPName: "unknown", Region: "unknown", City: "unknown"}
	}

	str := func(key string) string {
		if v, ok := data[key].(string); ok {
			return v
		}
		return "unknown"
	}

	return ISPInfo{
		IP:      str("query"),
		ISPName: str("isp"),
		Region:  str("regionName"),
		City:    str("city"),
		ASN:     str("as"),
	}
}

// CheckService — полная проверка одного сервиса
func CheckService(svc ServiceInfo) ServiceDiagResult {
	domain := svc.TestDomain
	result := ServiceDiagResult{
		ServiceID: svc.ID,
		Domain:    domain,
	}

	// DNS
	ips, err := net.LookupHost(domain)
	if err != nil || len(ips) == 0 {
		result.DNSResolved = false
		return result
	}
	result.DNSResolved = true
	result.DNSIP = ips[0]

	// TCP 443
	start := time.Now()
	conn, err := net.DialTimeout("tcp", domain+":443", checkTimeout)
	if err != nil {
		result.TCPConnect = false
		if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
			result.Timeout = true
		} else {
			result.RSTReceived = true
		}
		return result
	}
	result.TCPConnect = true
	result.TCPLatencyMs = float64(time.Since(start).Milliseconds())
	conn.Close()

	// TLS
	tlsConn, err := tls.DialWithDialer(
		&net.Dialer{Timeout: checkTimeout},
		"tcp", domain+":443",
		&tls.Config{ServerName: domain},
	)
	if err != nil {
		result.TLSHandshake = false
		result.TLSError = err.Error()
		return result
	}
	result.TLSHandshake = true
	tlsConn.Close()

	return result
}

// GetSystemInfo — информация о системе
func GetSystemInfo() (string, string) {
	hostname, _ := os.Hostname()
	osVersion := fmt.Sprintf("%s %s", runtime.GOOS, runtime.GOARCH)
	return osVersion, hostname
}
