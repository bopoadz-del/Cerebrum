import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Box,
  BookOpen,
  FlaskConical,
  FileText,
  GitBranch,
  Settings,
  ListTodo,
  Building2,
  ClipboardCheck,
  MessageSquare,
  Users,
  Wallet,
  Cpu,
  Monitor,
  Database,
  Layers,
  ShieldCheck,
  HardHat,
  ChevronLeft,
  ChevronRight,
  Menu,
  X
} from 'lucide-react';
import { useResponsive } from '@/hooks/useResponsive';
import { cn } from '@/lib/utils';
import { GoogleDriveConnectButton } from '@/components/GoogleDriveConnectButton';

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
  badge?: number;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/registry', label: 'Registry', icon: Box },
  { path: '/learning', label: 'Learning', icon: BookOpen },
  { path: '/sandbox', label: 'Sandbox', icon: FlaskConical },
  { path: '/pipelines', label: 'Pipelines', icon: GitBranch },
  { path: '/tasks', label: 'Tasks', icon: ListTodo },
  { path: '/bim', label: 'BIM Viewer', icon: Building2 },
  { path: '/action-items', label: 'Action Items', icon: ClipboardCheck },
  { path: '/documents', label: 'Documents', icon: FileText },
  { path: '/chat', label: 'Chat', icon: MessageSquare, badge: 3 },
  { path: '/admin', label: 'Admin Panel', icon: Users },
  { path: '/economics', label: 'Economics', icon: Wallet },
  { path: '/ml-tinker', label: 'ML Tinker', icon: Cpu },
  { path: '/edge-devices', label: 'Edge Devices', icon: Monitor },
  { path: '/field-data', label: 'Field Data', icon: Database },
  { path: '/vdc', label: 'VDC', icon: Layers },
  { path: '/quality', label: 'Quality', icon: ShieldCheck },
  { path: '/subcontractor', label: 'Subcontractor', icon: HardHat },
  { path: '/audit', label: 'Audit', icon: FileText },
  { path: '/settings', label: 'Settings', icon: Settings },
];

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onToggle }) => {
  const { isMobile, isTablet } = useResponsive();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  // Auto-collapse on tablet
  useEffect(() => {
    if (isTablet && !isMobile) {
      setCollapsed(true);
    } else if (!isTablet && !isMobile) {
      setCollapsed(false);
    }
  }, [isTablet, isMobile]);

  // Close mobile sidebar on route change
  useEffect(() => {
    if (isMobile && isOpen) {
      onToggle();
    }
  }, [location.pathname, isMobile]);

  const sidebarWidth = collapsed ? 'w-16' : 'w-60';

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 transition-opacity"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 z-50 transition-all duration-300 ease-in-out',
          sidebarWidth,
          isMobile && (isOpen ? 'translate-x-0' : '-translate-x-full'),
          !isMobile && sidebarWidth
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-800">
          {!collapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">C</span>
              </div>
              <span className="font-semibold text-gray-900 dark:text-white">Cerebrum</span>
            </div>
          )}
          {collapsed && (
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mx-auto">
              <span className="text-white font-bold text-sm">C</span>
            </div>
          )}
          {!isMobile && (
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400"
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            </button>
          )}
          {isMobile && (
            <button
              onClick={onToggle}
              className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400"
              aria-label="Close sidebar"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1 h-[calc(100vh-4rem)]">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors relative group',
                  isActive
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200',
                  collapsed && 'justify-center px-2'
                )}
                title={collapsed ? item.label : undefined}
              >
                <Icon size={20} className="flex-shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
                {!collapsed && item.badge && (
                  <span className="ml-auto bg-red-500 text-white text-xs font-medium px-2 py-0.5 rounded-full">
                    {item.badge}
                  </span>
                )}
                {collapsed && item.badge && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-medium flex items-center justify-center rounded-full">
                    {item.badge}
                  </span>
                )}
                {/* Tooltip for collapsed state */}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all whitespace-nowrap z-50">
                    {item.label}
                  </div>
                )}
              </NavLink>
            );
          })}
          
          {/* Divider */}
          <div className="my-4 border-t border-gray-200 dark:border-gray-800" />
          
          {/* Google Drive Connect */}
          {!collapsed && (
            <div className="px-3 py-2">
              <p className="text-xs text-gray-500 dark:text-gray-500 mb-2">Integrations</p>
              <GoogleDriveConnectButton variant="menu-item" />
            </div>
          )}
          {collapsed && (
            <div className="flex justify-center py-2">
              <GoogleDriveConnectButton variant="menu-item" />
            </div>
          )}
        </nav>
      </aside>

      {/* Mobile toggle button */}
      {isMobile && !isOpen && (
        <button
          onClick={onToggle}
          className="fixed top-4 left-4 z-40 p-2 bg-white dark:bg-gray-900 rounded-lg shadow-md border border-gray-200 dark:border-gray-800"
          aria-label="Open sidebar"
        >
          <Menu size={20} />
        </button>
      )}
    </>
  );
};

export default Sidebar;
