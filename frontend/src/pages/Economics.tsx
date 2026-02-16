import React, { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  BarChart3,
  Calendar,
  Download,
  Filter,
  MoreVertical,
  AlertTriangle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface BudgetItem {
  id: string;
  category: string;
  allocated: number;
  spent: number;
  remaining: number;
  status: 'on-track' | 'at-risk' | 'over-budget';
  lastUpdated: Date;
}

interface CostBreakdown {
  category: string;
  amount: number;
  percentage: number;
  color: string;
}

const mockBudget: BudgetItem[] = [
  {
    id: '1',
    category: 'Materials',
    allocated: 2500000,
    spent: 1800000,
    remaining: 700000,
    status: 'on-track',
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 24),
  },
  {
    id: '2',
    category: 'Labor',
    allocated: 3200000,
    spent: 2900000,
    remaining: 300000,
    status: 'at-risk',
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 12),
  },
  {
    id: '3',
    category: 'Equipment',
    allocated: 800000,
    spent: 950000,
    remaining: -150000,
    status: 'over-budget',
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 6),
  },
  {
    id: '4',
    category: 'Subcontractors',
    allocated: 1500000,
    spent: 800000,
    remaining: 700000,
    status: 'on-track',
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 48),
  },
  {
    id: '5',
    category: 'Overhead',
    allocated: 500000,
    spent: 320000,
    remaining: 180000,
    status: 'on-track',
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3),
  },
];

const costBreakdown: CostBreakdown[] = [
  { category: 'Materials', amount: 1800000, percentage: 28, color: '#3B82F6' },
  { category: 'Labor', amount: 2900000, percentage: 45, color: '#10B981' },
  { category: 'Equipment', amount: 950000, percentage: 15, color: '#F59E0B' },
  { category: 'Subcontractors', amount: 800000, percentage: 12, color: '#8B5CF6' },
];

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(amount);
};

const Economics: React.FC = () => {
  const [dateRange, setDateRange] = useState<'month' | 'quarter' | 'year'>('quarter');
  const totalAllocated = mockBudget.reduce((acc, item) => acc + item.allocated, 0);
  const totalSpent = mockBudget.reduce((acc, item) => acc + item.spent, 0);
  const totalRemaining = totalAllocated - totalSpent;
  const percentSpent = (totalSpent / totalAllocated) * 100;

  const getStatusIcon = (status: BudgetItem['status']) => {
    switch (status) {
      case 'on-track':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'at-risk':
        return <AlertTriangle size={16} className="text-yellow-500" />;
      case 'over-budget':
        return <AlertTriangle size={16} className="text-red-500" />;
    }
  };

  const getStatusColor = (status: BudgetItem['status']) => {
    switch (status) {
      case 'on-track':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400';
      case 'at-risk':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400';
      case 'over-budget':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Budget Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Track project costs and budget allocation
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
            {(['month', 'quarter', 'year'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={cn(
                  'px-3 py-2 text-sm capitalize transition-colors',
                  dateRange === range
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                    : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
                )}
              >
                {range}
              </button>
            ))}
          </div>
          <button className="inline-flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
            <Download size={18} />
            Export
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Budget</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatCurrency(totalAllocated)}
              </p>
            </div>
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <DollarSign size={24} className="text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Spent</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatCurrency(totalSpent)}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {percentSpent.toFixed(1)}% of budget
              </p>
            </div>
            <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
              <TrendingUp size={24} className="text-orange-600 dark:text-orange-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Remaining</p>
              <p
                className={cn(
                  'text-2xl font-bold',
                  totalRemaining >= 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-red-600 dark:text-red-400'
                )}
              >
                {formatCurrency(totalRemaining)}
              </p>
            </div>
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <TrendingDown size={24} className="text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Project Health</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">Good</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">3 of 5 on track</p>
            </div>
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <CheckCircle size={24} className="text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Breakdown */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Cost Breakdown
          </h2>
          <div className="flex items-center justify-center">
            <div className="relative w-48 h-48">
              <svg className="w-full h-full transform -rotate-90">
                {costBreakdown.reduce(
                  (acc, item, index) => {
                    const startAngle = acc.offset;
                    const sweepAngle = (item.percentage / 100) * 360;
                    const endAngle = startAngle + sweepAngle;

                    const startRad = (startAngle * Math.PI) / 180;
                    const endRad = (endAngle * Math.PI) / 180;

                    const x1 = 80 + 70 * Math.cos(startRad);
                    const y1 = 80 + 70 * Math.sin(startRad);
                    const x2 = 80 + 70 * Math.cos(endRad);
                    const y2 = 80 + 70 * Math.sin(endRad);

                    const largeArc = sweepAngle > 180 ? 1 : 0;

                    acc.elements.push(
                      <path
                        key={item.category}
                        d={`M 80 80 L ${x1} ${y1} A 70 70 0 ${largeArc} 1 ${x2} ${y2} Z`}
                        fill={item.color}
                        stroke="white"
                        strokeWidth="2"
                      />
                    );

                    acc.offset = endAngle;
                    return acc;
                  },
                  { elements: [] as React.ReactNode[], offset: 0 }
                ).elements}
                <circle cx="80" cy="80" r="40" fill="white" className="dark:fill-gray-900" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatCurrency(totalSpent)}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">Total Spent</span>
              </div>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {costBreakdown.map((item) => (
              <div key={item.category} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">{item.category}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {formatCurrency(item.amount)}
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white w-12 text-right">
                    {item.percentage}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Budget by Category */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Budget by Category
          </h2>
          <div className="space-y-4">
            {mockBudget.map((item) => {
              const percentUsed = (item.spent / item.allocated) * 100;
              return (
                <div key={item.id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {item.category}
                    </span>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(item.status)}
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {formatCurrency(item.spent)} / {formatCurrency(item.allocated)}
                      </span>
                    </div>
                  </div>
                  <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full transition-all',
                        item.status === 'on-track' && 'bg-green-500',
                        item.status === 'at-risk' && 'bg-yellow-500',
                        item.status === 'over-budget' && 'bg-red-500'
                      )}
                      style={{ width: `${Math.min(percentUsed, 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {formatCurrency(item.remaining)} remaining
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Budget Table */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Budget Details
          </h2>
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
            <MoreVertical size={18} className="text-gray-500" />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Category
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Allocated
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Spent
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Remaining
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Last Updated
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {mockBudget.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                    {item.category}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-400">
                    {formatCurrency(item.allocated)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-400">
                    {formatCurrency(item.spent)}
                  </td>
                  <td
                    className={cn(
                      'px-4 py-3 text-sm text-right font-medium',
                      item.remaining >= 0
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    )}
                  >
                    {formatCurrency(item.remaining)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full',
                        getStatusColor(item.status)
                      )}
                    >
                      {getStatusIcon(item.status)}
                      {item.status.replace('-', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-1">
                      <Clock size={14} />
                      {item.lastUpdated.toLocaleDateString()}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Economics;
