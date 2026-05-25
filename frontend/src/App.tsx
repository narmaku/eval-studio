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

export function Loading() {
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
        <Routes>
          <Route element={<AppShell />}>
            <Route
              index
              element={
                <Suspense fallback={<Loading />}>
                  <Dashboard />
                </Suspense>
              }
            />
            <Route path="evaluate">
              <Route
                index
                element={
                  <Suspense fallback={<Loading />}>
                    <EvaluateIndex />
                  </Suspense>
                }
              />
              <Route
                path="qa"
                element={
                  <Suspense fallback={<Loading />}>
                    <QAEvaluation />
                  </Suspense>
                }
              />
              <Route
                path="agent"
                element={
                  <Suspense fallback={<Loading />}>
                    <AgentEvaluation />
                  </Suspense>
                }
              />
              <Route
                path="rag"
                element={
                  <Suspense fallback={<Loading />}>
                    <RAGEvaluation />
                  </Suspense>
                }
              />
              <Route
                path="arena"
                element={
                  <Suspense fallback={<Loading />}>
                    <ArenaComparison />
                  </Suspense>
                }
              />
            </Route>
            <Route
              path="datasets"
              element={
                <Suspense fallback={<Loading />}>
                  <Datasets />
                </Suspense>
              }
            />
            <Route
              path="results"
              element={
                <Suspense fallback={<Loading />}>
                  <Results />
                </Suspense>
              }
            />
            <Route
              path="environments"
              element={
                <Suspense fallback={<Loading />}>
                  <Environments />
                </Suspense>
              }
            />
            <Route
              path="settings"
              element={
                <Suspense fallback={<Loading />}>
                  <Settings />
                </Suspense>
              }
            />
            <Route
              path="*"
              element={
                <Suspense fallback={<Loading />}>
                  <NotFound />
                </Suspense>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
