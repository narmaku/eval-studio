import { Outlet } from 'react-router-dom';
import { TopNav } from './TopNav';
import { Toaster } from '@/components/ui/sonner';

export function AppShell() {
  return (
    <div className="min-h-screen bg-background">
      <TopNav />
      <main className="container mx-auto py-6 px-4">
        <Outlet />
      </main>
      <Toaster />
    </div>
  );
}
