package proxy_test

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"smartparking/internal/config"
	"smartparking/internal/proxy"
)

func TestGatewayHealthEndpoint(t *testing.T) {
	cfg := &config.Config{
		GatewayPort: 8090,
		BackendPort: 8008,
		Host:        "127.0.0.1",
	}

	gw, err := proxy.NewGateway(cfg)
	if err != nil {
		t.Fatalf("failed to create gateway: %v", err)
	}

	req := httptest.NewRequest("GET", "/health", nil)
	rr := httptest.NewRecorder()

	// Direct call to gateway router
	serverHandler := gw.Handler()
	serverHandler.ServeHTTP(rr, req)

	// Since backend isn't running in unit test, it returns 503 or 200 with JSON payload
	if rr.Code != http.StatusOK && rr.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 200 or 503 from health check, got %d", rr.Code)
	}

	contentType := rr.Header().Get("Content-Type")
	if contentType != "application/json" {
		t.Errorf("expected Content-Type application/json, got %s", contentType)
	}
}

func TestGatewayEmbeddedUIIndex(t *testing.T) {
	cfg := &config.Config{
		GatewayPort: 8090,
		BackendPort: 8008,
		Host:        "127.0.0.1",
	}

	gw, err := proxy.NewGateway(cfg)
	if err != nil {
		t.Fatalf("failed to create gateway: %v", err)
	}

	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()

	gw.Handler().ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("expected 200 OK from embedded UI root, got %d", rr.Code)
	}
}
