"use client";

import { useRef, useState, useEffect, useCallback } from "react";
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
import { Plus, Trash2, Save, RotateCcw } from "lucide-react";

interface Point {
  x: number;
  y: number;
}

interface Slot {
  id: string;
  points: Point[];
  cluster: "Merah" | "Orange";
}

export function CanvasEditor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [currentPoints, setCurrentPoints] = useState<Point[]>([]);
  const [currentSlotId, setCurrentSlotId] = useState("");
  const [currentCluster, setCurrentCluster] = useState<"Merah" | "Orange">("Merah");
  const [drawing, setDrawing] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!drawing) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const newPoint = { x, y };
    const newPoints = [...currentPoints, newPoint];

    setCurrentPoints(newPoints);

    // Draw point
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = currentCluster === "Merah" ? "#ef4444" : "#f97316";
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    // Auto-complete polygon when 4 points are drawn
    if (newPoints.length === 4) {
      completePolygon();
    }
  }, [drawing, currentPoints, currentCluster]);

  const completePolygon = useCallback(() => {
    if (currentPoints.length !== 4 || !currentSlotId) {
      alert("Please draw exactly 4 points and provide a slot ID");
      return;
    }

    const newSlot: Slot = {
      id: currentSlotId,
      points: currentPoints,
      cluster: currentCluster,
    };

    setSlots([...slots, newSlot]);
    setCurrentPoints([]);
    setCurrentSlotId("");

    // Draw completed polygon
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.strokeStyle = currentCluster === "Merah" ? "#ef4444" : "#f97316";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(currentPoints[0].x, currentPoints[0].y);
    for (let i = 1; i < currentPoints.length; i++) {
      ctx.lineTo(currentPoints[i].x, currentPoints[i].y);
    }
    ctx.closePath();
    ctx.stroke();

    // Add label
    const centerX = currentPoints.reduce((sum, p) => sum + p.x, 0) / 4;
    const centerY = currentPoints.reduce((sum, p) => sum + p.y, 0) / 4;
    ctx.fillStyle = "#fff";
    ctx.font = "bold 14px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(currentSlotId, centerX, centerY);

    setDrawing(false);
  }, [currentPoints, currentSlotId, currentCluster, slots]);

  const handleUndo = () => {
    if (currentPoints.length > 0) {
      const newPoints = currentPoints.slice(0, -1);
      setCurrentPoints(newPoints);

      // Redraw
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Redraw all slots
      slots.forEach(slot => {
        ctx.strokeStyle = slot.cluster === "Merah" ? "#ef4444" : "#f97316";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(slot.points[0].x, slot.points[0].y);
        for (let i = 1; i < slot.points.length; i++) {
          ctx.lineTo(slot.points[i].x, slot.points[i].y);
        }
        ctx.closePath();
        ctx.stroke();

        const centerX = slot.points.reduce((sum, p) => sum + p.x, 0) / 4;
        const centerY = slot.points.reduce((sum, p) => sum + p.y, 0) / 4;
        ctx.fillStyle = "#fff";
        ctx.font = "bold 14px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(slot.id, centerX, centerY);
      });

      // Redraw current points
      newPoints.forEach(point => {
        ctx.fillStyle = currentCluster === "Merah" ? "#ef4444" : "#f97316";
        ctx.beginPath();
        ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
        ctx.fill();
      });
    }
  };

  const handleSave = () => {
    const data = {
      slots: slots.map(slot => ({
        id: slot.id,
        cluster: slot.cluster,
        polygon: slot.points.map(p => [p.x, p.y]),
      })),
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "slot_config.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleReset = () => {
    setSlots([]);
    setCurrentPoints([]);
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">Parking Area Editor</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Click Add Slot to start drawing a 4-point polygon on the canvas
        </p>

        <div className="flex gap-3 mb-4">
          <div className="space-y-2">
            <Label htmlFor="slot_id">Slot ID</Label>
            <Input
              id="slot_id"
              placeholder="M-01"
              value={currentSlotId}
              onChange={(e) => setCurrentSlotId(e.target.value)}
              disabled={drawing}
            />
          </div>

          <div className="space-y-2">
            <Label>Cluster</Label>
            <Select
              value={currentCluster}
              onValueChange={(v) => setCurrentCluster(v as "Merah" | "Orange")}
              disabled={drawing}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Merah">Merah</SelectItem>
                <SelectItem value="Orange">Orange</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-end">
            <Button
              onClick={() => setDrawing(true)}
              disabled={drawing || !currentSlotId}
              className="mb-0"
            >
              <Plus className="h-4 w-4 mr-2" />
              {drawing ? "Drawing..." : "Add Slot"}
            </Button>
          </div>

          {drawing && (
            <div className="flex items-end">
              <Button onClick={handleUndo} variant="outline" className="mb-0">
                <RotateCcw className="h-4 w-4 mr-2" />
                Undo
              </Button>
            </div>
          )}
        </div>

        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          onClick={handleCanvasClick}
          className="border border-border rounded-lg bg-background cursor-crosshair"
        />

        <div className="mt-4 flex gap-3">
          <Button onClick={handleSave} disabled={slots.length === 0}>
            <Save className="h-4 w-4 mr-2" />
            Export Config
          </Button>
          <Button onClick={handleReset} variant="outline" disabled={slots.length === 0}>
            <Trash2 className="h-4 w-4 mr-2" />
            Reset All
          </Button>
        </div>

        {slots.length > 0 && (
          <div className="mt-4 text-sm text-muted-foreground">
            {slots.length} slot(s) configured
          </div>
        )}
      </Card>
    </div>
  );
}