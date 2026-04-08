import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Check, X, Copy, CheckCheck, Terminal } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface CodeExecutionDisplayProps {
  code: string;
  language?: string;
  output?: string;
  error?: string;
  executionTime?: number;
  isExecuting?: boolean;
  onExecute?: () => void;
}

export function CodeExecutionDisplay({
  code,
  language = 'python',
  output,
  error,
  executionTime,
  isExecuting = false,
  onExecute,
}: CodeExecutionDisplayProps) {
  const [copied, setCopied] = useState(false);
  const [showOutput, setShowOutput] = useState(true);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Simple syntax highlighting for common keywords
  const highlightCode = (code: string) => {
    const keywords = ['def', 'class', 'if', 'else', 'elif', 'for', 'while', 'return', 'import', 'from', 'try', 'except', 'with', 'as'];
    const strings = /(".*?"|'.*?')/g;
    const comments = /(#.*$)/gm;
    
    let highlighted = code
      .replace(strings, '<span class="text-green-400">$1</span>')
      .replace(comments, '<span class="text-gray-500">$1</span>');
    
    keywords.forEach(keyword => {
      const regex = new RegExp(`\\b(${keyword})\\b`, 'g');
      highlighted = highlighted.replace(regex, '<span class="text-purple-400">$1</span>');
    });
    
    return highlighted;
  };

  return (
    <div className="rounded-lg overflow-hidden border border-gray-200 my-2">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-900 text-gray-400">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4" />
          <span className="text-xs font-medium uppercase">{language}</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 px-2 text-gray-400 hover:text-white hover:bg-gray-800"
          >
            {copied ? <CheckCheck className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </Button>
          {onExecute && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onExecute}
              disabled={isExecuting}
              className="h-7 px-2 text-gray-400 hover:text-white hover:bg-gray-800"
            >
              {isExecuting ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                >
                  <Play className="w-4 h-4" />
                </motion.div>
              ) : (
                <Play className="w-4 h-4" />
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Code */}
      <div className="bg-gray-900 p-4 overflow-x-auto">
        <pre className="text-sm font-mono text-gray-300">
          <code dangerouslySetInnerHTML={{ __html: highlightCode(code) }} />
        </pre>
      </div>

      {/* Output */}
      <AnimatePresence>
        {(output || error) && showOutput && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-gray-700"
          >
            <div className="px-3 py-2 bg-gray-900 text-gray-400 flex items-center justify-between">
              <span className="text-xs">Output</span>
              {executionTime && (
                <span className="text-xs text-gray-500">{executionTime}ms</span>
              )}
            </div>
            <div className="px-3 py-2 bg-gray-950 font-mono text-sm">
              {error ? (
                <pre className="text-red-400 whitespace-pre-wrap">{error}</pre>
              ) : (
                <pre className="text-green-400 whitespace-pre-wrap">{output}</pre>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
