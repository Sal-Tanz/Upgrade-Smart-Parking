package assets

import (
	"embed"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
)

//go:embed all:python
var pythonFS embed.FS

// ExtractBackendAndML extracts embedded Python backend, logic, ML scripts, and configuration
// files into workDir if they do not already exist on disk.
func ExtractBackendAndML(workDir string) error {
	sub, err := fs.Sub(pythonFS, "python")
	if err != nil {
		// If "python" folder is empty or unused during dev, ignore
		return nil
	}

	return fs.WalkDir(sub, ".", func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if path == "." {
			return nil
		}

		targetPath := filepath.Join(workDir, path)

		if d.IsDir() {
			return os.MkdirAll(targetPath, 0755)
		}

		// Don't overwrite existing files unless 0-byte or placeholder
		if fi, err := os.Stat(targetPath); err == nil && fi.Size() > 0 {
			return nil
		}

		srcFile, err := sub.Open(path)
		if err != nil {
			return fmt.Errorf("failed to open embedded asset %s: %w", path, err)
		}
		defer srcFile.Close()

		if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
			return err
		}

		dstFile, err := os.OpenFile(targetPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
		if err != nil {
			return fmt.Errorf("failed to create target file %s: %w", targetPath, err)
		}
		defer dstFile.Close()

		if _, err := io.Copy(dstFile, srcFile); err != nil {
			return fmt.Errorf("failed to extract file %s: %w", targetPath, err)
		}

		fmt.Printf("[BOOTSTRAP] Extracted embedded backend/ML file: %s -> %s\n", path, targetPath)
		return nil
	})
}
