import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Brain, AlertCircle, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SmartContextToggleProps {
  sessionToken?: string;
  onToggle?: (enabled: boolean) => void;
}

export function SmartContextToggle({ onToggle }: SmartContextToggleProps) {
  const [enabled, setEnabled] = useState(false);
  const [capacity, setCapacity] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  // Simulate capacity monitoring
  useEffect(() => {
    if (!enabled) return;
    
    const interval = setInterval(() => {
      // Simulate capacity increasing with messages
      setCapacity((prev) => {
        const newCapacity = Math.min(prev + Math.random() * 5, 100);
        return newCapacity;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [enabled]);

  // Reset capacity when disabled
  useEffect(() => {
    if (!enabled) {
      setCapacity(0);
    }
  }, [enabled]);

  const handleToggle = async () => {
    const nextState = !enabled;
    setIsLoading(true);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 300));
    
    setEnabled(nextState);
    onToggle?.(nextState);
    setIsLoading(false);
  };

  const getCapacityColor = () => {
    if (capacity < 50) return 'bg-emerald-500';
    if (capacity < 75) return 'bg-amber-500';
    if (capacity < 90) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getCapacityStatus = () => {
    if (capacity < 50) return 'Healthy';
    if (capacity < 75) return 'Moderate';
    if (capacity < 90) return 'High';
    return 'Critical - Handoff Soon';
  };

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 mb-4">
      {/* Toggle Row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center transition-colors',
              enabled ? 'bg-indigo-100' : 'bg-gray-100'
            )}
          >
            <Brain
              className={cn(
                'w-5 h-5 transition-colors',
                enabled ? 'text-indigo-600' : 'text-gray-400'
              )}
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'font-medium transition-colors',
                  enabled ? 'text-gray-900' : 'text-gray-600'
                )}
              >
                Smart Context
              </span>
              <span
                className={cn(
                  'text-xs px-2 py-0.5 rounded-full font-medium transition-colors',
                  enabled
                    ? 'bg-red-100 text-red-700'
                    : 'bg-gray-100 text-gray-500'
                )}
              >
                {enabled ? 'AUTO-HANDOFF ON' : 'Manual'}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              Auto-brief + handoff at 90% capacity
            </p>
          </div>
        </div>

        {/* Toggle Switch */}
        <button
          onClick={handleToggle}
          disabled={isLoading}
          className={cn(
            'relative w-14 h-7 rounded-full transition-colors duration-300',
            enabled ? 'bg-indigo-600' : 'bg-gray-300'
          )}
        >
          <motion.div
            initial={false}
            animate={{ x: enabled ? 28 : 2 }}
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            className="absolute top-1 w-5 h-5 bg-white rounded-full shadow-sm"
          />
        </button>
      </div>

      {/* Capacity Monitor (only when enabled) */}
      {enabled && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-4 pt-4 border-t border-gray-200"
        >
          {/* Capacity Bar */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">Context Capacity</span>
            <span
              className={cn(
                'text-sm font-medium',
                capacity >= 90 ? 'text-red-600' : 'text-gray-700'
              )}
            >
              {Math.round(capacity)}%
            </span>
          </div>

          {/* Progress Bar */}
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${capacity}%` }}
              transition={{ duration: 0.5 }}
              className={cn('h-full rounded-full transition-colors', getCapacityColor())}
            />
          </div>

          {/* Status */}
          <div className="flex items-center justify-between mt-2">
            <span className={cn('text-xs', capacity >= 90 ? 'text-red-600' : 'text-gray-500')}>
              {getCapacityStatus()}
            </span>
            {capacity >= 90 && (
              <div className="flex items-center gap-1 text-xs text-red-600">
                <AlertCircle className="w-3 h-3" />
                Handoff imminent
              </div>
            )}
          </div>

          {/* Handoff Warning */}
          {capacity >= 95 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg"
            >
              <div className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-red-500 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-700">
                    Context Limit Reached
                  </p>
                  <p className="text-xs text-red-600 mt-0.5">
                    A new session will be created automatically to maintain performance.
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>
      )}
    </div>
  );
}
