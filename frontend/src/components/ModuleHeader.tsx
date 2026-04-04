import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModuleHeaderProps {
  title: string;
  description: string;
  icon: LucideIcon;
  iconColor?: string;
  action?: React.ReactNode;
}

export function ModuleHeader({
  title,
  description,
  icon: Icon,
  iconColor = 'indigo',
  action,
}: ModuleHeaderProps) {
  const colorClasses: Record<string, string> = {
    indigo: 'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    rose: 'bg-rose-50 text-rose-600',
    blue: 'bg-blue-50 text-blue-600',
    purple: 'bg-purple-50 text-purple-600',
    cyan: 'bg-cyan-50 text-cyan-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-start justify-between mb-8"
    >
      <div className="flex items-start gap-4">
        <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0', colorClasses[iconColor])}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
          <p className="text-gray-500 mt-1">{description}</p>
        </div>
      </div>
      {action && <div>{action}</div>}
    </motion.div>
  );
}
