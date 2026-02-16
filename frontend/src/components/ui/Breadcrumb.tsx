import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BreadcrumbItem {
  label: string;
  path: string;
  isLast?: boolean;
}

// Route label mappings
const routeLabels: Record<string, string> = {
  '': 'Home',
  'registry': 'Registry',
  'learning': 'Learning',
  'sandbox': 'Sandbox',
  'audit': 'Audit Logs',
  'pipelines': 'Pipelines',
  'settings': 'Settings',
  'tasks': 'Tasks',
  'bim': 'BIM Viewer',
  'action-items': 'Action Items',
  'documents': 'Documents',
  'chat': 'Chat',
  'admin': 'Admin Panel',
  'economics': 'Economics',
  'ml-tinker': 'ML Tinker',
  'edge-devices': 'Edge Devices',
  'field-data': 'Field Data',
  'vdc': 'VDC',
  'quality': 'Quality',
  'subcontractor': 'Subcontractor Portal',
  'profile': 'Profile',
  'notifications': 'Notifications',
};

interface BreadcrumbProps {
  className?: string;
  separator?: React.ReactNode;
  showHome?: boolean;
  customLabels?: Record<string, string>;
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({
  className,
  separator = <ChevronRight size={16} />,
  showHome = true,
  customLabels = {},
}) => {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);

  // Merge custom labels with default labels
  const labels = { ...routeLabels, ...customLabels };

  // Build breadcrumb items
  const items: BreadcrumbItem[] = [];

  if (showHome) {
    items.push({
      label: 'Home',
      path: '/',
      isLast: pathnames.length === 0,
    });
  }

  let currentPath = '';
  pathnames.forEach((name, index) => {
    currentPath += `/${name}`;
    items.push({
      label: labels[name] || name.charAt(0).toUpperCase() + name.slice(1),
      path: currentPath,
      isLast: index === pathnames.length - 1,
    });
  });

  // Don't render if only home
  if (items.length <= 1 && showHome) {
    return null;
  }

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn('flex items-center text-sm', className)}
    >
      <ol className="flex items-center flex-wrap gap-1">
        {items.map((item, index) => (
          <li key={item.path} className="flex items-center">
            {index > 0 && (
              <span className="mx-2 text-gray-400 dark:text-gray-500">
                {separator}
              </span>
            )}
            {item.isLast ? (
              <span
                className="font-medium text-gray-900 dark:text-white"
                aria-current="page"
              >
                {item.label}
              </span>
            ) : (
              <Link
                to={item.path}
                className={cn(
                  'text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors',
                  index === 0 && 'flex items-center gap-1'
                )}
              >
                {index === 0 && showHome ? (
                  <>
                    <Home size={16} />
                    <span className="sr-only">{item.label}</span>
                  </>
                ) : (
                  item.label
                )}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
};

// Compact breadcrumb for mobile
export const CompactBreadcrumb: React.FC<Omit<BreadcrumbProps, 'separator'>> = ({
  className,
  showHome = true,
  customLabels = {},
}) => {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);
  const labels = { ...routeLabels, ...customLabels };

  if (pathnames.length === 0) return null;

  const currentLabel = labels[pathnames[pathnames.length - 1]] ||
    pathnames[pathnames.length - 1].charAt(0).toUpperCase() + pathnames[pathnames.length - 1].slice(1);

  const parentPath = '/' + pathnames.slice(0, -1).join('/');

  return (
    <nav className={cn('flex items-center text-sm', className)}>
      <Link
        to={parentPath || '/'}
        className="flex items-center gap-1 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
      >
        <ChevronRight size={16} className="rotate-180" />
        <span>Back</span>
      </Link>
      <span className="mx-2 text-gray-300 dark:text-gray-600">|</span>
      <span className="font-medium text-gray-900 dark:text-white truncate max-w-[200px]">
        {currentLabel}
      </span>
    </nav>
  );
};

export default Breadcrumb;
