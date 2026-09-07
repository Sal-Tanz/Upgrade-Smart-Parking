import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";

export default function SettingsPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title="Settings" subtitle="System configuration" />
        <main className="flex-1 overflow-y-auto p-6">
          <p className="text-muted-foreground">Settings page — configure ALPR thresholds, MQTT broker, and notifications.</p>
        </main>
      </div>
    </div>
  );
}