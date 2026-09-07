"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import JSZip from "jszip";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileArchive, CheckCircle } from "lucide-react";
import { detectionApi } from "@/lib/api/client";
import { DashboardShell } from "@/components/layout/dashboard-shell";

export default function BatchUploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<{ success: number; failed: number } | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(acceptedFiles);
    setResults(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".png", ".jpg", ".jpeg"],
      "application/zip": [".zip"],
    },
    maxFiles: 50,
    maxSize: 104857600,
  });

  const processImage = async (file: File) => {
    const response = await detectionApi.detect(file);
    if (!response.success) {
      throw new Error(response.error || "Detection failed");
    }
  };

  const handleProcess = async () => {
    setProcessing(true);
    let success = 0;
    let failed = 0;

    for (const file of files) {
      try {
        if (file.name.endsWith(".zip")) {
          const zip = await JSZip.loadAsync(file);
          const entries = Object.values(zip.files);

          for (const entry of entries) {
            if (!entry.dir && entry.name.match(/\.(png|jpg|jpeg)$/i)) {
              const blob = await entry.async("blob");
              const imageFile = new File([blob], entry.name.split("/").pop() || "image.jpg", {
                type: blob.type || "image/jpeg",
              });
              await processImage(imageFile);
              success++;
            }
          }
        } else {
          await processImage(file);
          success++;
        }
      } catch (error) {
        console.error("Failed to process:", file.name, error);
        failed++;
      }
    }

    setResults({ success, failed });
    setProcessing(false);

    setTimeout(() => {
      setFiles([]);
      setResults(null);
    }, 5000);
  };

  return (
    <DashboardShell
      title="Batch Upload"
      subtitle="Upload and process multiple vehicle license plate images"
    >
      <div className="space-y-6">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4">Batch Upload Plat Nomor</h2>

          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
              isDragActive ? "border-accent bg-accent/10" : "border-border hover:border-accent/50"
            }`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-2">
              {files.length > 0 ? (
                <>
                  <FileArchive className="h-10 w-10 text-accent" />
                  <p className="text-sm text-foreground">{files.length} file(s) selected</p>
                </>
              ) : (
                <>
                  <Upload className="h-10 w-10 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Drag & drop images or ZIP files here, or click to select
                  </p>
                  <p className="text-xs text-muted-foreground">
                    PNG, JPG, ZIP up to 100MB (max 50 files)
                  </p>
                </>
              )}
            </div>
          </div>

          {files.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="text-sm text-muted-foreground">Files to process:</div>
              <ul className="text-xs text-muted-foreground space-y-1 max-h-40 overflow-y-auto">
                {files.map((file, i) => (
                  <li key={i}>• {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</li>
                ))}
              </ul>
            </div>
          )}

          {files.length > 0 && (
            <div className="mt-4">
              <Button onClick={handleProcess} disabled={processing}>
                {processing ? "Processing..." : "Process All Files"}
              </Button>
            </div>
          )}

          {results && (
            <div className="mt-4 flex items-center gap-2 text-sm text-status-available">
              <CheckCircle className="h-4 w-4" />
              Processed: {results.success} successful, {results.failed} failed
            </div>
          )}
        </Card>
      </div>
    </DashboardShell>
  );
}