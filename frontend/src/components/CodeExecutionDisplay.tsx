import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Code2, 
  Play, 
  CheckCircle2, 
  XCircle, 
  Terminal, 
  Copy, 
  Check,
  ChevronDown,
  Clock,
  Cpu,
  AlertTriangle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export interface CodeExecutionResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  executionTimeMs: number;
  memoryUsedMb?: number;
}

export interface CodeExecutionData {
  code: string;
  language: string;
  status: 'running' | 'completed' | 'error' | 'timeout';
  result?: CodeExecutionResult;
  error?: string;
}

interface CodeExecutionDisplayProps {
  execution: CodeExecutionData;
  showLineNumbers?: boolean;
  maxHeight?: number;
}

const languageLabels: Record<string, string> = {
  python: 'Python',
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  java: 'Java',
  cpp: 'C++',
  c: 'C',
  go: 'Go',
  rust: 'Rust',
  ruby: 'Ruby',
  php: 'PHP',
  bash: 'Bash',
  sql: 'SQL',
  html: 'HTML',
  css: 'CSS',
  json: 'JSON',
  yaml: 'YAML',
  markdown: 'Markdown',
};

const languageColors: Record<string, string> = {
  python: 'bg-blue-100 text-blue-700 border-blue-200',
  javascript: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  typescript: 'bg-blue-100 text-blue-700 border-blue-200',
  java: 'bg-orange-100 text-orange-700 border-orange-200',
  cpp: 'bg-purple-100 text-purple-700 border-purple-200',
  c: 'bg-purple-100 text-purple-700 border-purple-200',
  go: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  rust: 'bg-orange-100 text-orange-700 border-orange-200',
  bash: 'bg-gray-100 text-gray-700 border-gray-200',
  sql: 'bg-emerald-100 text-emerald-700 border-emerald-200',
};

