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
const ResultDetail = lazy(() => import('@/pages/ResultDetail'));
const ResultComparison = lazy(() => import('@/pages/ResultComparison'));
const Sessions = lazy(() => import('@/pages/Sessions'));
const SessionDetail = lazy(() => import('@/pages/SessionDetail'));
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
            <Route path="results">
              <Route
                index
                element={
                  <Suspense fallback={<Loading />}>
                    <Results />
                  </Suspense>
                }
              />
              <Route
                path="compare"
                element={
                  <Suspense fallback={<Loading />}>
                    <ResultComparison />
                  </Suspense>
                }
              />
              <Route
                path=":resultId"
                element={
                  <Suspense fallback={<Loading />}>
                    <ResultDetail />
                  </Suspense>
                }
              />
            </Route>
            <Route path="sessions">
              <Route
                index
                element={
                  <Suspense fallback={<Loading />}>
                    <Sessions />
                  </Suspense>
                }
              />
              <Route
                path=":sessionId"
                element={
                  <Suspense fallback={<Loading />}>
                    <SessionDetail />
                  </Suspense>
                }
              />
            </Route>
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
