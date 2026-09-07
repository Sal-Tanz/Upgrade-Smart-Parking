//go:build windows

package supervisor

import (
	"os/exec"
)

func setProcessGroup(cmd *exec.Cmd) {
	// Process groups handled by Windows job objects or standard proc.Kill
}

func getProcessGroupID(pid int) int {
	return pid
}

func terminateProcess(cmd *exec.Cmd, pgid int) {
	if cmd != nil && cmd.Process != nil {
		_ = cmd.Process.Kill()
	}
}

func killProcess(cmd *exec.Cmd, pgid int) {
	if cmd != nil && cmd.Process != nil {
		_ = cmd.Process.Kill()
	}
}
