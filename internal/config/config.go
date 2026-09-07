package config

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

// Config holds runtime configuration for the smartparking system.
type Config struct {
	GatewayPort int
	BackendPort int
	Host        string
	PythonBin   string
	WorkDir     string
	DevMode     bool
}

// LoadConfig initializes configuration from flags, environment, and .env files.
func LoadConfig(gatewayPort, backendPort int, host string, devMode bool) (*Config, error) {
	workDir, err := os.Getwd()
	if err != nil {
		return nil, fmt.Errorf("failed to get working directory: %w", err)
	}

	// Try loading root .env or api/.env
	loadEnvFile(filepath.Join(workDir, ".env"))
	loadEnvFile(filepath.Join(workDir, "api", ".env"))

	// Default ports if not specified by flags
	if gatewayPort <= 0 {
		if envPort := os.Getenv("PORT"); envPort != "" {
			if p, err := strconv.Atoi(envPort); err == nil {
				gatewayPort = p
			}
		}
		if gatewayPort <= 0 {
			gatewayPort = 8090
		}
	}

	if backendPort <= 0 {
		if envBackendPort := os.Getenv("BACKEND_PORT"); envBackendPort != "" {
			if p, err := strconv.Atoi(envBackendPort); err == nil {
				backendPort = p
			}
		}
		if backendPort <= 0 {
			backendPort = 8008
		}
	}

	if host == "" {
		host = os.Getenv("HOST")
		if host == "" {
			host = "0.0.0.0"
		}
	}

	pythonBin := detectPython(workDir)

	return &Config{
		GatewayPort: gatewayPort,
		BackendPort: backendPort,
		Host:        host,
		PythonBin:   pythonBin,
		WorkDir:     workDir,
		DevMode:     devMode,
	}, nil
}

// detectPython locates the best Python 3 interpreter in virtualenvs or system.
func detectPython(workDir string) string {
	if custom := os.Getenv("PYTHON_BIN"); custom != "" {
		if path, err := exec.LookPath(custom); err == nil {
			return path
		}
	}

	candidates := []string{
		filepath.Join(workDir, ".venv", "bin", "python"),
		filepath.Join(workDir, "venv", "bin", "python"),
		filepath.Join(workDir, ".venv", "bin", "python3"),
		filepath.Join(workDir, "venv", "bin", "python3"),
		"python3",
		"python",
	}

	for _, c := range candidates {
		if filepath.IsAbs(c) || strings.Contains(c, string(filepath.Separator)) {
			if fi, err := os.Stat(c); err == nil && !fi.IsDir() {
				return c
			}
		} else {
			if path, err := exec.LookPath(c); err == nil {
				return path
			}
		}
	}

	return "python3"
}

// loadEnvFile reads a simple KEY=VALUE file and sets into os environment if not present.
func loadEnvFile(path string) {
	f, err := os.Open(path)
	if err != nil {
		return
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			k := strings.TrimSpace(parts[0])
			v := strings.TrimSpace(parts[1])
			v = strings.Trim(v, `"'`)
			if os.Getenv(k) == "" {
				os.Setenv(k, v)
			}
		}
	}
}
