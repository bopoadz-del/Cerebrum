import { motion } from 'framer-motion';
import { Globe, Search, ExternalLink, CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source?: string;
  publishedDate?: string;
}

export interface WebSearchData {
  query: string;
  status: 'searching' | 'completed' | 'error';
  results?: SearchResult[];
  error?: string;
  searchTimeMs?: number;
}

interface WebSearchIndicatorProps {
  searchData: WebSearchData;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function WebSearchIndicator({ 
  searchData, 
  isCollapsed = false,
  onToggleCollapse 
}: WebSearchIndicatorProps) {
  const { query, status, results, error, searchTimeMs } = searchData;

  return (
    <div className="w-full">
      {/* Search Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          'flex items-center gap-3 p-3 rounded-xl border transition-all duration-200',
          status === 'searching' 
            ? 'bg-blue-50/80 border-blue-200' 
            : status === 'completed'
            ? 'bg-emerald-50/80 border-emerald-200'
            : 'bg-red-50/80 border-red-200'
        )}
      >
        {/* Status Icon */}
        <div className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
          status === 'searching' 
            ? 'bg-blue-100' 
            : status === 'completed'
            ? 'bg-emerald-100'
            : 'bg-red-100'
        )}>
          {status === 'searching' ? (
            <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          ) : status === 'completed' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : (
            <Globe className="w-4 h-4 text-red-600" />
          )}
        </div>

        {/* Search Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-gray-500" />
            <span className="text-sm font-medium text-gray-700 truncate">
              {status === 'searching' ? 'Searching' : 'Searched'}: "{query}"
            </span>
          </div>
          {status === 'completed' && results && (
            <p className="text-xs text-gray-500 mt-0.5">
              Found {results.length} result{results.length !== 1 ? 's' : ''}
              {searchTimeMs && ` · ${searchTimeMs}ms`}
            </p>
          )}
          {status === 'error' && error && (
            <p className="text-xs text-red-600 mt-0.5">{error}</p>
          )}
        </div>

        {/* Toggle Button */}
        {results && results.length > 0 && (
          <button
            onClick={onToggleCollapse}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <motion.div
              animate={{ rotate: isCollapsed ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <svg 
                className="w-4 h-4" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </motion.div>
          </button>
        )}
      </motion.div>

      {/* Search Results */}
      {!isCollapsed && results && results.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-2 space-y-2"
        >
          {results.map((result, index) => (
            <motion.a
              key={index}
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className={cn(
                'block p-3 bg-white border border-gray-200 rounded-lg',
                'hover:border-indigo-300 hover:shadow-sm transition-all duration-200',
                'group'
              )}
            >
              <div className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  {/* Title */}
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-medium text-indigo-600 group-hover:text-indigo-700 truncate">
                      {result.title}
                    </h4>
                    <ExternalLink className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>

                  {/* URL */}
                  <p className="text-xs text-gray-500 truncate mt-0.5">
                    {result.url}
                  </p>

                  {/* Snippet */}
                  <p className="text-sm text-gray-600 mt-1.5 line-clamp-2">
                    {result.snippet}
                  </p>

                  {/* Source & Date */}
                  {(result.source || result.publishedDate) && (
                    <div className="flex items-center gap-2 mt-2">
                      {result.source && (
                        <span className="text-xs text-gray-400">
                          {result.source}
                        </span>
                      )}
                      {result.publishedDate && (
                        <span className="text-xs text-gray-400">
                          · {result.publishedDate}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </motion.a>
          ))}
        </motion.div>
      )}
    </div>
  );
}

// Compact version for inline display in messages
export function WebSearchBadge({ status }: { status: WebSearchData['status'] }) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
      status === 'searching' 
        ? 'bg-blue-100 text-blue-700' 
        : status === 'completed'
        ? 'bg-emerald-100 text-emerald-700'
        : 'bg-red-100 text-red-700'
    )}>
      {status === 'searching' ? (
        <>
          <Loader2 className="w-3 h-3 animate-spin" />
          Searching web...
        </>
      ) : status === 'completed' ? (
        <>
          <Globe className="w-3 h-3" />
          Web search
        </>
      ) : (
        <>
          <Globe className="w-3 h-3" />
          Search failed
        </>
      )}
    </span>
  );
}
