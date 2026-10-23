import React, { useState, useEffect } from 'react';
import { Navbar } from './components/common/Navbar';
import { DashboardView } from './components/views/DashboardView';
import { ReportsView } from './components/views/ReportsView';
import { IncidentsView } from './components/views/IncidentsView';
import { TasksView } from './components/views/TasksView';
import { AuditView } from './components/views/AuditView';
import { getHealth, listIncidents, listReports, listTasks, seedDemoData } from './services/api';
import { Incident, Report, Task, SystemHealth } from './types';
import { AlertCircle } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
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
        listIncidents().catch(() => []),
        listReports().catch(() => []),
        listTasks().catch(() => [])
      ]);

      setHealth(h);
      setIncidents(incList);
      setReports(repList);
      setTasks(taskList);

      // If database is empty, automatically seed the official deterministic dataset
      if (incList.length === 0 && repList.length === 0) {
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
      setIncidents(incList);
      setReports(repList);
      setTasks(taskList);
      if (incList.length > 0 && !selectedIncidentId) {
        setSelectedIncidentId(incList[0].id);
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

        {activeTab === 'dashboard' && (
          <DashboardView
            incidents={incidents}
            reports={reports}
            tasks={tasks}
            onNavigate={handleNavigate}
            onRefresh={loadData}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'reports' && (
          <ReportsView
            reports={reports}
            onRefresh={loadData}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'incidents' && (
          <IncidentsView
            incidents={incidents}
            selectedIncidentId={selectedIncidentId}
            onRefresh={loadData}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'tasks' && (
          <TasksView
            tasks={tasks}
            onRefresh={loadData}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'audit' && (
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

export default App;
