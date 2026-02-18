import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCountUp } from '@/hooks/useCountUp';

interface StatCardProps {
  title: string;
  value: number;
  trend: number;
  icon: LucideIcon;
  iconColor?: string;
  delay?: number;
}

export function StatCard({
  title,
  value,
  trend,
  icon: Icon,
  iconColor = 'indigo',
  delay = 0,
}: StatCardProps) {
  const animatedValue = useCountUp({ end: value, duration: 2000, delay });
  const isPositive = trend >= 0;

  const colorClasses: Record<string, string> = {
    indigo: 'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    rose: 'bg-rose-50 text-rose-600',
    blue: 'bg-blue-50 text-blue-600',
    purple: 'bg-purple-50 text-purple-600',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="bg-white border border-gray-200 rounded-xl p-5 card-hover"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{animatedValue.toLocaleString()}</p>
        </div>
        <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', colorClasses[iconColor])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="flex items-center gap-1.5 mt-4">
        <div
          className={cn(
            'flex items-center gap-0.5 text-sm font-medium',
            isPositive ? 'text-emerald-600' : 'text-red-600'
          )}
        >
          {isPositive ? (
            <TrendingUp className="w-4 h-4" />
          ) : (
            <TrendingDown className="w-4 h-4" />
          )}
          <span>{Math.abs(trend)}%</span>
        </div>
        <span className="text-sm text-gray-400">vs last month</span>
      </div>
    </motion.div>
  );
}
