import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SmartContextToggleProps {
  sessionToken?: string;
  onToggle?: (enabled: boolean) => void;
}

export function SmartContextToggle({ onToggle }: SmartContextToggleProps) {
  const [enabled, setEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleToggle = useCallback(async () => {
    const nextState = !enabled;
    setIsLoading(true);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 200));
    
    setEnabled(nextState);
    onToggle?.(nextState);
    setIsLoading(false);
  }, [enabled, onToggle]);

  return (
    <button
      onClick={handleToggle}
      disabled={isLoading}
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200',
        enabled 
          ? 'bg-indigo-50 border-indigo-200 text-indigo-700' 
          : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
      )}
      title={enabled ? 'Smart Context: ON' : 'Smart Context: OFF'}
    >
      <motion.div
        animate={{ 
          scale: enabled ? 1.1 : 1,
          rotate: enabled ? 0 : 0
        }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      >
        <Brain className={cn('w-4 h-4', enabled ? 'text-indigo-600' : 'text-gray-400')} />
      </motion.div>
      <span className="text-sm font-medium">
        {enabled ? 'ON' : 'OFF'}
      </span>
      <span className="sr-only">Toggle Smart Context</span>
    </button>
  );
}
