import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

interface MobileSettingsProps {
  onClose: () => void;
}

export function MobileSettings({ onClose }: MobileSettingsProps) {
  const { user, logout } = useAuth();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-white"
    >
      {/* Header */}
      <div className="h-14 border-b border-gray-200 flex items-center justify-between px-4">
        <h2 className="font-semibold text-gray-900">Settings</h2>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* Content */}
      <div className="p-6 overflow-y-auto h-[calc(100vh-56px)]">
        <div className="space-y-6">
          {/* Profile Section */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Profile</h3>
            <div className="space-y-3">
              <div>
                <label className="text-sm text-gray-600">Name</label>
                <input
                  type="text"
                  defaultValue={user?.full_name || 'John Doe'}
                  className="w-full mt-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-sm text-gray-600">Email</label>
                <input
                  type="email"
                  defaultValue={user?.email || 'john@example.com'}
                  className="w-full mt-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
              </div>
            </div>
          </div>

          {/* Notifications */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Notifications</h3>
            <div className="space-y-2">
              {['Email notifications', 'Analysis complete alerts', 'New features'].map((item) => (
                <label key={item} className="flex items-center justify-between py-2">
                  <span className="text-sm text-gray-700">{item}</span>
                  <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-gray-300" />
                </label>
              ))}
            </div>
          </div>

          {/* API Keys */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">API Keys</h3>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between">
                <code className="text-sm text-gray-600">sk_live_xxxxxxxxxxxx</code>
                <Button variant="outline" size="sm">Copy</Button>
              </div>
            </div>
          </div>

          {/* Sign Out */}
          <div className="pt-4 border-t border-gray-200">
            <Button 
              variant="destructive" 
              className="w-full"
              onClick={() => {
                logout();
                onClose();
              }}
            >
              Sign Out
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
