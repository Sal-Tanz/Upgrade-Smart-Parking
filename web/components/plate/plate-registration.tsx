"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload, X, CheckCircle } from "lucide-react";

export function PlateRegistration() {
  const [files, setFiles] = useState<File[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [plateText, setPlateText] = useState("");
  const [vehicleType, setVehicleType] = useState("");
  const [lighting, setLighting] = useState("");
  const [angle, setAngle] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
    if (acceptedFiles.length > 0 && !preview) {
      setPreview(URL.createObjectURL(acceptedFiles[0]));
    }
  }, [preview]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".png", ".jpg", ".jpeg"] },
    maxFiles: 10,
    maxSize: 10485760,
  });

  function removeFile(index: number) {
    const newFiles = files.filter((_, i) => i !== index);
    setFiles(newFiles);
    if (newFiles.length === 0) {
      setPreview(null);
    } else if (preview) {
      URL.revokeObjectURL(preview);
      setPreview(URL.createObjectURL(newFiles[0]));
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setFiles([]);
      setPreview(null);
      setPlateText("");
      setVehicleType("");
      setLighting("");
      setAngle("");
    }, 3000);
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">Upload Plat Nomor</h2>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
            isDragActive ? "border-accent bg-accent/10" : "border-border hover:border-accent/50"
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-10 w-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              {files.length > 0
                ? `${files.length} file(s) selected — drop more or click`
                : "Drag & drop images here, or click to select"}
            </p>
            <p className="text-xs text-muted-foreground">PNG, JPG up to 10MB (max 10 files)</p>
          </div>
        </div>

        {preview && (
          <div className="mt-4 space-y-2">
            <div className="flex gap-2 overflow-x-auto pb-2">
              {files.map((file, i) => (
                <div key={i} className="relative inline-block flex-shrink-0">
                  <img
                    src={URL.createObjectURL(file)}
                    alt={`Preview ${i + 1}`}
                    className="h-32 w-auto rounded-lg border border-border object-cover"
                  />
                  <button
                    onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                    className="absolute -top-2 -right-2 p-1 rounded-full bg-red-500 text-white hover:bg-red-600 cursor-pointer"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {files.length > 0 && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4">Metadata</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="plate_text">Plat Nomor (Ground Truth)</Label>
                <Input id="plate_text" placeholder="B 1234 XYZ" value={plateText}
                  onChange={(e) => setPlateText(e.target.value)} required />
              </div>

              <div className="space-y-2">
                <Label>Jenis Kendaraan</Label>
                <Select value={vehicleType} onValueChange={setVehicleType}>
                  <SelectTrigger><SelectValue placeholder="Pilih jenis" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sedan">Sedan</SelectItem>
                    <SelectItem value="suv">SUV</SelectItem>
                    <SelectItem value="hatchback">Hatchback</SelectItem>
                    <SelectItem value="motor">Motor</SelectItem>
                    <SelectItem value="truck">Truk</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Kondisi Pencahayaan</Label>
                <Select value={lighting} onValueChange={setLighting}>
                  <SelectTrigger><SelectValue placeholder="Pilih kondisi" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="siang">Siang</SelectItem>
                    <SelectItem value="malam">Malam</SelectItem>
                    <SelectItem value="hujan">Hujan</SelectItem>
                    <SelectItem value="mendung">Mendung</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Sudut Pengambilan</Label>
                <Select value={angle} onValueChange={setAngle}>
                  <SelectTrigger><SelectValue placeholder="Pilih sudut" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="depan">Depan</SelectItem>
                    <SelectItem value="belakang">Belakang</SelectItem>
                    <SelectItem value="miring">Miring</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex gap-3">
              <Button type="submit" disabled={submitted}>
                {submitted ? "Saved to Dataset!" : "Submit"}
              </Button>
              <Button type="button" variant="outline"
                onClick={() => { setFiles([]); setPreview(null); setPlateText(""); }}>
                Reset
              </Button>
            </div>

            {submitted && (
              <div className="flex items-center gap-2 text-sm text-status-available">
                <CheckCircle className="h-4 w-4" />
                Successfully added to training dataset!
              </div>
            )}
          </form>
        </Card>
      )}
    </div>
  );
}