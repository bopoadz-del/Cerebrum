import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  FileText,
  Activity,
  Users,
  Zap,
  Clock,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';
import { StatCard } from '@/components/StatCard';
import { ModuleHeader } from '@/components/ModuleHeader';
import { cn } from '@/lib/utils';

// Sample data for charts
const activityData = [
  { name: 'Mon', analyses: 45, uploads: 32 },
  { name: 'Tue', analyses: 52, uploads: 38 },
  { name: 'Wed', analyses: 38, uploads: 28 },
  { name: 'Thu', analyses: 65, uploads: 45 },
  { name: 'Fri', analyses: 48, uploads: 35 },
  { name: 'Sat', analyses: 25, uploads: 18 },
  { name: 'Sun', analyses: 20, uploads: 15 },
];

const moduleUsageData = [
  { name: 'PDF', value: 35, color: '#6366f1' },
  { name: 'Schedule', value: 25, color: '#10b981' },
  { name: 'Audio', value: 20, color: '#f59e0b' },
  { name: 'CAD', value: 15, color: '#3b82f6' },
  { name: 'Other', value: 5, color: '#9ca3af' },
];

const recentActivity = [
  { id: 1, action: 'PDF Analysis', file: 'Q4-Report.pdf', status: 'completed', time: '2 min ago' },
  { id: 2, action: 'Schedule Check', file: 'Project-X.xer', status: 'completed', time: '15 min ago' },
  { id: 3, action: 'Audio Transcription', file: 'Meeting-Recording.mp3', status: 'processing', time: '32 min ago' },
  { id: 4, action: 'CAD Analysis', file: 'Floor-Plan.dwg', status: 'completed', time: '1 hour ago' },
  { id: 5, action: 'Anomaly Detection', file: 'sensor-data.csv', status: 'error', time: '2 hours ago' },
];

const stats = [
  { title: 'Total Analyses', value: 1247, trend: 12.5, icon: Activity, iconColor: 'indigo' },
  { title: 'Files Processed', value: 3856, trend: 8.2, icon: FileText, iconColor: 'emerald' },
  { title: 'Active Users', value: 48, trend: 5.1, icon: Users, iconColor: 'blue' },
  { title: 'System Health', value: 99.9, trend: 0.3, icon: Zap, iconColor: 'amber' },
];

export default function Dashboard() {
  return (
    <div className="p-8">
      <ModuleHeader
        title="Dashboard"
        description="Overview of your analysis activity and system performance"
        icon={Activity}
        iconColor="indigo"
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat, index) => (
          <StatCard
            key={stat.title}
            title={stat.title}
            value={stat.value}
            trend={stat.trend}
            icon={stat.icon}
            iconColor={stat.iconColor}
            delay={index * 0.1}
          />
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Activity Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-6"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Weekly Activity</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                <YAxis stroke="#9ca3af" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                  }}
                />
                <Bar dataKey="analyses" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="uploads" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Module Usage Pie Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-white border border-gray-200 rounded-xl p-6"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Module Usage</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={moduleUsageData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {moduleUsageData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-3 mt-4 justify-center">
            {moduleUsageData.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-xs text-gray-600">{item.name}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="bg-white border border-gray-200 rounded-xl overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
        </div>
        <div className="divide-y divide-gray-100">
          {recentActivity.map((activity) => (
            <div key={activity.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
              <div className="flex items-center gap-4">
                <div
                  className={cn(
                    'w-10 h-10 rounded-lg flex items-center justify-center',
                    activity.status === 'completed' && 'bg-emerald-50',
                    activity.status === 'processing' && 'bg-amber-50',
                    activity.status === 'error' && 'bg-red-50'
                  )}
                >
                  {activity.status === 'completed' && <CheckCircle className="w-5 h-5 text-emerald-600" />}
                  {activity.status === 'processing' && <Clock className="w-5 h-5 text-amber-600" />}
                  {activity.status === 'error' && <AlertTriangle className="w-5 h-5 text-red-600" />}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                  <p className="text-sm text-gray-500">{activity.file}</p>
                </div>
              </div>
              <span className="text-sm text-gray-400">{activity.time}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
