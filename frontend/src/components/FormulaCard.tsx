import { useState } from 'react';
import { motion } from 'framer-motion';
import { FunctionSquare, Play, BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { Formula } from '@/types';

interface FormulaCardProps {
  formula: Formula;
  index: number;
}

const categoryColors: Record<string, string> = {
  Finance: 'bg-emerald-100 text-emerald-700',
  Engineering: 'bg-blue-100 text-blue-700',
  Statistics: 'bg-purple-100 text-purple-700',
  Custom: 'bg-gray-100 text-gray-700',
};

export function FormulaCard({ formula, index }: FormulaCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showExecuteDialog, setShowExecuteDialog] = useState(false);
  const [parameterValues, setParameterValues] = useState<Record<string, string>>({});

  const handleExecute = () => {
    console.log('Executing formula with parameters:', parameterValues);
    setShowExecuteDialog(false);
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.05, duration: 0.3 }}
        className={cn(
          'bg-white border border-gray-200 rounded-xl overflow-hidden',
          'transition-all duration-200 card-hover'
        )}
      >
        {/* Header */}
        <div className="p-5">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
                <FunctionSquare className="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">{formula.name}</h3>
                <Badge className={cn('mt-1 text-xs', categoryColors[formula.category] || categoryColors.Custom)}>
                  {formula.category}
                </Badge>
              </div>
            </div>
          </div>

          {/* Description */}
          <p className="text-sm text-gray-600 mb-4">{formula.description}</p>

          {/* Parameters Preview */}
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="font-medium">Parameters:</span>
            <span>{formula.parameters.length}</span>
            {formula.parameters.length > 0 && (
              <span className="text-gray-400">
                ({formula.parameters.map(p => p.name).join(', ')})
              </span>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="text-gray-500 hover:text-gray-700"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-4 h-4 mr-1" />
                Less details
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4 mr-1" />
                More details
              </>
            )}
          </Button>

          <div className="flex gap-2">
            {formula.documentationUrl && (
              <Button variant="ghost" size="sm" className="text-gray-500 hover:text-gray-700">
                <BookOpen className="w-4 h-4 mr-1" />
                Docs
              </Button>
            )}
            <Button
              size="sm"
              onClick={() => setShowExecuteDialog(true)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              <Play className="w-4 h-4 mr-1" />
              Execute
            </Button>
          </div>
        </div>

        {/* Expanded Details */}
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-5 py-4 bg-gray-50 border-t border-gray-100"
          >
            <h4 className="text-sm font-medium text-gray-900 mb-3">Parameters</h4>
            <div className="space-y-3">
              {formula.parameters.map((param) => (
                <div key={param.name} className="flex items-start gap-3">
                  <code className="px-2 py-1 bg-white border border-gray-200 rounded text-xs font-mono text-gray-700">
                    {param.name}
                  </code>
                  <div className="flex-1">
                    <span className="text-xs text-gray-500">{param.type}</span>
                    {param.required && <span className="text-xs text-red-500 ml-2">required</span>}
                    {param.description && (
                      <p className="text-xs text-gray-600 mt-1">{param.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>

      {/* Execute Dialog */}
      <Dialog open={showExecuteDialog} onOpenChange={setShowExecuteDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Execute {formula.name}</DialogTitle>
            <DialogDescription>{formula.description}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {formula.parameters.map((param) => (
              <div key={param.name} className="space-y-2">
                <Label htmlFor={param.name}>
                  {param.name}
                  {param.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                <Input
                  id={param.name}
                  placeholder={param.description || `Enter ${param.name}`}
                  value={parameterValues[param.name] || ''}
                  onChange={(e) =>
                    setParameterValues((prev) => ({
                      ...prev,
                      [param.name]: e.target.value,
                    }))
                  }
                />
                <p className="text-xs text-gray-500">Type: {param.type}</p>
              </div>
            ))}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowExecuteDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleExecute} className="bg-indigo-600 hover:bg-indigo-700 text-white">
              <Play className="w-4 h-4 mr-1" />
              Execute
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
