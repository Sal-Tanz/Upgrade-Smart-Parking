package ml

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"smartparking/internal/config"
)

// RunTrain executes model training for ALPR or slot occupancy.
func RunTrain(cfg *config.Config, args []string) error {
	scriptName := filepath.Join("ml", "training", "train_alpr.py")
	if len(args) > 0 && args[0] == "slot" {
		scriptName = filepath.Join("ml", "training", "train_slot.py")
		args = args[1:]
	} else if len(args) > 0 && args[0] == "alpr" {
		args = args[1:]
	}

	scriptPath := filepath.Join(cfg.WorkDir, scriptName)
	if _, err := os.Stat(scriptPath); err != nil {
		return fmt.Errorf("%s not found at %s", scriptName, scriptPath)
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

	fmt.Printf("[TRAIN] Running: %s %s %v\n", cfg.PythonBin, scriptPath, args)
	return cmd.Run()
}
