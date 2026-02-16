import React, { useState } from 'react';
import {
  Monitor,
  Wifi,
  WifiOff,
  Battery,
  BatteryLow,
  BatteryMedium,
  BatteryFull,
  MapPin,
  Settings,
  RefreshCw,
  MoreVertical,
  Plus,
  Search,
  Filter,
  AlertTriangle,
  CheckCircle,
  Signal,
  SignalLow,
  SignalMedium,
  SignalHigh,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface EdgeDevice {
  id: string;
  name: string;
  type: 'camera' | 'sensor' | 'gateway' | 'drone';
  status: 'online' | 'offline' | 'warning';
  batteryLevel: number;
  signalStrength: number;
  location: string;
  lastSeen: Date;
  firmware: string;
  temperature?: number;
  ipAddress: string;
}

const mockDevices: EdgeDevice[] = [
  {
    id: 'CAM-001',
    name: 'Site Camera A1',
    type: 'camera',
    status: 'online',
    batteryLevel: 85,
    signalStrength: 92,
    location: 'Building A - North',
    lastSeen: new Date(Date.now() - 1000 * 60 * 2),
    firmware: 'v2.4.1',
    temperature: 42,
    ipAddress: '192.168.1.101',
  },
  {
    id: 'SNS-002',
    name: 'Environmental Sensor B2',
    type: 'sensor',
    status: 'online',
    batteryLevel: 62,
    signalStrength: 78,
    location: 'Building B - East',
    lastSeen: new Date(Date.now() - 1000 * 60 * 5),
    firmware: 'v1.8.3',
    temperature: 35,
    ipAddress: '192.168.1.102',
  },
  {
    id: 'GTW-003',
    name: 'Gateway Hub C1',
    type: 'gateway',
    status: 'warning',
    batteryLevel: 100,
    signalStrength: 45,
    location: 'Site Office',
    lastSeen: new Date(Date.now() - 1000 * 60 * 15),
    firmware: 'v3.1.0',
    ipAddress: '192.168.1.1',
  },
  {
    id: 'DRN-004',
    name: 'Survey Drone D1',
    type: 'drone',
    status: 'offline',
    batteryLevel: 12,
    signalStrength: 0,
    location: 'Charging Station',
    lastSeen: new Date(Date.now() - 1000 * 60 * 60 * 2),
    firmware: 'v2.0.5',
    ipAddress: '192.168.1.104',
  },
  {
    id: 'CAM-005',
    name: 'Safety Camera E3',
    type: 'camera',
    status: 'online',
    batteryLevel: 95,
    signalStrength: 88,
    location: 'Building E - South',
    lastSeen: new Date(Date.now() - 1000 * 30),
    firmware: 'v2.4.1',
    temperature: 38,
    ipAddress: '192.168.1.105',
  },
];

const EdgeDevices: React.FC = () => {
  const [devices, setDevices] = useState<EdgeDevice[]>(mockDevices);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedDevice, setSelectedDevice] = useState<EdgeDevice | null>(null);

  const filteredDevices = devices.filter((device) => {
    const matchesSearch =
      device.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      device.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      device.location.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || device.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const stats = {
    total: devices.length,
    online: devices.filter((d) => d.status === 'online').length,
    offline: devices.filter((d) => d.status === 'offline').length,
    warning: devices.filter((d) => d.status === 'warning').length,
  };

  const getStatusIcon = (status: EdgeDevice['status']) => {
    switch (status) {
      case 'online':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'offline':
        return <WifiOff size={16} className="text-red-500" />;
      case 'warning':
        return <AlertTriangle size={16} className="text-yellow-500" />;
    }
  };

  const getStatusColor = (status: EdgeDevice['status']) => {
    switch (status) {
      case 'online':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400';
      case 'offline':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400';
      case 'warning':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400';
    }
  };

  const getBatteryIcon = (level: number) => {
    if (level >= 75) return <BatteryFull size={16} className="text-green-500" />;
    if (level >= 40) return <BatteryMedium size={16} className="text-yellow-500" />;
    return <BatteryLow size={16} className="text-red-500" />;
  };

  const getSignalIcon = (strength: number) => {
    if (strength >= 80) return <SignalHigh size={16} className="text-green-500" />;
    if (strength >= 50) return <SignalMedium size={16} className="text-yellow-500" />;
    if (strength > 0) return <SignalLow size={16} className="text-red-500" />;
    return <Signal size={16} className="text-gray-400" />;
  };

  const getTypeIcon = (type: EdgeDevice['type']) => {
    switch (type) {
      case 'camera':
        return <Monitor size={18} className="text-blue-500" />;
      case 'sensor':
        return <Signal size={18} className="text-green-500" />;
      case 'gateway':
        return <Wifi size={18} className="text-purple-500" />;
      case 'drone':
        return <MapPin size={18} className="text-orange-500" />;
    }
  };

  const formatLastSeen = (date: Date): string => {
    const minutes = Math.floor((Date.now() - date.getTime()) / (1000 * 60));
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Edge Devices</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Monitor and manage connected devices
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium">
            <Plus size={18} />
            Add Device
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Devices', value: stats.total, color: 'blue' },
          { label: 'Online', value: stats.online, color: 'green' },
          { label: 'Offline', value: stats.offline, color: 'red' },
          { label: 'Warning', value: stats.warning, color: 'yellow' },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4"
          >
            <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search devices..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
          >
            <option value="all">All Status</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
            <option value="warning">Warning</option>
          </select>
          <button className="inline-flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
            <Filter size={18} />
            Filter
          </button>
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
            <RefreshCw size={18} className="text-gray-500" />
          </button>
        </div>
      </div>

      {/* Devices Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDevices.map((device) => (
          <div
            key={device.id}
            onClick={() => setSelectedDevice(device)}
            className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5 hover:border-blue-300 dark:hover:border-blue-700 transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  {getTypeIcon(device.type)}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{device.name}</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{device.id}</p>
                </div>
              </div>
              <span
                className={cn(
                  'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full',
                  getStatusColor(device.status)
                )}
              >
                {getStatusIcon(device.status)}
                {device.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                {getBatteryIcon(device.batteryLevel)}
                <span>{device.batteryLevel}%</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                {getSignalIcon(device.signalStrength)}
                <span>{device.signalStrength > 0 ? `${device.signalStrength}%` : 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <MapPin size={16} />
                <span className="truncate">{device.location}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <Wifi size={16} />
                <span className="font-mono text-xs">{device.ipAddress}</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Last seen {formatLastSeen(device.lastSeen)}
              </span>
              <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                <MoreVertical size={16} className="text-gray-400" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Device Detail Modal */}
      {selectedDevice && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                  {getTypeIcon(selectedDevice.type)}
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {selectedDevice.name}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {selectedDevice.id}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDevice(null)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Status</p>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full mt-1',
                      getStatusColor(selectedDevice.status)
                    )}
                  >
                    {getStatusIcon(selectedDevice.status)}
                    {selectedDevice.status}
                  </span>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Battery</p>
                  <div className="flex items-center gap-2 mt-1">
                    {getBatteryIcon(selectedDevice.batteryLevel)}
                    <span className="font-medium text-gray-900 dark:text-white">
                      {selectedDevice.batteryLevel}%
                    </span>
                  </div>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Signal Strength</p>
                  <div className="flex items-center gap-2 mt-1">
                    {getSignalIcon(selectedDevice.signalStrength)}
                    <span className="font-medium text-gray-900 dark:text-white">
                      {selectedDevice.signalStrength > 0 ? `${selectedDevice.signalStrength}%` : 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Temperature</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {selectedDevice.temperature ? `${selectedDevice.temperature}°C` : 'N/A'}
                  </p>
                </div>
              </div>

              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <p className="text-xs text-gray-500 dark:text-gray-400">Location</p>
                <p className="font-medium text-gray-900 dark:text-white">{selectedDevice.location}</p>
              </div>

              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <p className="text-xs text-gray-500 dark:text-gray-400">Network</p>
                <p className="font-medium text-gray-900 dark:text-white font-mono">
                  {selectedDevice.ipAddress}
                </p>
              </div>

              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <p className="text-xs text-gray-500 dark:text-gray-400">Firmware</p>
                <p className="font-medium text-gray-900 dark:text-white">{selectedDevice.firmware}</p>
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">
                <Settings size={18} />
                Configure
              </button>
              <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800">
                <RefreshCw size={18} />
                Reboot
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EdgeDevices;
