import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { Toaster } from '@/components/ui/sonner';
import { NotificationPanel } from '@/components/notifications/NotificationPanel';
import { useEvaluationStore } from '@/stores/evaluationStore';

export function AppShell() {
  const resumeTracking = useEvaluationStore((s) => s.resumeTracking);

  useEffect(() => {
    resumeTracking();
  }, [resumeTracking]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1600px] px-6 py-7 pb-16 animate-es-fade">
            <Outlet />
          </div>
        </main>
      </div>
      <Toaster />
      <NotificationPanel />
    </div>
  );
}
