import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FunctionSquare, Search, Plus, Loader2 } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FormulaCard } from '@/components/FormulaCard';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import type { Formula } from '@/types';
import { STORAGE_KEYS } from '@/context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

const categories = ['All', 'Finance', 'Engineering', 'Statistics', 'Custom'];

export default function FormulasPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [formulas, setFormulas] = useState<Formula[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch formulas from API
  useEffect(() => {
    const fetchFormulas = async () => {
      try {
        const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
        const response = await fetch(`${API_BASE}/formulas`, {
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch formulas: ${response.statusText}`);
        }

        const data = await response.json();
        setFormulas(data.formulas || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load formulas');
        setFormulas([]);
      } finally {
        setLoading(false);
      }
    };

    fetchFormulas();
  }, []);

  const filteredFormulas = formulas.filter((formula) => {
    const matchesSearch = formula.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         formula.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || formula.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="p-8">
      <ModuleHeader
        title="Formula Catalog"
        description="Browse and execute formulas for calculations and analysis"
        icon={FunctionSquare}
        iconColor="indigo"
        action={
          <Button className="bg-indigo-600 hover:bg-indigo-700 text-white">
            <Plus className="w-4 h-4 mr-1" />
            New Formula
          </Button>
        }
      />

      {/* Search and Filter */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex flex-col sm:flex-row gap-4 mb-8"
      >
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search formulas..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedCategory === category
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Error State */}
      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6"
        >
          <p className="text-red-600">{error}</p>
        </motion.div>
      )}

      {/* Loading State */}
      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-16"
        >
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <span className="ml-2 text-gray-600">Loading formulas...</span>
        </motion.div>
      )}

      {/* Results Count */}
      {!loading && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-sm text-gray-500 mb-4"
        >
          Showing {filteredFormulas.length} formula{filteredFormulas.length !== 1 ? 's' : ''}
        </motion.p>
      )}

      {/* Formula Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredFormulas.map((formula, index) => (
          <FormulaCard key={formula.id} formula={formula} index={index} />
        ))}
      </div>

      {!loading && filteredFormulas.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16"
        >
          <FunctionSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No formulas found matching your criteria</p>
        </motion.div>
      )}
    </div>
  );
}
