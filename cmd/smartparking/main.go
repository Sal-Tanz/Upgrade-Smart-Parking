package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"smartparking/internal/bootstrap"
	"smartparking/internal/config"
	"smartparking/internal/ml"
	"smartparking/internal/proxy"
	"smartparking/internal/supervisor"
)

const (
	Version   = "1.0.0-standalone"
	ColorBlue = "\033[34m"
	ColorGreen = "\033[32m"
	ColorYellow = "\033[33m"
	ColorReset = "\033[0m"
)

func printBanner() {
	fmt.Printf("%s====================================================%s\n", ColorBlue, ColorReset)
	fmt.Printf("%s    Smart Parking System - All-in-One Binary       %s\n", ColorBlue, ColorReset)
	fmt.Printf("%s    Version: %s | Web UI + Backend + ML       %s\n", ColorBlue, Version, ColorReset)
	fmt.Printf("%s====================================================%s\n", ColorBlue, ColorReset)
}

func printUsage() {
	printBanner()
	fmt.Println("Usage: smartparking <command> [options]")
	fmt.Println()
	fmt.Println("Commands:")
	fmt.Println("  run               Start fullstack server (Web UI + Backend + Gateway) [default]")
	fmt.Println("  gate              Run dual-lane real-time ALPR gate controller")
	fmt.Println("  detect            Run video/image detection inference")
	fmt.Println("  train             Run YOLOv8 model training (alpr / slot)")
	fmt.Println("  test              Run automated pytest test suite")
	fmt.Println("  status            Check system and service health status")
	fmt.Println("  stop              Stop running background daemon")
	fmt.Println("  version           Print binary version information")
	fmt.Println()
	fmt.Println("Options for 'run':")
	fmt.Println("  --port <port>     Public gateway port (default: 8090)")
	fmt.Println("  --backend <port>  Internal backend port (default: 8008)")
	fmt.Println("  --host <host>     Host binding address (default: 0.0.0.0)")
	fmt.Println("  --dev             Enable development reload mode")
}

func main() {
	if len(os.Args) < 2 {
		runServer([]string{})
		return
	}

	command := os.Args[1]

	switch command {
	case "run":
		runServer(os.Args[2:])
	case "gate":
		runGate(os.Args[2:])
	case "detect":
		runDetect(os.Args[2:])
	case "train":
		runTrain(os.Args[2:])
	case "test":
		runTests(os.Args[2:])
	case "status":
		checkStatus()
	case "stop":
		stopServer()
	case "version", "-v", "--version":
		fmt.Printf("smartparking version %s\n", Version)
	case "help", "-h", "--help":
		printUsage()
	default:
		if strings.HasPrefix(command, "-") {
			runServer(os.Args[1:])
		} else {
			fmt.Printf("Unknown command '%s'. Run 'smartparking --help' for usage.\n", command)
			os.Exit(1)
		}
	}
}

func runServer(args []string) {
	printBanner()

	fs := flag.NewFlagSet("run", flag.ExitOnError)
	port := fs.Int("port", 8090, "Gateway public port")
	backendPort := fs.Int("backend", 8008, "Backend internal port")
	host := fs.String("host", "0.0.0.0", "Bind host")
	dev := fs.Bool("dev", false, "Development reload mode")
	_ = fs.Parse(args)

	cfg, err := config.LoadConfig(*port, *backendPort, *host, *dev)
	if err != nil {
		fmt.Printf("[ERROR] Failed to load configuration: %v\n", err)
		os.Exit(1)
	}

	// 1. Bootstrap environment
	if err := bootstrap.EnsureEnvironment(cfg); err != nil {
		fmt.Printf("[ERROR] Bootstrapping failed: %v\n", err)
		os.Exit(1)
	}

	// 2. Start Backend Supervisor
	fmt.Printf("%s[+] Starting Backend API on 127.0.0.1:%d...%s\n", ColorGreen, cfg.BackendPort, ColorReset)
	sup := supervisor.NewSupervisor(cfg)
	if err := sup.Start(); err != nil {
		fmt.Printf("[ERROR] Failed to start backend: %v\n", err)
		os.Exit(1)
	}

	// Wait for health
	fmt.Println("[+] Waiting for backend health check...")
	if err := sup.WaitForHealth(15 * time.Second); err != nil {
		fmt.Printf("%s[!] Warning: %v. Proceeding to open gateway.%s\n", ColorYellow, err, ColorReset)
	} else {
		fmt.Printf("%s[+] Backend is healthy!%s\n", ColorGreen, ColorReset)
	}

	// 3. Start Gateway & Embedded UI
	gw, err := proxy.NewGateway(cfg)
	if err != nil {
		fmt.Printf("[ERROR] Failed to initialize gateway: %v\n", err)
		_ = sup.Stop()
		os.Exit(1)
	}

	fmt.Printf("\n%s====================================================%s\n", ColorGreen, ColorReset)
	fmt.Printf("%s  Smart Parking System is LIVE!%s\n", ColorGreen, ColorReset)
	fmt.Printf("  Dashboard (Web UI): %shttp://localhost:%d%s\n", ColorBlue, cfg.GatewayPort, ColorReset)
	fmt.Printf("  API Docs (Swagger): %shttp://localhost:%d/docs%s\n", ColorBlue, cfg.GatewayPort, ColorReset)
	fmt.Printf("  Health Endpoint:    %shttp://localhost:%d/health%s\n", ColorBlue, cfg.GatewayPort, ColorReset)
	fmt.Printf("%s====================================================%s\n", ColorGreen, ColorReset)
	fmt.Printf("%sPress Ctrl+C to stop all services.%s\n\n", ColorYellow, ColorReset)

	// Graceful shutdown handler
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)

	go func() {
		<-sigCh
		fmt.Printf("\n%s[!] Shutting down Smart Parking services...%s\n", ColorYellow, ColorReset)
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		_ = gw.Shutdown(shutdownCtx)
		_ = sup.Stop()
		fmt.Printf("%s[+] All services stopped cleanly.%s\n", ColorGreen, ColorReset)
		os.Exit(0)
	}()

	if err := gw.Start(); err != nil {
		fmt.Printf("[ERROR] Gateway error: %v\n", err)
		_ = sup.Stop()
		os.Exit(1)
	}
}

