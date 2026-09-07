package assets

import (
	"embed"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

//go:embed models/*
var ModelsFS embed.FS

// ExtractModels checks if required model weights exist in workDir.
// If any model is missing, it is automatically extracted from embedded assets.
func ExtractModels(workDir string) error {
	modelsToExtract := []struct {
		embeddedName string
		targetPaths  []string
	}{
		{
			embeddedName: "models/best.pt",
			targetPaths: []string{
				filepath.Join(workDir, "runs", "detect", "alpr_plate_detector", "weights", "best.pt"),
				filepath.Join(workDir, "ml", "models", "best.pt"),
			},
		},
		{
			embeddedName: "models/yolov8n.pt",
			targetPaths: []string{
				filepath.Join(workDir, "yolov8n.pt"),
			},
		},
		{
			embeddedName: "models/yolo26n.pt",
			targetPaths: []string{
				filepath.Join(workDir, "yolo26n.pt"),
			},
		},
	}

	for _, item := range modelsToExtract {
		for _, targetPath := range item.targetPaths {
			if fi, err := os.Stat(targetPath); err == nil && fi.Size() > 0 {
				// Target model already exists and is non-empty
				continue
			}

			if err := extractFile(ModelsFS, item.embeddedName, targetPath); err != nil {
				return fmt.Errorf("failed to extract embedded model %s to %s: %w", item.embeddedName, targetPath, err)
			}
		}
	}

	return nil
}

func extractFile(fsys embed.FS, srcPath, dstPath string) error {
	srcFile, err := fsys.Open(srcPath)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	if err := os.MkdirAll(filepath.Dir(dstPath), 0755); err != nil {
		return err
	}

	dstFile, err := os.OpenFile(dstPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		return err
	}
	defer dstFile.Close()

	if _, err := io.Copy(dstFile, srcFile); err != nil {
		return err
	}

	fmt.Printf("[BOOTSTRAP] Extracted embedded ML model: %s -> %s\n", filepath.Base(srcPath), dstPath)
	return nil
}
