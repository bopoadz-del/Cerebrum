import React from 'react';
import {
  TrendingUp,
  Users,
  FileText,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  CheckCircle,
  AlertCircle,
  MoreHorizontal,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon: React.ElementType;
  trend?: 'up' | 'down' | 'neutral';
  loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  trend = 'neutral',
  loading = false,
}) => {
  if (loading) {
    return <SkeletonCard className="h-32" lines={2} />;
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {title}
          </p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {value}
          </p>
          {change !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              {trend === 'up' ? (
                <ArrowUpRight size={16} className="text-green-500" />
              ) : trend === 'down' ? (
                <ArrowDownRight size={16} className="text-red-500" />
              ) : null}
              <span
                className={cn(
                  'text-sm font-medium',
                  trend === 'up' && 'text-green-600 dark:text-green-400',
                  trend === 'down' && 'text-red-600 dark:text-red-400',
                  trend === 'neutral' && 'text-gray-600 dark:text-gray-400'
                )}
              >
                {change > 0 ? '+' : ''}
                {change}%
              </span>
              {changeLabel && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {changeLabel}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <Icon size={20} className="text-blue-600 dark:text-blue-400" />
        </div>
      </div>
    </div>
  );
};

interface ActivityItem {
  id: string;
  title: string;
  description: string;
  timestamp: Date;
  type: 'success' | 'warning' | 'info' | 'error';
}

const mockActivities: ActivityItem[] = [
  {
    id: '1',
    title: 'Pipeline Completed',
    description: 'Data processing pipeline finished successfully',
    timestamp: new Date(Date.now() - 1000 * 60 * 5),
    type: 'success',
  },
  {
    id: '2',
    title: 'New Document Uploaded',
    description: 'BIM_Model_v2.dwg was uploaded by John Doe',
    timestamp: new Date(Date.now() - 1000 * 60 * 30),
    type: 'info',
  },
  {
    id: '3',
    title: 'Model Training Alert',
    description: 'Training accuracy dropped below threshold',
    timestamp: new Date(Date.now() - 1000 * 60 * 60),
    type: 'warning',
  },
  {
    id: '4',
    title: 'User Login Failed',
    description: 'Multiple failed login attempts detected',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
    type: 'error',
  },
];

const ActivityFeed: React.FC<{ activities: ActivityItem[] }> = ({ activities }) => {
  const getIcon = (type: ActivityItem['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'warning':
        return <AlertCircle size={16} className="text-yellow-500" />;
      case 'error':
        return <AlertCircle size={16} className="text-red-500" />;
      default:
        return <Activity size={16} className="text-blue-500" />;
    }
  };

  const formatTime = (date: Date): string => {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="space-y-4">
      {activities.map((activity) => (
        <div
          key={activity.id}
          className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <div className="mt-0.5">{getIcon(activity.type)}</div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {activity.title}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
              {activity.description}
            </p>
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
            <Clock size={12} />
            {formatTime(activity.timestamp)}
          </span>
        </div>
      ))}
    </div>
  );
};

const Dashboard: React.FC = () => {
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    // Simulate data loading
    const timer = setTimeout(() => setLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Welcome back! Here's what's happening today.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
            New Project
          </button>
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-800">
            <MoreHorizontal size={20} className="text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Projects"
          value="24"
          change={12}
          changeLabel="vs last month"
          icon={FileText}
          trend="up"
          loading={loading}
        />
        <StatCard
          title="Active Users"
          value="1,429"
          change={8}
          changeLabel="vs last month"
          icon={Users}
          trend="up"
          loading={loading}
        />
        <StatCard
          title="Processing Tasks"
          value="87"
          change={-3}
          changeLabel="vs last month"
          icon={Activity}
          trend="down"
          loading={loading}
        />
        <StatCard
          title="Success Rate"
          value="98.5%"
          change={2}
          changeLabel="vs last month"
          icon={TrendingUp}
          trend="up"
          loading={loading}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Feed */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Activity
            </h2>
            <button className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400">
              View all
            </button>
          </div>
          {loading ? (
            <SkeletonList count={4} />
          ) : (
            <ActivityFeed activities={mockActivities} />
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Quick Actions
          </h2>
          <div className="space-y-2">
            {[
              { label: 'Upload Document', icon: FileText },
              { label: 'Create Pipeline', icon: Activity },
              { label: 'Invite Team Member', icon: Users },
              { label: 'View Reports', icon: TrendingUp },
            ].map((action) => (
              <button
                key={action.label}
                className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left"
              >
                <action.icon size={18} className="text-gray-500 dark:text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {action.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Task Completion
          </h2>
          {loading ? (
            <SkeletonChart />
          ) : (
            <div className="h-64 flex items-end justify-around px-4">
              {[65, 45, 80, 55, 90, 70, 85].map((height, i) => (
                <div
                  key={i}
                  className="w-12 bg-blue-500 rounded-t transition-all duration-500 hover:bg-blue-600"
                  style={{ height: `${height}%` }}
                />
              ))}
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Resource Usage
          </h2>
          {loading ? (
            <SkeletonChart />
          ) : (
            <div className="h-64 flex items-center justify-center">
              <div className="relative w-40 h-40">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="12"
                    className="text-gray-200 dark:text-gray-700"
                  />
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="12"
                    strokeLinecap="round"
                    strokeDasharray={`${0.75 * 440} 440`}
                    className="text-blue-500"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold text-gray-900 dark:text-white">
                    75%
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Used
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Import missing components
import { SkeletonList, SkeletonChart } from '@/components/ui/SkeletonCard';

export default Dashboard;
