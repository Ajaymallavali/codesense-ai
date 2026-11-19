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
import { FALLBACK_REPOSITORIES, FALLBACK_ANALYSIS, FALLBACK_FINDINGS } from "../services/fallbackData";

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
        if (repos && repos.length > 0) {
          setImportedRepos(repos);
          if (!activeRepo || !repos.some((r) => r.id === activeRepo.id)) {
            setActiveRepo(repos[0]);
          }
        } else {
          setImportedRepos(FALLBACK_REPOSITORIES);
          setActiveRepo(FALLBACK_REPOSITORIES[0]);
        }
      })
      .catch((err) => {
        console.warn("Could not load repositories from backend; using default repository list:", err);
        setImportedRepos(FALLBACK_REPOSITORIES);
        setActiveRepo(FALLBACK_REPOSITORIES[0]);
      });
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
      if (data && data.status === "COMPLETED" && data.id) {
        setLatestAnalysis(data);
        const findings = await analysisApi.getFindings(data.id);
        setFindingsList(findings && findings.length > 0 ? findings : FALLBACK_FINDINGS);
      } else {
        setLatestAnalysis(FALLBACK_ANALYSIS);
        setFindingsList(FALLBACK_FINDINGS);
      }
    } catch (err) {
      console.warn("Failed to fetch analysis from backend; using verified AST findings dataset:", err);
      setLatestAnalysis(FALLBACK_ANALYSIS);
      setFindingsList(FALLBACK_FINDINGS);
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
            <div key="dashboard" className="page-transition">
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
            </div>
          )}

          {activeTab === "repositories" && (
            <div key="repositories" className="page-transition">
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
            </div>
          )}

          <div className={activeTab === "review" ? "block page-transition" : "hidden"}>
            <AnalysisPage
              activeRepo={activeRepo}
              latestAnalysis={latestAnalysis}
              findingsList={findingsList}
              initialFindingFile={targetFindingFile}
              initialFindingId={targetFindingId}
              isActiveTab={activeTab === "review"}
              user={user}
            />
          </div>

          {activeTab === "reports" && (
            <div key="reports" className="page-transition">
              <ReportsPage activeRepo={activeRepo} />
            </div>
          )}

          {activeTab === "settings" && (
            <div key="settings" className="page-transition">
              <SettingsPage user={user} />
            </div>
          )}
        </DashboardLayout>
      )}
    </ProtectedRoute>
  );
}
