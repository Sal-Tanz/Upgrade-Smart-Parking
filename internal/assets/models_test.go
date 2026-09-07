package assets

import (
	"os"
	"path/filepath"
	"testing"
)

func TestEmbeddedModelsExist(t *testing.T) {
	requiredFiles := []string{
		"models/best.pt",
		"models/yolov8n.pt",
		"models/yolo26n.pt",
	}

	for _, req := range requiredFiles {
		f, err := ModelsFS.Open(req)
		if err != nil {
			t.Fatalf("Embedded model %s not found in ModelsFS: %v", req, err)
		}
		fi, err := f.Stat()
		_ = f.Close()
		if err != nil {
			t.Fatalf("Failed to stat %s: %v", req, err)
		}
		if fi.Size() == 0 {
			t.Fatalf("Embedded model %s is empty (size 0)", req)
		}
	}
}

func TestExtractModels(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "smartparking-models-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	if err := ExtractModels(tempDir); err != nil {
		t.Fatalf("ExtractModels failed: %v", err)
	}

	expectedTargets := []string{
		filepath.Join(tempDir, "runs", "detect", "alpr_plate_detector", "weights", "best.pt"),
		filepath.Join(tempDir, "ml", "models", "best.pt"),
		filepath.Join(tempDir, "yolov8n.pt"),
		filepath.Join(tempDir, "yolo26n.pt"),
	}

	for _, target := range expectedTargets {
		fi, err := os.Stat(target)
		if err != nil {
			t.Errorf("Expected extracted file %s does not exist: %v", target, err)
			continue
		}
		if fi.Size() == 0 {
			t.Errorf("Extracted file %s is empty", target)
		}
	}

	// Test idempotency (calling again should not fail)
	if err := ExtractModels(tempDir); err != nil {
		t.Fatalf("Second ExtractModels call failed: %v", err)
	}
}
