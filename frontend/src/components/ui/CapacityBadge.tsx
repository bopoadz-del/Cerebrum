import React from 'react';
import { useCapacity } from '@/hooks/useCapacity';
import { cn } from '@/lib/utils';
import { Loader2, AlertTriangle, Database } from 'lucide-react';

interface CapacityBadgeProps {
  className?: string;
  showLabel?: boolean;
  showPercentage?: boolean;
  compact?: boolean;
}

export const CapacityBadge: React.FC<CapacityBadgeProps> = ({
  className,
  showLabel = false,
  showPercentage = true,
  compact = false,
}) => {
  const { capacity, isLoading, error } = useCapacity({
    interval: 5000,
    enabled: true,
  });

  const getStatusColor = () => {
    switch (capacity.status) {
      case 'healthy':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 border-green-300 dark:border-green-700';
      case 'warning':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400 border-yellow-300 dark:border-yellow-700';
      case 'critical':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400 border-red-300 dark:border-red-700';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400 border-gray-300 dark:border-gray-700';
    }
  };

  const getStatusIcon = () => {
    if (isLoading) {
      return <Loader2 size={compact ? 14 : 16} className="animate-spin" />;
    }
    if (error) {
      return <AlertTriangle size={compact ? 14 : 16} />;
    }
    return <Database size={compact ? 14 : 16} />;
  };

  const getProgressBarColor = () => {
    switch (capacity.status) {
      case 'healthy':
        return 'bg-green-500';
      case 'warning':
        return 'bg-yellow-500';
      case 'critical':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs font-medium',
          getStatusColor(),
          className
        )}
        title={`Capacity: ${capacity.current}/${capacity.limit} (${capacity.percentage}%)`}
      >
        {getStatusIcon()}
        {showPercentage && (
          <span>{error ? 'Error' : `${capacity.percentage}%`}</span>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg border',
        getStatusColor(),
        className
      )}
    >
      {getStatusIcon()}
      <div className="flex flex-col min-w-[100px]">
        {showLabel && (
          <span className="text-xs opacity-75">Capacity</span>
        )}
        <div className="flex items-center gap-2">
          {showPercentage && (
            <span className="text-sm font-semibold">
              {error ? 'Error' : `${capacity.percentage}%`}
            </span>
          )}
          <span className="text-xs opacity-75">
            {capacity.current}/{capacity.limit}
          </span>
        </div>
        {/* Progress bar */}
        <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full mt-1 overflow-hidden">
          <div
            className={cn('h-full transition-all duration-500', getProgressBarColor())}
            style={{ width: `${Math.min(capacity.percentage, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
};

// Detailed capacity panel
export const CapacityPanel: React.FC<{ className?: string }> = ({ className }) => {
  const { capacity, isLoading, error, refresh } = useCapacity({
    interval: 5000,
    enabled: true,
  });

  const getStatusText = () => {
    switch (capacity.status) {
      case 'healthy':
        return 'System operating normally';
      case 'warning':
        return 'Approaching capacity limit';
      case 'critical':
        return 'Critical capacity reached';
      default:
        return 'Unknown status';
    }
  };

  const getStatusIcon = () => {
    switch (capacity.status) {
      case 'healthy':
        return '✓';
      case 'warning':
        return '⚠';
      case 'critical':
        return '✕';
      default:
        return '?';
    }
  };

  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4',
        className
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          System Capacity
        </h3>
        <button
          onClick={refresh}
          disabled={isLoading}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          title="Refresh"
        >
          <Loader2
            size={18}
            className={cn('text-gray-500', isLoading && 'animate-spin')}
          />
        </button>
      </div>

      {error ? (
        <div className="p-4 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-700 dark:text-red-400">
            Failed to load capacity data
          </p>
          <button
            onClick={refresh}
            className="mt-2 text-sm text-red-600 hover:text-red-700 dark:text-red-400 underline"
          >
            Try again
          </button>
        </div>
      ) : (
        <>
          {/* Main capacity display */}
          <div className="flex items-center gap-4 mb-4">
            <div
              className={cn(
                'w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold',
                capacity.status === 'healthy' && 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400',
                capacity.status === 'warning' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400',
                capacity.status === 'critical' && 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400'
              )}
            >
              {getStatusIcon()}
            </div>
            <div>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {capacity.percentage}%
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {getStatusText()}
              </p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600 dark:text-gray-400">
                {capacity.current} used
              </span>
              <span className="text-gray-600 dark:text-gray-400">
                {capacity.limit} total
              </span>
            </div>
            <div className="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full transition-all duration-500 rounded-full',
                  capacity.status === 'healthy' && 'bg-green-500',
                  capacity.status === 'warning' && 'bg-yellow-500',
                  capacity.status === 'critical' && 'bg-red-500'
                )}
                style={{ width: `${Math.min(capacity.percentage, 100)}%` }}
              />
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                Available
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {capacity.limit - capacity.current}
              </p>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                Last Updated
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {capacity.lastUpdated.toLocaleTimeString()}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default CapacityBadge;
