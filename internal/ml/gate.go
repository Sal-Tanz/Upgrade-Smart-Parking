package ml

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"smartparking/internal/config"
)

// RunGate executes the dual-lane gate detection script (gate_detection.py).
func RunGate(cfg *config.Config, args []string) error {
	scriptPath := filepath.Join(cfg.WorkDir, "gate_detection.py")
	if _, err := os.Stat(scriptPath); err != nil {
		return fmt.Errorf("gate_detection.py not found at %s", scriptPath)
	}

	cmdArgs := append([]string{scriptPath}, args...)
	cmd := exec.Command(cfg.PythonBin, cmdArgs...)
	cmd.Dir = cfg.WorkDir
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	env := os.Environ()
	env = append(env, fmt.Sprintf("PYTHONPATH=%s:%s", cfg.WorkDir, os.Getenv("PYTHONPATH")))
	cmd.Env = env

	fmt.Printf("[GATE] Running: %s %s %v\n", cfg.PythonBin, scriptPath, args)
	return cmd.Run()
}
