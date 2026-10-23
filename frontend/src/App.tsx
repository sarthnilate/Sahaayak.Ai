import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Navbar } from './components/common/Navbar';
import { LoginView } from './components/views/LoginView';
import { SubmitReportView } from './components/views/SubmitReportView';
import { DashboardView } from './components/views/DashboardView';
import { ReportsView } from './components/views/ReportsView';
import { IncidentsView } from './components/views/IncidentsView';
import { TasksView } from './components/views/TasksView';
import { AuditView } from './components/views/AuditView';
import { getHealth, listIncidents, listReports, listTasks, seedDemoData } from './services/api';
import { Incident, Report, Task, SystemHealth } from './types';
import { AlertCircle, Loader2 } from 'lucide-react';

function AuthenticatedApp() {
  const { user, hasRole } = useAuth();
  const defaultTab = hasRole('coordinator', 'admin') ? 'dashboard' : 'submit';
  const [activeTab, setActiveTab] = useState<string>(defaultTab);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);

  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSeeding, setIsSeeding] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [h, incList, repList, taskList] = await Promise.all([
        getHealth().catch(() => null),
        hasRole('coordinator', 'admin') ? listIncidents().catch(() => []) : Promise.resolve([]),
        hasRole('coordinator', 'admin') ? listReports().catch(() => ({ items: [], total: 0, page: 1, limit: 20, pages: 0 })) : Promise.resolve({ items: [], total: 0, page: 1, limit: 20, pages: 0 }),
        hasRole('coordinator', 'admin') ? listTasks().catch(() => []) : Promise.resolve([])
      ]);

      setHealth(h);
      const incItems = Array.isArray(incList) ? incList : (incList as any)?.items || [];
      setIncidents(incItems as Incident[]);
      const reportItems = Array.isArray(repList) ? repList : (repList as any).items || [];
      setReports(reportItems);
      setTasks(taskList as Task[]);

      // If database is empty and user is admin/coordinator, automatically seed
      if (hasRole('coordinator', 'admin') && incItems.length === 0 && reportItems.length === 0) {
        await handleSeedDemo();
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Error connecting to backend services.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSeedDemo = async () => {
    setIsSeeding(true);
    try {
      await seedDemoData();
      const [incList, repList, taskList] = await Promise.all([
        listIncidents(),
        listReports(),
        listTasks()
      ]);
      const incItems = Array.isArray(incList) ? incList : (incList as any)?.items || [];
      setIncidents(incItems);
      const reportItems = Array.isArray(repList) ? repList : (repList as any).items || [];
      setReports(reportItems);
      setTasks(taskList);
      if (incItems.length > 0 && !selectedIncidentId) {
        setSelectedIncidentId(incItems[0].id);
      }
    } catch (err: any) {
      setErrorMessage('Failed to seed demo data: ' + err.message);
    } finally {
      setIsSeeding(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleNavigate = (tab: string, incidentId?: string) => {
    if (incidentId) {
      setSelectedIncidentId(incidentId);
    }
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#0B0B0B] text-white flex flex-col font-sans bg-grid-cyber selection:bg-[#FF2DA8] selection:text-white">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        onSeedDemo={handleSeedDemo}
        isSeeding={isSeeding}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        
        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-[#351316] border border-[#FF5C68]/50 text-xs font-mono text-[#FF5C68] flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={loadData}
              className="px-3 py-1 rounded bg-[#FF5C68] text-white font-bold hover:bg-[#ff3b4b]"
            >
              RETRY
            </button>
          </div>
        )}

        {activeTab === 'submit' && <SubmitReportView />}

        {activeTab === 'dashboard' && hasRole('coordinator', 'admin') && (
          <DashboardView
            incidents={incidents}
            reports={reports}
            tasks={tasks}
            onNavigate={handleNavigate}
            onRefresh={loadData}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'reports' && hasRole('coordinator', 'admin') && (
          <ReportsView
            reports={reports}
            onRefresh={loadData}
            isLoading={isLoading}
            onNavigateToIncident={(id) => handleNavigate('incidents', id)}
          />
        )}

        {activeTab === 'incidents' && hasRole('coordinator', 'admin') && (
          <IncidentsView
            incidents={incidents}
            selectedIncidentId={selectedIncidentId}
            onRefresh={loadData}
            isLoading={isLoading}
            onNavigateToReport={(id) => handleNavigate('reports', id)}
          />
        )}

        {activeTab === 'tasks' && hasRole('coordinator', 'admin') && (
          <TasksView
            tasks={tasks}
            onRefresh={loadData}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'audit' && hasRole('coordinator', 'admin') && (
          <AuditView
            health={health}
          />
        )}

      </main>

      {/* Minimal Operational Footer */}
      <footer className="border-t border-[#1C1C1C] bg-[#070707] py-4 px-4 sm:px-8 text-center sm:text-left text-xs font-mono text-[#666]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>SAHAAYAK AI • DESIGNED FOR CIVIC RESILIENCE & CRISIS INTELLIGENCE</span>
          <span className="text-[#A7A7A7]">
            AI RECOMMENDATION • HUMAN COORDINATOR AUTHORIZED
          </span>
        </div>
      </footer>
    </div>
  );
}

function AppContent() {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0B0B0B] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-[#FF2DA8] animate-spin mx-auto mb-3" />
          <p className="text-xs font-mono text-[#A7A7A7]">INITIALIZING SESSION...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginView />;
  }

  return <AuthenticatedApp />;
}

export function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
