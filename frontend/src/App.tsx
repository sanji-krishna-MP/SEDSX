import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { LandingPage } from './components/LandingPage';
import { EvidenceSidebar } from './components/EvidenceSidebar';
import { OriginalsPreview } from './components/OriginalsPreview';
import { RegisteredComparison } from './components/RegisteredComparison';
import { MetricsTabs } from './components/MetricsTabs';
import { FormulaModal } from './components/FormulaModal';
import { UploadView } from './components/UploadView';
import { HistoryView } from './components/HistoryView';
import { MetricDetail, RunSummary, MatchPoint, CheckpointRecord } from './types';

export type ViewState = 'landing' | 'upload' | 'dashboard' | 'history';

export function App() {
  const [currentView, setCurrentView] = useState<ViewState>('landing');
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runSummary, setRunSummary] = useState<RunSummary | null>(null);
  const [assets, setAssets] = useState<Record<string, string>>({});
  const [metrics, setMetrics] = useState<MetricDetail[]>([]);
  const [matches, setMatches] = useState<MatchPoint[]>([]);
  const [checkpoints, setCheckpoints] = useState<CheckpointRecord[]>([]);

  const [selectedMetric, setSelectedMetric] = useState<MetricDetail | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  const pollIntervalRef = useRef<any>(null);

  // Poll active run status until terminal state
  const pollRunStatus = async (runId: string) => {
    try {
      const res = await fetch(`/api/runs/${runId}`);
      if (!res.ok) return;
      const data = await res.json();
      setRunSummary(data.run);
      setAssets(data.assets || {});

      const status = data.run.status;
      if (['completed', 'inconclusive', 'failed', 'cancelled'].includes(status)) {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        // Fetch metrics and matches
        fetchRunDetails(runId);
      }
    } catch (e) {
      console.error('Polling error:', e);
    }
  };

  const fetchRunDetails = async (runId: string) => {
    try {
      const [resRun, resMetrics, resMatches] = await Promise.all([
        fetch(`/api/runs/${runId}`),
        fetch(`/api/runs/${runId}/metrics`),
        fetch(`/api/runs/${runId}/matches`)
      ]);

      if (resRun.ok) {
        const d = await resRun.json();
        setRunSummary(d.run);
        setAssets(d.assets || {});
      }
      if (resMetrics.ok) {
        const d = await resMetrics.json();
        setMetrics(d.metrics || []);
      }
      if (resMatches.ok) {
        const d = await resMatches.json();
        setMatches(d.matches || []);
        setCheckpoints(d.checkpoints || []);
      }
    } catch (e) {
      console.error('Error fetching run details:', e);
    }
  };

  const handleStartRun = async (formData: FormData) => {
    setIsSubmitting(true);
    try {
      const res = await fetch('/api/runs', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        const runId = data.id;
        setActiveRunId(runId);
        setCurrentView('dashboard');

        // Start polling
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = setInterval(() => pollRunStatus(runId), 800);
      }
    } catch (e) {
      console.error('Error creating run:', e);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLoadDemo = async () => {
    setIsDemoLoading(true);
    try {
      const res = await fetch('/api/runs/demo', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const runId = data.id;
        setActiveRunId(runId);
        setCurrentView('dashboard');

        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = setInterval(() => pollRunStatus(runId), 800);
      }
    } catch (e) {
      console.error('Error launching demo run:', e);
    } finally {
      setIsDemoLoading(false);
    }
  };

  const handleSelectRun = (runId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    setActiveRunId(runId);
    fetchRunDetails(runId);
    setCurrentView('dashboard');
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const runParam = params.get('run');
    if (runParam) {
      handleSelectRun(runParam);
    }
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-[#020617] text-slate-100">
      {/* Show Navbar on operational pages */}
      {currentView !== 'landing' && (
        <Navbar
          currentView={currentView}
          setCurrentView={setCurrentView}
          activeRun={runSummary}
          onLoadDemo={handleLoadDemo}
          isDemoLoading={isDemoLoading}
        />
      )}

      {/* Main Content Areas */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {currentView === 'landing' && (
          <LandingPage
            onStartUpload={() => setCurrentView('upload')}
            onViewHistory={() => setCurrentView('history')}
            onLoadDemo={handleLoadDemo}
            isDemoLoading={isDemoLoading}
          />
        )}

        {currentView === 'upload' && (
          <UploadView
            onStartComparison={handleStartRun}
            isSubmitting={isSubmitting}
            onLoadDemo={handleLoadDemo}
            isDemoLoading={isDemoLoading}
          />
        )}

        {currentView === 'history' && (
          <HistoryView
            onSelectRun={handleSelectRun}
            activeRunId={activeRunId || undefined}
          />
        )}

        {currentView === 'dashboard' && runSummary && (
          <div className="flex-1 flex overflow-hidden">
            {/* Left: Evidence Sidebar */}
            <EvidenceSidebar
              metrics={metrics}
              run={runSummary}
              onSelectMetric={(m) => setSelectedMetric(m)}
            />

            {/* Right: Primary Layout */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Top Center: Reference & Top Right: Source */}
              <OriginalsPreview
                run={runSummary}
                assets={assets}
              />

              {/* Wide Registered Comparison View */}
              <RegisteredComparison
                run={runSummary}
                assets={assets}
              />

              {/* Bottom Tabs: Preprocessing, Comparison Calculations, Matches, Details */}
              <MetricsTabs
                metrics={metrics}
                matches={matches}
                checkpoints={checkpoints}
                run={runSummary}
                onSelectMetric={(m) => setSelectedMetric(m)}
              />
            </div>
          </div>
        )}

        {currentView === 'dashboard' && !runSummary && (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
            <p className="text-sm">No run selected.</p>
            <div className="mt-3 flex items-center gap-3">
              <button
                onClick={() => setCurrentView('upload')}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors"
              >
                Upload Images
              </button>
              <button
                onClick={handleLoadDemo}
                disabled={isDemoLoading}
                className="px-4 py-2 bg-emerald-700/80 hover:bg-emerald-600 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
              >
                {isDemoLoading ? 'Loading Demo...' : 'Load Demo'}
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Formula Drilldown Modal */}
      <FormulaModal
        metric={selectedMetric}
        onClose={() => setSelectedMetric(null)}
      />
    </div>
  );
}

export default App;
