package assets

import (
	"os"
	"path/filepath"
	"testing"
)

func TestExtractBackendAndML(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "smartparking-python-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	if err := ExtractBackendAndML(tempDir); err != nil {
		t.Fatalf("ExtractBackendAndML failed: %v", err)
	}

	expectedFiles := []string{
		filepath.Join(tempDir, "api", "main.py"),
		filepath.Join(tempDir, "logic", "karnaugh.py"),
		filepath.Join(tempDir, "gate_detection.py"),
		filepath.Join(tempDir, "requirements.txt"),
	}

	for _, target := range expectedFiles {
		fi, err := os.Stat(target)
		if err != nil {
			t.Errorf("Expected extracted backend/ML file %s does not exist: %v", target, err)
			continue
		}
		if fi.Size() == 0 {
			t.Errorf("Extracted file %s is empty", target)
		}
	}

	// Test idempotency
	if err := ExtractBackendAndML(tempDir); err != nil {
		t.Fatalf("Second ExtractBackendAndML call failed: %v", err)
	}
}