func runGate(args []string) {
	cfg, err := config.LoadConfig(8080, 8001, "0.0.0.0", false)
	if err != nil {
		fmt.Printf("[ERROR] %v\n", err)
		os.Exit(1)
	}
	if err := ml.RunGate(cfg, args); err != nil {
		fmt.Printf("[ERROR] Gate detection exited with error: %v\n", err)
		os.Exit(1)
	}
}

func runDetect(args []string) {
	cfg, err := config.LoadConfig(8080, 8001, "0.0.0.0", false)
	if err != nil {
		fmt.Printf("[ERROR] %v\n", err)
		os.Exit(1)
	}
	if err := ml.RunDetect(cfg, args); err != nil {
		fmt.Printf("[ERROR] Detect exited with error: %v\n", err)
		os.Exit(1)
	}
}

func runTrain(args []string) {
	cfg, err := config.LoadConfig(8080, 8001, "0.0.0.0", false)
	if err != nil {
		fmt.Printf("[ERROR] %v\n", err)
		os.Exit(1)
	}
	if err := ml.RunTrain(cfg, args); err != nil {
		fmt.Printf("[ERROR] Training exited with error: %v\n", err)
		os.Exit(1)
	}
}

func runTests(args []string) {
	cfg, err := config.LoadConfig(8080, 8001, "0.0.0.0", false)
	if err != nil {
		fmt.Printf("[ERROR] %v\n", err)
		os.Exit(1)
	}

	cmdArgs := append([]string{"-m", "pytest"}, args...)
	cmd := exec.Command(cfg.PythonBin, cmdArgs...)
	cmd.Dir = cfg.WorkDir
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	env := os.Environ()
	env = append(env, fmt.Sprintf("PYTHONPATH=%s:%s", cfg.WorkDir, os.Getenv("PYTHONPATH")))
	cmd.Env = env

	fmt.Println("[TEST] Running automated test suite...")
	if err := cmd.Run(); err != nil {
		fmt.Printf("[TEST] Tests failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("%s[TEST] All tests passed!%s\n", ColorGreen, ColorReset)
}

func checkStatus() {
	pidFile := ".smartparking.pid"
	if pidBytes, err := os.ReadFile(pidFile); err == nil {
		pidStr := strings.TrimSpace(string(pidBytes))
		fmt.Printf("[STATUS] Active PID recorded: %s\n", pidStr)
	}

	resp, err := http.Get("http://127.0.0.1:8090/health")
	if err != nil {
		fmt.Printf("[STATUS] Gateway is NOT reachable at http://127.0.0.1:8090/health (%v)\n", err)
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	fmt.Printf("[STATUS] Gateway Response (%d): %s\n", resp.StatusCode, string(body))
}

func stopServer() {
	pidFile := ".smartparking.pid"
	pidBytes, err := os.ReadFile(pidFile)
	if err != nil {
		fmt.Println("[STOP] No active .smartparking.pid file found.")
		return
	}

	pid, err := strconv.Atoi(strings.TrimSpace(string(pidBytes)))
	if err != nil {
		fmt.Printf("[STOP] Invalid PID in %s\n", pidFile)
		return
	}

	proc, err := os.FindProcess(pid)
	if err != nil {
		fmt.Printf("[STOP] Process %d not found: %v\n", pid, err)
		return
	}

	fmt.Printf("[STOP] Sending SIGTERM to PID %d...\n", pid)
	_ = proc.Signal(syscall.SIGTERM)
	time.Sleep(1 * time.Second)
	_ = os.Remove(pidFile)
	fmt.Println("[STOP] Done.")
}
