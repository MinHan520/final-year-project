import type { ReactNode } from 'react';
import { TopHeader } from './TopHeader';
import { MainContent } from './MainContent';
import { FloatingChatWidget } from './FloatingChatWidget';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-bg text-fg">
      <TopHeader />
      <MainContent>{children}</MainContent>
      <FloatingChatWidget />
    </div>
  );
}
