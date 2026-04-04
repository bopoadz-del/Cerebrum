import { motion } from 'framer-motion';
import { Globe, Loader2 } from 'lucide-react';

interface WebSearchIndicatorProps {
  query: string;
  isSearching: boolean;
  results?: {
    title: string;
    url: string;
    snippet: string;
  }[];
}

export function WebSearchIndicator({ query, isSearching, results }: WebSearchIndicatorProps) {
  if (!isSearching && !results) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg"
    >
      {isSearching ? (
        <>
          <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          <span className="text-sm text-blue-700">
            Searching the web for "{query}"...
          </span>
        </>
      ) : results && results.length > 0 ? (
        <>
          <Globe className="w-4 h-4 text-blue-600" />
          <span className="text-sm text-blue-700">
            Found {results.length} web results
          </span>
        </>
      ) : null}
    </motion.div>
  );
}
