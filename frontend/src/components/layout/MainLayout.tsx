import React, { useState, Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { useResponsive } from '@/hooks/useResponsive';
import { cn } from '@/lib/utils';

// Loading fallback for Suspense
const PageLoader: React.FC = () => (
  <div className="p-6 space-y-4">
    <SkeletonCard className="h-32" />
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <SkeletonCard className="h-48" />
      <SkeletonCard className="h-48" />
      <SkeletonCard className="h-48" />
    </div>
    <SkeletonCard className="h-64" />
  </div>
);

export const MainLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isMobile } = useResponsive();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Error Boundary for the entire layout */}
      <ErrorBoundary>
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

        {/* Main content area */}
        <div
          className={cn(
            'transition-all duration-300 ease-in-out',
            isMobile ? 'ml-0' : 'ml-60'
          )}
        >
          {/* Top Navigation Bar */}
          <TopBar />

          {/* Main Content */}
          <main className="min-h-[calc(100vh-4rem)]">
            <ErrorBoundary>
              <Suspense fallback={<PageLoader />}>
                <Outlet />
              </Suspense>
            </ErrorBoundary>
          </main>
        </div>
      </ErrorBoundary>
    </div>
  );
};

export default MainLayout;
