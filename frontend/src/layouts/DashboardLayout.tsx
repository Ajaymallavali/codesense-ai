import React, { ReactNode } from "react";
import { User } from "../types";
import { Sidebar } from "../components/Sidebar";
import { Navbar } from "../components/Navbar";

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
    <div className="min-h-screen bg-slate-50 text-slate-800 flex">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={onTabChange} />

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-64 flex flex-col min-w-0">
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
