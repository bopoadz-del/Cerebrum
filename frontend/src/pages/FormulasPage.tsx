import { useState } from 'react';
import { motion } from 'framer-motion';
import { FunctionSquare, Search, Plus } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FormulaCard } from '@/components/FormulaCard';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { } from '@/components/ui/badge';
import type { Formula } from '@/types';

const mockFormulas: Formula[] = [
  {
    id: '1',
    name: 'Net Present Value',
    description: 'Calculate the present value of future cash flows.',
    category: 'Finance',
    formula: 'NPV = Σ(Ct / (1+r)^t) - C0',
    variables: [
      { name: 'Ct', description: 'Cash flow at time t', unit: '$' },
      { name: 'r', description: 'Discount rate', unit: '%' },
      { name: 'C0', description: 'Initial investment', unit: '$' },
    ],
  },
  {
    id: '2',
    name: 'Concrete Volume',
    description: 'Calculate concrete volume for a rectangular slab.',
    category: 'Construction',
    formula: 'V = L × W × D',
    variables: [
      { name: 'L', description: 'Length', unit: 'ft' },
      { name: 'W', description: 'Width', unit: 'ft' },
      { name: 'D', description: 'Depth', unit: 'ft' },
    ],
  },
];

const categories = ['All', 'Finance', 'Engineering', 'Statistics', 'Custom'];

export default function FormulasPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  const filteredFormulas = mockFormulas.filter((formula) => {
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

      {/* Search and */}
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

      {/* Results Count */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-sm text-gray-500 mb-4"
      >
        Showing {filteredFormulas.length} formula{filteredFormulas.length !== 1 ? 's' : ''}
      </motion.p>

      {/* Formula Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredFormulas.map((formula, index) => (
          <FormulaCard key={formula.id} formula={formula} index={index} />
        ))}
      </div>

      {filteredFormulas.length === 0 && (
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
