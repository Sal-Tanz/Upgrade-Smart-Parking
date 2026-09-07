package config_test

import (
	"testing"

	"smartparking/internal/config"
)

func TestLoadConfigDefaults(t *testing.T) {
	cfg, err := config.LoadConfig(0, 0, "", false)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if cfg.GatewayPort != 8090 {
		t.Errorf("expected default GatewayPort 8090, got %d", cfg.GatewayPort)
	}

	if cfg.BackendPort != 8008 {
		t.Errorf("expected default BackendPort 8008, got %d", cfg.BackendPort)
	}

	if cfg.Host != "0.0.0.0" {
		t.Errorf("expected default Host 0.0.0.0, got %s", cfg.Host)
	}

	if cfg.PythonBin == "" {
		t.Errorf("expected non-empty PythonBin")
	}
}

func TestLoadConfigCustomPorts(t *testing.T) {
	cfg, err := config.LoadConfig(9000, 9001, "127.0.0.1", true)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if cfg.GatewayPort != 9000 {
		t.Errorf("expected GatewayPort 9000, got %d", cfg.GatewayPort)
	}

	if cfg.BackendPort != 9001 {
		t.Errorf("expected BackendPort 9001, got %d", cfg.BackendPort)
	}

	if cfg.Host != "127.0.0.1" {
		t.Errorf("expected Host 127.0.0.1, got %s", cfg.Host)
	}

	if !cfg.DevMode {
		t.Errorf("expected DevMode to be true")
	}
}
