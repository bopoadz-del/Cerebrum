import React, { useState } from 'react';
import {
  Key,
  Webhook,
  Bell,
  Shield,
  User,
  Globe,
  Database,
  Save,
  Copy,
  Eye,
  EyeOff,
  Plus,
  Trash2,
  Check,
  X,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface ApiKey {
  id: string;
  name: string;
  key: string;
  createdAt: Date;
  lastUsed?: Date;
  permissions: string[];
}

interface WebhookConfig {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  secret?: string;
}

const mockApiKeys: ApiKey[] = [
  {
    id: '1',
    name: 'Production API Key',
    key: 'sk_live_xxxxxxxxxxxxxxxxxxxx',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30),
    lastUsed: new Date(Date.now() - 1000 * 60 * 5),
    permissions: ['read', 'write'],
  },
  {
    id: '2',
    name: 'Development API Key',
    key: 'sk_test_yyyyyyyyyyyyyyyyyyyy',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
    lastUsed: new Date(Date.now() - 1000 * 60 * 60),
    permissions: ['read'],
  },
];

const mockWebhooks: WebhookConfig[] = [
  {
    id: '1',
    url: 'https://api.example.com/webhooks/cerebrum',
    events: ['model.completed', 'pipeline.failed'],
    active: true,
    secret: 'whsec_xxxxxxxxxxxxxxxx',
  },
];

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'api' | 'webhooks' | 'notifications' | 'security'>('api');
  const [apiKeys, setApiKeys] = useState<ApiKey[]>(mockApiKeys);
  const [webhooks, setWebhooks] = useState<WebhookConfig[]>(mockWebhooks);
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});
  const [newKeyName, setNewKeyName] = useState('');
  const [newWebhookUrl, setNewWebhookUrl] = useState('');

  const generateApiKey = () => {
    if (!newKeyName.trim()) return;
    
    const newKey: ApiKey = {
      id: `${apiKeys.length + 1}`,
      name: newKeyName,
      key: `sk_live_${Math.random().toString(36).substring(2, 15)}`,
      createdAt: new Date(),
      permissions: ['read'],
    };
    
    setApiKeys([...apiKeys, newKey]);
    setNewKeyName('');
  };

  const deleteApiKey = (id: string) => {
    setApiKeys(apiKeys.filter((k) => k.id !== id));
  };

  const addWebhook = () => {
    if (!newWebhookUrl.trim()) return;
    
    const newWebhook: WebhookConfig = {
      id: `${webhooks.length + 1}`,
      url: newWebhookUrl,
      events: ['model.completed'],
      active: true,
      secret: `whsec_${Math.random().toString(36).substring(2, 15)}`,
    };
    
    setWebhooks([...webhooks, newWebhook]);
    setNewWebhookUrl('');
  };

  const deleteWebhook = (id: string) => {
    setWebhooks(webhooks.filter((w) => w.id !== id));
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const tabs = [
    { id: 'api', label: 'API Keys', icon: Key },
    { id: 'webhooks', label: 'Webhooks', icon: Webhook },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
  ];

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <Breadcrumb className="mb-2" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Manage your API keys, webhooks, and preferences
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-800">
        <div className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={cn(
                'flex items-center gap-2 pb-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        {activeTab === 'api' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  API Keys
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Manage API keys for programmatic access
                </p>
              </div>
            </div>

            {/* Generate new key */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Key name..."
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
              />
              <button
                onClick={generateApiKey}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
              >
                <Plus size={16} />
                Generate Key
              </button>
            </div>

            {/* API Keys List */}
            <div className="space-y-3">
              {apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {key.name}
                      </h4>
                      <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-xs rounded-full">
                        Active
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                        {showKey[key.id]
                          ? key.key
                          : `${key.key.substring(0, 12)}...`}
                      </code>
                      <button
                        onClick={() =>
                          setShowKey((prev) => ({ ...prev, [key.id]: !prev[key.id] }))
                        }
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                      >
                        {showKey[key.id] ? (
                          <EyeOff size={14} className="text-gray-500" />
                        ) : (
                          <Eye size={14} className="text-gray-500" />
                        )}
                      </button>
                      <button
                        onClick={() => copyToClipboard(key.key)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                      >
                        <Copy size={14} className="text-gray-500" />
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Created {key.createdAt.toLocaleDateString()}
                      {key.lastUsed && ` · Last used ${key.lastUsed.toLocaleDateString()}`}
                    </p>
                  </div>
                  <button
                    onClick={() => deleteApiKey(key.id)}
                    className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg text-red-500"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'webhooks' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Webhooks
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Configure webhook endpoints for event notifications
              </p>
            </div>

            {/* Add new webhook */}
            <div className="flex gap-2">
              <input
                type="url"
                placeholder="https://your-endpoint.com/webhook"
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
              />
              <button
                onClick={addWebhook}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
              >
                <Plus size={16} />
                Add Webhook
              </button>
            </div>

            {/* Webhooks List */}
            <div className="space-y-3">
              {webhooks.map((webhook) => (
                <div
                  key={webhook.id}
                  className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className={cn(
                          'w-2 h-2 rounded-full',
                          webhook.active ? 'bg-green-500' : 'bg-gray-400'
                        )}
                      />
                      <span className="font-medium text-gray-900 dark:text-white">
                        {webhook.url}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyToClipboard(webhook.secret || '')}
                        className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg"
                        title="Copy secret"
                      >
                        <Copy size={16} className="text-gray-500" />
                      </button>
                      <button
                        onClick={() => deleteWebhook(webhook.id)}
                        className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg text-red-500"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {webhook.events.map((event) => (
                      <span
                        key={event}
                        className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 text-xs rounded"
                      >
                        {event}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Notification Preferences
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Choose how you want to be notified
              </p>
            </div>

            <div className="space-y-4">
              {[
                { label: 'Pipeline completions', default: true },
                { label: 'Model training finished', default: true },
                { label: 'System alerts', default: true },
                { label: 'New team member invitations', default: false },
                { label: 'Weekly summary reports', default: false },
              ].map((item) => (
                <label
                  key={item.label}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg cursor-pointer"
                >
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {item.label}
                  </span>
                  <input
                    type="checkbox"
                    defaultChecked={item.default}
                    className="w-4 h-4 text-blue-600 rounded border-gray-300"
                  />
                </label>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Security Settings
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Manage your account security
              </p>
            </div>

            <div className="space-y-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      Two-Factor Authentication
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Add an extra layer of security to your account
                    </p>
                  </div>
                  <button className="px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800">
                    Enable
                  </button>
                </div>
              </div>

              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      Session Management
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Manage your active sessions
                    </p>
                  </div>
                  <button className="px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800">
                    View Sessions
                  </button>
                </div>
              </div>

              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      Change Password
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Update your account password
                    </p>
                  </div>
                  <button className="px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800">
                    Change
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;
