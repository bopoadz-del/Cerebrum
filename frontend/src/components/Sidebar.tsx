import { motion } from 'framer-motion';
import { NavLink, useLocation } from 'react-router-dom';
import {
  MessageSquare,
  Calendar,
  Mic,
  Archive,
  Box,
  FileText,
  File,
  Building2,
  AlertTriangle,
  TrendingUp,
  FunctionSquare,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Brain,
  LayoutDashboard,
} from 'lucide-react';
import { useSidebar } from '@/hooks/useSidebar';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface NavItemProps {
  to: string;
  icon: React.ElementType;
  label: string;
  collapsed: boolean;
}

const NavItem = ({ to, icon: Icon, label, collapsed }: NavItemProps) => {
  const location = useLocation();
  const isActive = location.pathname === to;

  const content = (
    <NavLink
      to={to}
      className={cn(
        'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group',
        'hover:bg-gray-100',
        isActive && 'bg-gray-100 nav-active'
      )}
    >
      <Icon
        className={cn(
          'w-5 h-5 flex-shrink-0 transition-colors',
          isActive ? 'text-indigo-600' : 'text-gray-500 group-hover:text-gray-700'
        )}
      />
      {!collapsed && (
        <span
          className={cn(
            'text-sm font-medium transition-colors whitespace-nowrap',
            isActive ? 'text-gray-900' : 'text-gray-600 group-hover:text-gray-900'
          )}
        >
          {label}
        </span>
      )}
    </NavLink>
  );;

  if (collapsed) {
    return (
      <Tooltip delayDuration={100}>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right" className="ml-2">
          {label}
        </TooltipContent>
      </Tooltip>
    );
  }

  return content;
};

const NavSection = ({ title, collapsed, children }: { title: string; collapsed: boolean; children: React.ReactNode }) => (
  <div className="mb-4">
    {!collapsed && (
      <h3 className="px-3 mb-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
        {title}
      </h3>
    )}
    <div className="space-y-0.5">{children}</div>
  </div>
);

export function Sidebar() {
  const { collapsed, toggle } = useSidebar();

  return (
    <TooltipProvider>
      <motion.aside
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
        className={cn(
          'fixed left-0 top-0 h-screen bg-white border-r border-gray-200 z-50 flex flex-col',
          'transition-all duration-300 ease-out'
        )}
        style={{ width: collapsed ? 72 : 260 }}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
              <Brain className="w-5 h-5 text-white" />
            </div>
            {!collapsed && (
              <span className="font-semibold text-lg text-gray-900 whitespace-nowrap">
                Reasoner
              </span>
            )}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto py-4 px-2">
          <NavSection title="Main" collapsed={collapsed}>
            <NavItem to="/" icon={MessageSquare} label="Chat" collapsed={collapsed} />
            <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" collapsed={collapsed} />
          </NavSection>

          <NavSection title="Analysis" collapsed={collapsed}>
            <NavItem to="/schedule" icon={Calendar} label="Schedule" collapsed={collapsed} />
            <NavItem to="/audio" icon={Mic} label="Audio" collapsed={collapsed} />
            <NavItem to="/archive" icon={Archive} label="Archive" collapsed={collapsed} />
            <NavItem to="/cad" icon={Box} label="CAD" collapsed={collapsed} />
            <NavItem to="/pdf" icon={FileText} label="PDF" collapsed={collapsed} />
            <NavItem to="/document" icon={File} label="Document" collapsed={collapsed} />
            <NavItem to="/ifc" icon={Building2} label="IFC" collapsed={collapsed} />
            <NavItem to="/anomaly" icon={AlertTriangle} label="Anomaly" collapsed={collapsed} />
            <NavItem to="/forecast" icon={TrendingUp} label="Forecast" collapsed={collapsed} />
          </NavSection>

          <NavSection title="Tools" collapsed={collapsed}>
            <NavItem to="/formulas" icon={FunctionSquare} label="Formulas" collapsed={collapsed} />
          </NavSection>

          <NavSection title="System" collapsed={collapsed}>
            <NavItem to="/settings" icon={Settings} label="Settings" collapsed={collapsed} />
            <NavItem to="/help" icon={HelpCircle} label="Help" collapsed={collapsed} />
          </NavSection>
        </div>

        {/* Collapse Toggle */}
        <div className="p-3 border-t border-gray-100">
          <button
            onClick={toggle}
            className={cn(
              'w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg',
              'text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-all duration-200'
            )}
          >
            {collapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <>
                <ChevronLeft className="w-5 h-5" />
                <span className="text-sm font-medium">Collapse</span>
              </>
            )}
          </button>
        </div>
      </motion.aside>
    </TooltipProvider>
  );
}
