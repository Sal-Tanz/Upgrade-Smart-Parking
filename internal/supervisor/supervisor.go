package supervisor

import (
	"bufio"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"smartparking/internal/config"
)

// ANSI Colors
const (
	colorCyan   = "\033[36m"
	colorReset  = "\033[0m"
	colorRed    = "\033[31m"
	colorGreen  = "\033[32m"
	colorYellow = "\033[33m"
)

// Supervisor manages the lifecycle of the Python FastAPI backend process.
type Supervisor struct {
	cfg        *config.Config
	cmd        *exec.Cmd
	pgid       int
	mu         sync.Mutex
	running    bool
	done       chan struct{}
	pidFile    string
}

// NewSupervisor creates a supervisor instance for the given configuration.
func NewSupervisor(cfg *config.Config) *Supervisor {
	return &Supervisor{
		cfg:     cfg,
		done:    make(chan struct{}),
		pidFile: filepath.Join(cfg.WorkDir, ".smartparking.pid"),
	}
}

// Start spawns the FastAPI backend subprocess and monitors it.
func (s *Supervisor) Start() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.running {
		return nil
	}

	backendHost := "127.0.0.1"
	args := []string{
		"-m", "uvicorn",
		"api.main:app",
		"--host", backendHost,
		"--port", strconv.Itoa(s.cfg.BackendPort),
	}

	if s.cfg.DevMode {
		args = append(args, "--reload")
	}

	cmd := exec.Command(s.cfg.PythonBin, args...)
	cmd.Dir = s.cfg.WorkDir

	// Ensure PYTHONPATH includes working directory
	env := os.Environ()
	env = append(env, fmt.Sprintf("PYTHONPATH=%s:%s", s.cfg.WorkDir, os.Getenv("PYTHONPATH")))
	cmd.Env = env

	// Set process group so all child processes can be killed together
	setProcessGroup(cmd)

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("failed to open stdout pipe: %w", err)
	}

	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		return fmt.Errorf("failed to open stderr pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start backend: %w", err)
	}

	s.cmd = cmd
	s.running = true
	s.pgid = getProcessGroupID(cmd.Process.Pid)

	// Write PID file
	_ = os.WriteFile(s.pidFile, []byte(strconv.Itoa(cmd.Process.Pid)), 0644)

	// Stream logs with [BACKEND] tag
	go streamLog(stdoutPipe, colorCyan+"[BACKEND]"+colorReset)
	go streamLog(stderrPipe, colorCyan+"[BACKEND]"+colorReset)

	// Background monitor
	go func() {
		_ = cmd.Wait()
		s.mu.Lock()
		s.running = false
		_ = os.Remove(s.pidFile)
		s.mu.Unlock()
		close(s.done)
	}()

	return nil
}

// WaitForHealth polls the backend health endpoint until it is ready or times out.
func (s *Supervisor) WaitForHealth(timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	healthURL := fmt.Sprintf("http://127.0.0.1:%d/health", s.cfg.BackendPort)

	client := &http.Client{Timeout: 1 * time.Second}

	for time.Now().Before(deadline) {
		resp, err := client.Get(healthURL)
		if err == nil && resp.StatusCode == http.StatusOK {
			_ = resp.Body.Close()
			return nil
		}
		if resp != nil {
			_ = resp.Body.Close()
		}

		s.mu.Lock()
		if !s.running {
			s.mu.Unlock()
			return fmt.Errorf("backend process terminated unexpectedly during startup")
		}
		s.mu.Unlock()

		time.Sleep(300 * time.Millisecond)
	}

	return fmt.Errorf("timeout waiting for backend at %s", healthURL)
}

// Stop sends SIGTERM to the backend process group and waits for exit.
func (s *Supervisor) Stop() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.running || s.cmd == nil || s.cmd.Process == nil {
		_ = os.Remove(s.pidFile)
		return nil
	}

	// Send terminate signal
	terminateProcess(s.cmd, s.pgid)

	// Wait up to 5 seconds for clean exit, then kill
	waitCh := make(chan struct{})
	go func() {
		for {
			s.mu.Lock()
			r := s.running
			s.mu.Unlock()
			if !r {
				close(waitCh)
				return
			}
			time.Sleep(100 * time.Millisecond)
		}
	}()

	select {
	case <-waitCh:
		// gracefully exited
	case <-time.After(5 * time.Second):
		killProcess(s.cmd, s.pgid)
	}

	s.running = false
	_ = os.Remove(s.pidFile)
	return nil
}

// IsRunning reports whether the backend is active.
func (s *Supervisor) IsRunning() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.running
}

func streamLog(r io.Reader, prefix string) {
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		fmt.Printf("%s %s\n", prefix, scanner.Text())
	}
}
