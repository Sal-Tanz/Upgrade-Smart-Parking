import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { PlateRegistration } from "@/components/plate/plate-registration";

export default function PlateRegisterPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title="Register Plate" subtitle="Add plate images to training dataset" />
        <main className="flex-1 overflow-y-auto p-6">
          <PlateRegistration />
        </main>
      </div>
    </div>
  );
}