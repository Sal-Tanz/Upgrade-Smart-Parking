import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { CanvasEditor } from "@/components/parking/canvas-editor";

export default function ParkingEditorPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title="Parking Area Editor" subtitle="Draw parking slot polygons" />
        <main className="flex-1 overflow-y-auto p-6">
          <CanvasEditor />
        </main>
      </div>
    </div>
  );
}