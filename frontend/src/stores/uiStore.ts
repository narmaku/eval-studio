import { create } from 'zustand';

type Theme = 'light' | 'dark' | 'system';

interface UIStore {
  sidebarOpen: boolean;
  activePage: string;
  theme: Theme;

  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setActivePage: (page: string) => void;
  setTheme: (theme: Theme) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: false,
  activePage: 'dashboard',
  theme: 'system',

  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActivePage: (activePage) => set({ activePage }),
  setTheme: (theme) => set({ theme }),
}));
