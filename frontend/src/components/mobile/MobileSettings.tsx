import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  User,
  Bell,
  Shield,
  Key,
  Database,
  ChevronRight,
  Globe,
  LogOut,
  // Moon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';

interface SettingSection {
  id: string;
  title: string;
  icon: React.ElementType;
  items: {
    label: string;
    value?: string;
    type: 'toggle' | 'link' | 'value';
    checked?: boolean;
  }[];
}

const settingsData: SettingSection[] = [
  {
    id: 'profile',
    title: 'Profile',
    icon: User,
    items: [
      { label: 'Name', value: 'John Doe', type: 'value' },
      { label: 'Email', value: 'john@example.com', type: 'value' },
      { label: 'Company', value: 'Acme Inc.', type: 'value' },
    ],
  },
  {
    id: 'notifications',
    title: 'Notifications',
    icon: Bell,
    items: [
      { label: 'Email notifications', type: 'toggle', checked: true },
      { label: 'Analysis complete', type: 'toggle', checked: true },
      { label: 'New features', type: 'toggle', checked: false },
    ],
  },
  {
    id: 'preferences',
    title: 'Preferences',
    icon: Globe,
    items: [
      { label: 'Dark mode', type: 'toggle', checked: false },
      { label: 'Language', value: 'English', type: 'value' },
    ],
  },
  {
    id: 'security',
    title: 'Security',
    icon: Shield,
    items: [
      { label: 'Change password', type: 'link' },
      { label: 'Two-factor auth', type: 'toggle', checked: false },
    ],
  },
  {
    id: 'api',
    title: 'API Keys',
    icon: Key,
    items: [
      { label: 'Production key', value: 'sk_live_...', type: 'value' },
      { label: 'Generate new key', type: 'link' },
    ],
  },
  {
    id: 'data',
    title: 'Data',
    icon: Database,
    items: [
      { label: 'Export data', type: 'link' },
      { label: 'Clear cache', type: 'link' },
    ],
  },
];

export function MobileSettings() {
  const [expandedSection, setExpandedSection] = useState<string | null>('profile');
  const { user, logout } = useAuth();

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="h-14 bg-white border-b border-gray-200 flex items-center px-4">
        <span className="font-semibold text-gray-900">Settings</span>
      </div>

      {/* User Card */}
      {user && (
        <div className="p-4 bg-white border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center">
              <User className="w-6 h-6 text-indigo-600" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-900">{user.full_name}</p>
              <p className="text-sm text-gray-500">{user.email}</p>
            </div>
          </div>
        </div>
      )}

      {/* Settings List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          {settingsData.map((section) => (
            <motion.div
              key={section.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-xl border border-gray-200 overflow-hidden"
            >
              {/* Section Header */}
              <button
                onClick={() => setExpandedSection(
                  expandedSection === section.id ? null : section.id
                )}
                className="w-full flex items-center gap-3 px-4 py-3"
              >
                <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                  <section.icon className="w-4 h-4 text-gray-600" />
                </div>
                <span className="flex-1 text-left font-medium text-gray-900">
                  {section.title}
                </span>
                <ChevronRight
                  className={cn(
                    'w-5 h-5 text-gray-400 transition-transform',
                    expandedSection === section.id && 'rotate-90'
                  )}
                />
              </button>

              {/* Section Items */}
              {expandedSection === section.id && (
                <div className="border-t border-gray-100">
                  {section.items.map((item, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
                    >
                      <span className="text-sm text-gray-700">{item.label}</span>
                      {item.type === 'toggle' && (
                        <button
                          className={cn(
                            'w-11 h-6 rounded-full transition-colors',
                            item.checked ? 'bg-indigo-600' : 'bg-gray-300'
                          )}
                        >
                          <div
                            className={cn(
                              'w-5 h-5 rounded-full bg-white shadow-sm transition-transform',
                              item.checked ? 'translate-x-5' : 'translate-x-0.5'
                            )}
                          />
                        </button>
                      )}
                      {item.type === 'value' && (
                        <span className="text-sm text-gray-500">{item.value}</span>
                      )}
                      {item.type === 'link' && (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Sign Out Button */}
        <button
          onClick={logout}
          className="w-full mt-6 flex items-center justify-center gap-2 px-4 py-3 bg-red-50 text-red-600 rounded-xl font-medium"
        >
          <LogOut className="w-5 h-5" />
          Sign Out
        </button>

        {/* Version */}
        <p className="text-center text-xs text-gray-400 mt-6">
          Reasoner v1.0.0
        </p>
      </div>
    </div>
  );
}
