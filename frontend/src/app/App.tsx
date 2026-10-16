import React, { useEffect, useState } from "react";
import { Analysis, Finding, Repository } from "../types";
import { useAuth } from "../hooks/useAuth";
import { githubApi } from "../services/githubApi";
import { analysisApi } from "../services/analysisApi";
import { ProtectedRoute } from "../routes/ProtectedRoute";
import { DashboardLayout } from "../layouts/DashboardLayout";
import { Dashboard } from "../pages/Dashboard";
import { RepositoryPage } from "../pages/Repository";
import { AnalysisPage } from "../pages/Analysis";
import { ReportsPage } from "../pages/Reports";
import { SettingsPage } from "../pages/Settings";

export function App() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<string>("dashboard");

  // Repository & Analysis Shared State
  const [importedRepos, setImportedRepos] = useState<Repository[]>([]);
  const [activeRepo, setActiveRepo] = useState<Repository | null>(null);
  const [latestAnalysis, setLatestAnalysis] = useState<Analysis | null>(null);
  const [findingsList, setFindingsList] = useState<Finding[]>([]);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  // Focus specific file/finding when navigated from dashboard table
  const [targetFindingFile, setTargetFindingFile] = useState<string | null>(null);
  const [targetFindingId, setTargetFindingId] = useState<string | null>(null);

  // Fetch imported repos on initial mount
  useEffect(() => {
    if (!user) return;
    githubApi
      .getImportedRepositories()
      .then((repos) => {
        setImportedRepos(repos);
        if (repos.length > 0 && !activeRepo) {
          setActiveRepo(repos[0]);
        }
      })
      .catch((err) => console.error("Error loading repositories:", err));
  }, [user]);

  // Load latest analysis and findings whenever activeRepo changes
  useEffect(() => {
    if (!activeRepo) {
      setLatestAnalysis(null);
      setFindingsList([]);
      return;
    }

    loadAnalysis(activeRepo.id);
  }, [activeRepo]);

  // Polling for running analysis
  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    if (
      activeRepo &&
      latestAnalysis &&
      (latestAnalysis.status === "RUNNING" ||
        latestAnalysis.status === "PENDING" ||
        latestAnalysis.status === "SCANNING")
    ) {
      timer = setInterval(() => {
        loadAnalysis(activeRepo.id);
      }, 2000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [activeRepo, latestAnalysis?.status]);

  async function loadAnalysis(repoId: string) {
    setIsLoadingAnalysis(true);
    try {
      const data = await analysisApi.getLatestAnalysis(repoId);
      setLatestAnalysis(data);
      if (data && data.status === "COMPLETED" && data.id) {
        const findings = await analysisApi.getFindings(data.id);
        setFindingsList(findings);
      } else {
        setFindingsList([]);
      }
    } catch (err) {
      console.error("Failed to fetch analysis:", err);
    } finally {
      setIsLoadingAnalysis(false);
    }
  }

  async function handleTriggerAnalysis() {
    if (!activeRepo) return;
    setIsLoadingAnalysis(true);
    try {
      const triggered = await analysisApi.triggerAnalysis(activeRepo.id);
      setLatestAnalysis(triggered);
    } catch (err) {
      console.error("Failed to trigger analysis:", err);
    } finally {
      setIsLoadingAnalysis(false);
    }
  }

  function handleNavigateToReview(filePath?: string, findingId?: string) {
    if (filePath) setTargetFindingFile(filePath);
    if (findingId) setTargetFindingId(findingId);
    setActiveTab("review");
  }

  return (
    <ProtectedRoute>
      {user && (
        <DashboardLayout
          user={user}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenImportModal={() => {
            setActiveTab("repositories");
            setShowImportModal(true);
          }}
          onLogout={logout}
        >
          {activeTab === "dashboard" && (
            <Dashboard
              activeRepo={activeRepo}
              latestAnalysis={latestAnalysis}
              findingsList={findingsList}
              isLoadingAnalysis={isLoadingAnalysis}
              onTriggerAnalysis={handleTriggerAnalysis}
              onNavigateToReview={handleNavigateToReview}
              onOpenImportModal={() => {
                setActiveTab("repositories");
                setShowImportModal(true);
              }}
            />
          )}

          {activeTab === "repositories" && (
            <RepositoryPage
              importedRepos={importedRepos}
              activeRepo={activeRepo}
              onSelectRepo={(repo) => setActiveRepo(repo)}
              onRepoImported={(newRepo) => {
                setImportedRepos((prev) => [newRepo, ...prev.filter((r) => r.id !== newRepo.id && r.fullName !== newRepo.fullName)]);
                setActiveRepo(newRepo);
              }}
              onNavigateToDashboard={() => setActiveTab("dashboard")}
              showImportModal={showImportModal}
              setShowImportModal={setShowImportModal}
            />
          )}

          {activeTab === "review" && (
            <AnalysisPage
              activeRepo={activeRepo}
              latestAnalysis={latestAnalysis}
              findingsList={findingsList}
              initialFindingFile={targetFindingFile}
              initialFindingId={targetFindingId}
            />
          )}

          {activeTab === "reports" && <ReportsPage activeRepo={activeRepo} />}

          {activeTab === "settings" && <SettingsPage user={user} />}
        </DashboardLayout>
      )}
    </ProtectedRoute>
  );
}
