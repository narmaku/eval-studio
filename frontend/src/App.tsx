import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AppShell } from '@/components/layout/AppShell';

const Dashboard = lazy(() => import('@/pages/Dashboard'));
const EvaluateIndex = lazy(() => import('@/pages/EvaluateIndex'));
const QAEvaluation = lazy(() => import('@/pages/QAEvaluation'));
const AgentEvaluation = lazy(() => import('@/pages/AgentEvaluation'));
const RAGEvaluation = lazy(() => import('@/pages/RAGEvaluation'));
const ArenaComparison = lazy(() => import('@/pages/ArenaComparison'));
const Datasets = lazy(() => import('@/pages/Datasets'));
const Results = lazy(() => import('@/pages/Results'));
const Environments = lazy(() => import('@/pages/Environments'));
const Settings = lazy(() => import('@/pages/Settings'));
const NotFound = lazy(() => import('@/pages/NotFound'));

function Loading() {
  return (
    <div className="flex items-center justify-center py-12">
      <p className="text-muted-foreground">Loading...</p>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Dashboard />} />
              <Route path="evaluate">
                <Route index element={<EvaluateIndex />} />
                <Route path="qa" element={<QAEvaluation />} />
                <Route path="agent" element={<AgentEvaluation />} />
                <Route path="rag" element={<RAGEvaluation />} />
                <Route path="arena" element={<ArenaComparison />} />
              </Route>
              <Route path="datasets" element={<Datasets />} />
              <Route path="results" element={<Results />} />
              <Route path="environments" element={<Environments />} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
