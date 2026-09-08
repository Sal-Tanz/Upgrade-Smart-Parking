package bootstrap

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"smartparking/internal/assets"
	"smartparking/internal/config"
)

// EnsureEnvironment prepares required files, directories, and verifies Python libraries.
func EnsureEnvironment(cfg *config.Config) error {
	// 0. Auto-extract embedded backend and ML Python sources if missing
	if err := assets.ExtractBackendAndML(cfg.WorkDir); err != nil {
		fmt.Printf("[BOOTSTRAP] Warning: Failed to extract embedded backend/ML modules: %v\n", err)
	}

	// 1. Ensure .env files exist
	if err := copyIfMissing(filepath.Join(cfg.WorkDir, ".env.example"), filepath.Join(cfg.WorkDir, ".env")); err != nil {
		fmt.Printf("[BOOTSTRAP] Warning copying .env: %v\n", err)
	}
	if err := copyIfMissing(filepath.Join(cfg.WorkDir, "api", ".env.example"), filepath.Join(cfg.WorkDir, "api", ".env")); err != nil {
		fmt.Printf("[BOOTSTRAP] Warning copying api/.env: %v\n", err)
	}

	// 2. Ensure data directories exist
	dataDir := filepath.Join(cfg.WorkDir, "data")
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return fmt.Errorf("failed to create data directory: %w", err)
	}

	// 3. Verify Python runtime
	if _, err := exec.LookPath(cfg.PythonBin); err != nil {
		return fmt.Errorf("python interpreter '%s' not found in PATH or environment", cfg.PythonBin)
	}

	// 4. Verify critical Python packages
	checkCmd := exec.Command(cfg.PythonBin, "-c", "import fastapi, uvicorn, sqlalchemy, paho.mqtt")
	checkCmd.Env = os.Environ()
	checkCmd.Dir = cfg.WorkDir
	if err := checkCmd.Run(); err != nil {
		fmt.Println("[BOOTSTRAP] Critical Python packages missing. Attempting automatic installation...")
		reqFile := filepath.Join(cfg.WorkDir, "requirements.txt")
		if _, statErr := os.Stat(reqFile); statErr == nil {
			installCmd := exec.Command(cfg.PythonBin, "-m", "pip", "install", "-r", "requirements.txt")
			installCmd.Stdout = os.Stdout
			installCmd.Stderr = os.Stderr
			installCmd.Dir = cfg.WorkDir
			if installErr := installCmd.Run(); installErr != nil {
				return fmt.Errorf("automatic pip install failed: %w. Please ensure dependencies in requirements.txt are installed", installErr)
			}
			fmt.Println("[BOOTSTRAP] Dependencies installed successfully.")
		} else {
			fmt.Printf("[BOOTSTRAP] Warning: %s not found. Proceeding with caution.\n", reqFile)
		}
	}

	// 5. Auto-extract embedded ML model weights if missing
	if err := assets.ExtractModels(cfg.WorkDir); err != nil {
		fmt.Printf("[BOOTSTRAP] Warning: Failed to extract embedded models: %v\n", err)
	}

	// 6. Verify ML model weights
	modelCandidates := []string{
		filepath.Join(cfg.WorkDir, "runs", "detect", "alpr_plate_detector", "weights", "best.pt"),
		filepath.Join(cfg.WorkDir, "ml", "models", "best.pt"),
		filepath.Join(cfg.WorkDir, "yolov8n.pt"),
		filepath.Join(cfg.WorkDir, "yolo26n.pt"),
	}
	var foundModels []string
	for _, m := range modelCandidates {
		if fi, err := os.Stat(m); err == nil && !fi.IsDir() && fi.Size() > 0 {
			foundModels = append(foundModels, filepath.Base(m))
		}
	}
	if len(foundModels) > 0 {
		fmt.Printf("[BOOTSTRAP] Ready ML model weights: %s\n", strings.Join(foundModels, ", "))
	} else {
		fmt.Println("[BOOTSTRAP] Warning: No YOLO weights detected in default paths. ALPR may run in fallback mode.")
	}

	return nil
}

func copyIfMissing(src, dst string) error {
	if _, err := os.Stat(dst); err == nil {
		return nil // destination already exists
	}
	if _, err := os.Stat(src); os.IsNotExist(err) {
		return nil // source template doesn't exist
	}

	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	if err == nil {
		fmt.Printf("[BOOTSTRAP] Initialized %s from %s\n", filepath.Base(dst), filepath.Base(src))
	}
	return err
}
