import { useState, useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { Bell, User, LayoutDashboard, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { label: 'About us', icon: Info, path: '/about' },
];

/**
 * Synthesise a short notification chime using the Web Audio API.
 * No external audio file required.
 */
function playNotificationChime() {
  try {
    const ctx = new AudioContext();
    const now = ctx.currentTime;

    // Two-note ascending chime
    [523.25, 659.25].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.18, now + i * 0.15);
      gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.15 + 0.5);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now + i * 0.15);
      osc.stop(now + i * 0.15 + 0.5);
    });
  } catch {
    // AudioContext may not be available — fail silently.
  }
}

export function TopHeader() {
  const [bellActive, setBellActive] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  // Listen for scan-completed events fired by ActiveScanPanel
  useEffect(() => {
    const handler = () => {
      setBellActive(true);
      playNotificationChime();
    };
    window.addEventListener('scan-completed', handler);
    return () => window.removeEventListener('scan-completed', handler);
  }, []);

  // Close profile dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <header className="sticky top-0 z-30 h-14 flex items-center gap-6 px-6 border-b border-border bg-bg/80 backdrop-blur supports-[backdrop-filter]:bg-bg/60">
      {/* Brand */}
      <NavLink
        to="/"
        className="font-display text-lg font-bold tracking-tight text-fg shrink-0 hover:text-primary transition-colors"
      >
        TruthLens
      </NavLink>

      {/* Navigation links */}
      <nav className="flex items-center gap-1">
        {NAV_ITEMS.map(({ label, icon: Icon, path }) => (
          <NavLink
            key={label}
            to={path}
            end={path === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-primary/15 text-fg font-medium'
                  : 'text-muted hover:bg-card hover:text-fg',
              )
            }
          >
            <Icon className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Right-side icons */}
      <div className="ml-auto flex items-center gap-2">
        {/* Notification bell */}
        <button
          type="button"
          onClick={() => setBellActive(false)}
          className={cn(
            'relative size-9 grid place-items-center rounded-md text-muted hover:text-fg hover:bg-card transition-colors',
            bellActive && 'animate-bell-glow',
          )}
          aria-label="Notifications"
          title={bellActive ? 'Scan complete — click to dismiss' : 'No new notifications'}
        >
          <Bell className="size-4" />
          {bellActive && (
            <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-primary" />
          )}
        </button>

        {/* Profile with hover dropdown */}
        <div
          ref={profileRef}
          className="relative"
          onMouseEnter={() => setProfileOpen(true)}
          onMouseLeave={() => setProfileOpen(false)}
        >
          <button
            type="button"
            className="size-9 grid place-items-center rounded-full bg-card text-fg hover:ring-2 hover:ring-primary/40 transition-all"
            aria-label="Account"
          >
            <User className="size-4" />
          </button>

          {/* Dropdown */}
          {profileOpen && (
            <div className="absolute right-0 top-full mt-1 w-44 rounded-md border border-border bg-card shadow-xl py-1 z-50 animate-[fadeIn_150ms_ease-out]">
              <button
                type="button"
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-muted hover:text-fg hover:bg-bg-elevated transition-colors text-left"
              >
                <User className="size-4" />
                User Profile
              </button>
              <button
                type="button"
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-muted hover:text-fg hover:bg-bg-elevated transition-colors text-left"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
                Settings
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
