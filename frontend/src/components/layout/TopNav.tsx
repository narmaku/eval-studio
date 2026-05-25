import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/evaluate', label: 'Evaluate' },
  { to: '/datasets', label: 'Datasets' },
  { to: '/results', label: 'Results' },
  { to: '/environments', label: 'Environments' },
];

export function TopNav() {
  return (
    <header className="border-b bg-background">
      <div className="flex h-14 items-center px-6">
        <span className="text-lg font-semibold mr-8">eval-studio</span>
        <nav className="flex items-center gap-6">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `text-sm font-medium transition-colors hover:text-primary ${
                  isActive ? 'text-foreground' : 'text-muted-foreground'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-4">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `text-sm font-medium transition-colors hover:text-primary ${
                isActive ? 'text-foreground' : 'text-muted-foreground'
              }`
            }
          >
            Settings
          </NavLink>
        </div>
      </div>
    </header>
  );
}
