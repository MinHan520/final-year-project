import { useState } from 'react';
import { LayoutDashboard, Settings, LifeBuoy, Menu } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface NavItem {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  path: string;
}

const NAV: NavItem[] = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
];

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "hidden lg:flex shrink-0 flex-col border-r border-border bg-bg-elevated transition-all duration-300",
        isCollapsed ? "w-[72px]" : "w-60"
      )}
    >
      <div className={cn("px-4 pt-6 pb-4 border-b border-border flex items-center", isCollapsed ? "justify-center" : "justify-between")}>
        {!isCollapsed && (
          <div className="font-display text-xl font-bold tracking-tight text-fg leading-tight">
            TruthLens
          </div>
        )}
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-md text-muted hover:text-fg hover:bg-card transition-colors"
          aria-label="Toggle Sidebar"
        >
          <Menu className="size-5" />
        </button>
      </div>

      <nav className={cn("flex-1 py-4 space-y-1 overflow-y-auto", isCollapsed ? "px-3" : "px-2")}>
        {NAV.map(({ label, icon: Icon, path }) => (
          <NavLink
            key={label}
            to={path}
            end={path === '/'}
            title={isCollapsed ? label : undefined}
            className={({ isActive }) =>
              cn(
                'w-full flex items-center rounded-md text-sm transition-colors text-left',
                isCollapsed ? 'justify-center py-2.5' : 'gap-3 px-3 py-2',
                isActive
                  ? 'bg-primary/15 text-fg ring-1 ring-primary/30'
                  : 'text-muted hover:bg-card hover:text-fg',
              )
            }
          >
            <Icon className="size-5 shrink-0" />
            {!isCollapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className={cn("py-4 border-t border-border flex flex-col gap-3", isCollapsed ? "px-3 items-center" : "px-4")}>
        <div className={cn("flex items-center text-xs text-muted", isCollapsed ? "justify-center py-2" : "gap-2")}>
          <span className="size-2 rounded-full bg-success animate-pulse shrink-0" />
          {!isCollapsed && <span>Nodes online · 1 / 4</span>}
        </div>
        <div className={cn("flex text-muted", isCollapsed ? "flex-col gap-3" : "items-center gap-4")}>
          <button type="button" className={cn("flex items-center hover:text-fg text-xs", isCollapsed ? "justify-center p-1.5" : "gap-2")} title={isCollapsed ? "Settings" : undefined}>
            <Settings className="size-4" />
            {!isCollapsed && <span>Settings</span>}
          </button>
          <button type="button" className={cn("flex items-center hover:text-fg text-xs", isCollapsed ? "justify-center p-1.5" : "gap-2")} title={isCollapsed ? "Support" : undefined}>
            <LifeBuoy className="size-4" />
            {!isCollapsed && <span>Support</span>}
          </button>
        </div>
      </div>
    </aside>
  );
}
