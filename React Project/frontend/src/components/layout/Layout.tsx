import type { ReactNode } from 'react';
import { TopHeader } from './TopHeader';
import { MainContent } from './MainContent';
import { FloatingChatWidget } from './FloatingChatWidget';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-bg text-fg relative overflow-hidden">
      {/* Volumetric background lighting & particles */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        {/* Purple glow — top left */}
        <div className="absolute -top-[20%] -left-[10%] w-[70vw] h-[70vw] rounded-full bg-[radial-gradient(circle,var(--glow-1)_0%,transparent_60%)] blur-3xl opacity-80" />
        {/* Hot pink / magenta glow — bottom right */}
        <div className="absolute -bottom-[20%] -right-[10%] w-[60vw] h-[60vw] rounded-full bg-[radial-gradient(circle,var(--glow-2)_0%,transparent_60%)] blur-3xl opacity-70" />
        {/* Electric cyan glow — bottom left */}
        <div className="absolute -bottom-[10%] -left-[5%] w-[40vw] h-[40vw] rounded-full bg-[radial-gradient(circle,var(--glow-3)_0%,transparent_60%)] blur-3xl opacity-60" />
        {/* Soft violet glow — center right */}
        <div className="absolute top-[30%] -right-[5%] w-[35vw] h-[35vw] rounded-full bg-[radial-gradient(circle,var(--glow-4)_0%,transparent_60%)] blur-3xl opacity-55" />

        {/* Multicolor floating particles */}
        <div className="absolute inset-0 opacity-40">
          {[...Array(18)].map((_, i) => {
            const size = Math.random() * 4 + 2;
            const left = Math.random() * 100;
            const duration = Math.random() * 15 + 15;
            const delay = Math.random() * -20;
            // Alternate between purple, pink, and cyan particles
            const colorClass = i % 3 === 0
              ? 'bg-pink-400/50'
              : i % 3 === 1
              ? 'bg-cyan-400/40'
              : 'bg-purple-400/45';
            return (
              <div
                key={i}
                className={`bg-particle absolute bottom-0 rounded-full ${colorClass}`}
                style={{
                  width: `${size}px`,
                  height: `${size}px`,
                  left: `${left}%`,
                  animationDuration: `${duration}s`,
                  animationDelay: `${delay}s`,
                  filter: 'blur(0.5px)',
                }}
              />
            );
          })}
        </div>
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        <TopHeader />
        <MainContent>{children}</MainContent>
        <FloatingChatWidget />
      </div>
    </div>
  );
}
