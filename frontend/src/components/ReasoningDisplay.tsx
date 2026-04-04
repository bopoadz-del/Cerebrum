import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, ChevronDown, Wrench, Database, Lightbulb, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ReasoningData, ReasoningStep } from '@/types';

interface ReasoningDisplayProps {
  reasoning?: ReasoningData;
  isThinking?: boolean;
}

const stepIcons = {
  tool: Wrench,
  data: Database,
  thought: Lightbulb,
  decision: CheckCircle2,
};

const stepColors = {
  tool: 'text-indigo-600 bg-indigo-50 border-indigo-200',
  data: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  thought: 'text-amber-600 bg-amber-50 border-amber-200',
  decision: 'text-purple-600 bg-purple-50 border-purple-200',
};

export function ReasoningDisplay({ reasoning, isThinking }: ReasoningDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Show thinking animation if in thinking state
  if (isThinking) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 mt-2">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        >
          <Brain className="w-4 h-4 text-indigo-500" />
        </motion.div>
        <span className="font-medium">Thinking</span>
        <motion.span
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="flex gap-0.5"
        >
          <span>.</span>
          <motion.span
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
          >
            .
          </motion.span>
          <motion.span
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
          >
            .
          </motion.span>
        </motion.span>
      </div>
    );
  }

  // Don't render if no reasoning data
  if (!reasoning) {
    return null;
  }

  return (
    <div className="mt-3">
      {/* Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
          'bg-gray-50 hover:bg-gray-100 text-gray-600 hover:text-gray-800',
          'border border-gray-200 hover:border-gray-300',
          'focus:outline-none focus:ring-2 focus:ring-indigo-500/20'
        )}
      >
        <Brain className="w-4 h-4 text-indigo-500" />
        <span>View reasoning</span>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </button>

      {/* Expandable Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="overflow-hidden"
          >
            <div className="mt-3 p-4 bg-gray-50/80 border border-gray-200 rounded-xl space-y-4">
              {/* Reasoning Steps */}
              {reasoning.steps && reasoning.steps.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Reasoning Process
                  </h4>
                  <div className="space-y-2">
                    {reasoning.steps.map((step, index) => (
                      <ReasoningStepItem key={index} step={step} index={index} />
                    ))}
                  </div>
                </div>
              )}

              {/* Tools Considered */}
              {reasoning.toolsConsidered && reasoning.toolsConsidered.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Tools Considered
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {reasoning.toolsConsidered.map((tool, index) => (
                      <span
                        key={index}
                        className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs font-medium rounded-full border border-indigo-100"
                      >
                        {tool}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Data Looked Up */}
              {reasoning.dataLookedUp && reasoning.dataLookedUp.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Data Sources
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {reasoning.dataLookedUp.map((data, index) => (
                      <span
                        key={index}
                        className="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-xs font-medium rounded-full border border-emerald-100"
                      >
                        {data}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Why This Answer */}
              {reasoning.whyThisAnswer && (
                <div className="pt-3 border-t border-gray-200">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Why This Answer
                  </h4>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {reasoning.whyThisAnswer}
                  </p>
                </div>
              )}

              {/* Execution Time */}
              {reasoning.executionTimeMs && (
                <div className="pt-2 border-t border-gray-200">
                  <span className="text-xs text-gray-400">
                    Execution time: {reasoning.executionTimeMs}ms
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ReasoningStepItem({ step, index }: { step: ReasoningStep; index: number }) {
  const Icon = stepIcons[step.type] || Lightbulb;
  const colorClass = stepColors[step.type] || stepColors.thought;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className={cn(
        'flex items-start gap-3 p-2.5 rounded-lg border transition-colors',
        colorClass
      )}
    >
      <div className="flex-shrink-0 mt-0.5">
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{step.content}</p>
        {step.details && (
          <p className="text-xs opacity-75 mt-1">{step.details}</p>
        )}
        {step.timestamp && (
          <p className="text-xs opacity-50 mt-1">
            {new Date(step.timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </motion.div>
  );
}
