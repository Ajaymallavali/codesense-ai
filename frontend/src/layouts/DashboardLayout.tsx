import React, { ReactNode } from "react";
import { User } from "../types";
import { Sidebar } from "../components/Sidebar";
import { Navbar } from "../components/Navbar";
import { CyberBackground } from "../components/CyberBackground";

interface DashboardLayoutProps {
  user: User;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onOpenImportModal: () => void;
  onLogout: () => void;
  children: ReactNode;
}

export function DashboardLayout({
  user,
  activeTab,
  onTabChange,
  onOpenImportModal,
  onLogout,
  children,
}: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex relative selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* High-Tech Cyber Dynamic Background & Plasma Glows */}
      <CyberBackground />

      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={onTabChange} />

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-64 flex flex-col min-w-0 z-10">
        <Navbar
          user={user}
          activeTab={activeTab}
          onNavigate={onTabChange}
          onOpenImportModal={onOpenImportModal}
          onLogout={onLogout}
        />

        <main className="flex-1 p-5 sm:p-8 space-y-6">
          {children}
        </main>
      </div>
    </div>
  );
}
