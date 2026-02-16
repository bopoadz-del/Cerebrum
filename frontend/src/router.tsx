import React, { Suspense, lazy } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { MainLayout } from '@/components/layout/MainLayout';
import { PageSkeleton } from '@/components/ui/SkeletonCard';

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Registry = lazy(() => import('@/pages/Registry'));
const Learning = lazy(() => import('@/pages/Learning'));
const Sandbox = lazy(() => import('@/pages/Sandbox'));
const Audit = lazy(() => import('@/pages/Audit'));
const Pipelines = lazy(() => import('@/pages/Pipelines'));
const Settings = lazy(() => import('@/pages/Settings'));
const Tasks = lazy(() => import('@/pages/Tasks'));
const BIMViewer = lazy(() => import('@/pages/BIMViewer'));
const ActionItems = lazy(() => import('@/pages/ActionItems'));
const Documents = lazy(() => import('@/pages/Documents'));
const Chat = lazy(() => import('@/pages/Chat'));
const Login = lazy(() => import('@/pages/Login'));
const AdminPanel = lazy(() => import('@/pages/AdminPanel'));
const Economics = lazy(() => import('@/pages/Economics'));
const MLTinker = lazy(() => import('@/pages/MLTinker'));
const EdgeDevices = lazy(() => import('@/pages/EdgeDevices'));
const FieldData = lazy(() => import('@/pages/FieldData'));
const VDC = lazy(() => import('@/pages/VDC'));
const Quality = lazy(() => import('@/pages/Quality'));
const Subcontractor = lazy(() => import('@/pages/Subcontractor'));

// Loading fallback
const PageLoader = () => <PageSkeleton />;

// Protected route wrapper
interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  // TODO: Implement actual auth check
  const isAuthenticated = true; // Replace with actual auth check

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Route wrapper with error boundary and suspense
const RouteWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ErrorBoundary>
    <Suspense fallback={<PageLoader />}>{children}</Suspense>
  </ErrorBoundary>
);

// Define routes
export const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <RouteWrapper>
        <Login />
      </RouteWrapper>
    ),
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: (
          <RouteWrapper>
            <Dashboard />
          </RouteWrapper>
        ),
      },
      {
        path: 'registry',
        element: (
          <RouteWrapper>
            <Registry />
          </RouteWrapper>
        ),
      },
      {
        path: 'learning',
        element: (
          <RouteWrapper>
            <Learning />
          </RouteWrapper>
        ),
      },
      {
        path: 'sandbox',
        element: (
          <RouteWrapper>
            <Sandbox />
          </RouteWrapper>
        ),
      },
      {
        path: 'audit',
        element: (
          <RouteWrapper>
            <Audit />
          </RouteWrapper>
        ),
      },
      {
        path: 'pipelines',
        element: (
          <RouteWrapper>
            <Pipelines />
          </RouteWrapper>
        ),
      },
      {
        path: 'settings',
        element: (
          <RouteWrapper>
            <Settings />
          </RouteWrapper>
        ),
      },
      {
        path: 'tasks',
        element: (
          <RouteWrapper>
            <Tasks />
          </RouteWrapper>
        ),
      },
      {
        path: 'bim',
        element: (
          <RouteWrapper>
            <BIMViewer />
          </RouteWrapper>
        ),
      },
      {
        path: 'action-items',
        element: (
          <RouteWrapper>
            <ActionItems />
          </RouteWrapper>
        ),
      },
      {
        path: 'documents',
        element: (
          <RouteWrapper>
            <Documents />
          </RouteWrapper>
        ),
      },
      {
        path: 'chat',
        element: (
          <RouteWrapper>
            <Chat />
          </RouteWrapper>
        ),
      },
      {
        path: 'admin',
        element: (
          <ProtectedRoute requiredRole="admin">
            <RouteWrapper>
              <AdminPanel />
            </RouteWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'economics',
        element: (
          <RouteWrapper>
            <Economics />
          </RouteWrapper>
        ),
      },
      {
        path: 'ml-tinker',
        element: (
          <RouteWrapper>
            <MLTinker />
          </RouteWrapper>
        ),
      },
      {
        path: 'edge-devices',
        element: (
          <RouteWrapper>
            <EdgeDevices />
          </RouteWrapper>
        ),
      },
      {
        path: 'field-data',
        element: (
          <RouteWrapper>
            <FieldData />
          </RouteWrapper>
        ),
      },
      {
        path: 'vdc',
        element: (
          <RouteWrapper>
            <VDC />
          </RouteWrapper>
        ),
      },
      {
        path: 'quality',
        element: (
          <RouteWrapper>
            <Quality />
          </RouteWrapper>
        ),
      },
      {
        path: 'subcontractor',
        element: (
          <RouteWrapper>
            <Subcontractor />
          </RouteWrapper>
        ),
      },
      {
        path: '*',
        element: (
          <div className="flex flex-col items-center justify-center h-full p-8">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">404</h1>
            <p className="text-gray-500 dark:text-gray-400 mb-6">Page not found</p>
            <a
              href="/"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              Go Home
            </a>
          </div>
        ),
      },
    ],
  },
]);

export default router;