export function CodeExecutionDisplay({ 
  execution, 
  showLineNumbers = true,
  maxHeight = 400 
}: CodeExecutionDisplayProps) {
  const { code, language, status, result, error } = execution;
  const [isExpanded, setIsExpanded] = useState(true);
  const [isOutputExpanded, setIsOutputExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = code.split('\n');
  const languageLabel = languageLabels[language] || language.toUpperCase();
  const languageColor = languageColors[language] || 'bg-gray-100 text-gray-700 border-gray-200';

  return (
    <div className="w-full rounded-xl border border-gray-200 overflow-hidden bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-3">
          {/* Language Badge */}
          <span className={cn(
            'px-2 py-0.5 rounded-md text-xs font-medium border',
            languageColor
          )}>
            {languageLabel}
          </span>

          {/* Status */}
          <div className="flex items-center gap-1.5">
            {status === 'running' ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                >
                  <Play className="w-3.5 h-3.5 text-amber-500" />
                </motion.div>
                <span className="text-xs text-amber-600 font-medium">Running...</span>
              </>
            ) : status === 'completed' ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-xs text-emerald-600 font-medium">
                  Completed {result && `· ${result.executionTimeMs}ms`}
                </span>
              </>
            ) : status === 'timeout' ? (
              <>
                <Clock className="w-3.5 h-3.5 text-orange-500" />
                <span className="text-xs text-orange-600 font-medium">Timeout</span>
              </>
            ) : (
              <>
                <XCircle className="w-3.5 h-3.5 text-red-500" />
                <span className="text-xs text-red-600 font-medium">Error</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1">
          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
            title="Copy code"
          >
            {copied ? (
              <Check className="w-4 h-4 text-emerald-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>

          {/* Expand/Collapse */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <motion.div
              animate={{ rotate: isExpanded ? 0 : 180 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="w-4 h-4" />
            </motion.div>
          </button>
        </div>
      </div>

      {/* Code Block */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div 
              className="relative overflow-auto bg-gray-900"
              style={{ maxHeight }}
            >
              <pre className="p-4 text-sm font-mono">
                <code className="text-gray-100">
                  {showLineNumbers && (
                    <div className="absolute left-0 top-4 bottom-0 w-12 bg-gray-900 border-r border-gray-700 select-none">
                      {lines.map((_, i) => (
                        <div 
                          key={i} 
                          className="text-right pr-3 text-gray-500 text-xs leading-6"
                        >
                          {i + 1}
                        </div>
                      ))}
                    </div>
                  )}
                  <div className={showLineNumbers ? 'pl-10' : ''}>
                    {lines.map((line, i) => (
                      <div key={i} className="leading-6 whitespace-pre">
                        {line || ' '}
                      </div>
                    ))}
                  </div>
                </code>
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Output Section */}
      {result && (result.stdout || result.stderr) && (
        <div className="border-t border-gray-200">
          {/* Output Header */}
          <button
            onClick={() => setIsOutputExpanded(!isOutputExpanded)}
            className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Output</span>
              {result.exitCode !== 0 && (
                <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-xs rounded">
                  Exit {result.exitCode}
                </span>
              )}
            </div>
            <motion.div
              animate={{ rotate: isOutputExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </motion.div>
          </button>

          {/* Output Content */}
          <AnimatePresence>
            {isOutputExpanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="overflow-hidden"
              >
                <div className="p-4 space-y-3">
                  {/* Stdout */}
                  {result.stdout && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1.5">Standard Output</p>
                      <pre className="p-3 bg-gray-900 rounded-lg text-sm font-mono text-gray-100 overflow-auto max-h-48">
                        {result.stdout}
                      </pre>
                    </div>
                  )}

                  {/* Stderr */}
                  {result.stderr && (
                    <div>
                      <p className="text-xs text-red-500 mb-1.5">Standard Error</p>
                      <pre className="p-3 bg-red-950 rounded-lg text-sm font-mono text-red-200 overflow-auto max-h-48">
                        {result.stderr}
                      </pre>
                    </div>
                  )}

                  {/* Execution Stats */}
                  <div className="flex items-center gap-4 pt-2 border-t border-gray-200">
                    <div className="flex items-center gap-1.5 text-xs text-gray-500">
                      <Clock className="w-3.5 h-3.5" />
                      {result.executionTimeMs}ms
                    </div>
                    {result.memoryUsedMb && (
                      <div className="flex items-center gap-1.5 text-xs text-gray-500">
                        <Cpu className="w-3.5 h-3.5" />
                        {result.memoryUsedMb}MB
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border-t border-red-200">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-700">Execution Error</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Compact inline code display for use in messages
interface InlineCodeProps {
  code: string;
  language?: string;
}

export function InlineCode({ code, language = 'text' }: InlineCodeProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-2">
      <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={handleCopy}
          className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <pre className="p-3 bg-gray-900 rounded-lg text-sm font-mono text-gray-100 overflow-x-auto">
        <code>{code}</code>
      </pre>
      {language !== 'text' && (
        <span className="absolute left-2 top-2 text-xs text-gray-500">
          {language}
        </span>
      )}
    </div>
  );
}

// Code block with syntax highlighting placeholder (can be enhanced with Prism.js or similar)
export function CodeBlock({ 
  code, 
  language = 'text',
  filename 
}: { 
  code: string; 
  language?: string;
  filename?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden my-3">
      {(filename || language !== 'text') && (
        <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Code2 className="w-4 h-4 text-gray-500" />
            {filename && (
              <span className="text-sm font-medium text-gray-700">{filename}</span>
            )}
            <span className={cn(
              'px-1.5 py-0.5 rounded text-xs font-medium',
              languageColors[language] || 'bg-gray-100 text-gray-600'
            )}>
              {languageLabels[language] || language}
            </span>
          </div>
          <button
            onClick={handleCopy}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      )}
      <div className="relative">
        <pre className="p-4 bg-gray-900 text-sm font-mono text-gray-100 overflow-x-auto">
          <code>{code}</code>
        </pre>
        {!filename && language === 'text' && (
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>
    </div>
  );
}
