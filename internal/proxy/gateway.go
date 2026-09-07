package proxy

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"smartparking/internal/assets"
	"smartparking/internal/config"
)

// Gateway is the single-port reverse proxy and static server for Smart Parking.
type Gateway struct {
	cfg        *config.Config
	server     *http.Server
	proxy      *httputil.ReverseProxy
	uiHandler  http.Handler
	backendURL *url.URL
}

// NewGateway initializes the gateway with embedded UI and backend reverse proxy.
func NewGateway(cfg *config.Config) (*Gateway, error) {
	backendTarget := fmt.Sprintf("http://127.0.0.1:%d", cfg.BackendPort)
	targetURL, err := url.Parse(backendTarget)
	if err != nil {
		return nil, fmt.Errorf("invalid backend URL: %w", err)
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)

	// Custom error handler for proxy
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"error":   "Backend unavailable",
			"message": err.Error(),
		})
	}

	uiHandler := assets.GetUIHandler()

	gw := &Gateway{
		cfg:        cfg,
		proxy:      proxy,
		uiHandler:  uiHandler,
		backendURL: targetURL,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", gw.dispatch)

	gw.server = &http.Server{
		Addr:         fmt.Sprintf("%s:%d", cfg.Host, cfg.GatewayPort),
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	return gw, nil
}

// Handler returns the underlying http.Handler for testing and inspection.
func (g *Gateway) Handler() http.Handler {
	return g.server.Handler
}

// Start listens and serves requests until closed or context is cancelled.
func (g *Gateway) Start() error {
	if err := g.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}
	return nil
}

// Shutdown gracefully stops the HTTP server.
func (g *Gateway) Shutdown(ctx context.Context) error {
	return g.server.Shutdown(ctx)
}

func (g *Gateway) dispatch(w http.ResponseWriter, r *http.Request) {
	p := r.URL.Path

	// 1. Gateway aggregated health check
	if p == "/health" {
		g.handleHealth(w, r)
		return
	}

	// 2. API, Swagger docs, and OpenAPI specifications
	if strings.HasPrefix(p, "/api/") ||
		strings.HasPrefix(p, "/docs") ||
		strings.HasPrefix(p, "/openapi.json") ||
		strings.HasPrefix(p, "/redoc") ||
		p == "/api" {
		// Set original host header
		r.Header.Set("X-Forwarded-Host", r.Host)
		r.Header.Set("X-Forwarded-Proto", "http")
		g.proxy.ServeHTTP(w, r)
		return
	}

	// 3. WebSocket endpoints: /ws or /ws/*
	if strings.HasPrefix(p, "/ws") || strings.HasPrefix(p, "/api/events/ws") {
		g.proxy.ServeHTTP(w, r)
		return
	}

	// 4. Everything else served by Embedded Web UI
	g.uiHandler.ServeHTTP(w, r)
}

func (g *Gateway) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Check if backend responds
	backendHealthy := false
	resp, err := http.Get(fmt.Sprintf("http://127.0.0.1:%d/health", g.cfg.BackendPort))
	if err == nil && resp.StatusCode == http.StatusOK {
		backendHealthy = true
		_ = resp.Body.Close()
	} else if resp != nil {
		_ = resp.Body.Close()
	}

	status := map[string]interface{}{
		"gateway":        "healthy",
		"backend":        backendHealthy,
		"backend_port":   g.cfg.BackendPort,
		"gateway_port":   g.cfg.GatewayPort,
		"embedded_ui":    true,
		"timestamp":      time.Now().Format(time.RFC3339),
	}

	if !backendHealthy {
		w.WriteHeader(http.StatusServiceUnavailable)
	} else {
		w.WriteHeader(http.StatusOK)
	}

	_ = json.NewEncoder(w).Encode(status)
}
