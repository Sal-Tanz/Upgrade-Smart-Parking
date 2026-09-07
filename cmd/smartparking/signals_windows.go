//go:build windows

package main

import (
	"os"
	"os/signal"
)

func notifyShutdown(sigCh chan os.Signal) {
	signal.Notify(sigCh, os.Interrupt)
}

func terminatePID(proc *os.Process) error {
	return proc.Kill()
}
