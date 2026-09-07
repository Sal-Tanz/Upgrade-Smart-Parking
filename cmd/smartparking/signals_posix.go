//go:build !windows

package main

import (
	"os"
	"os/signal"
	"syscall"
)

func notifyShutdown(sigCh chan os.Signal) {
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
}

func terminatePID(proc *os.Process) error {
	return proc.Signal(syscall.SIGTERM)
}
