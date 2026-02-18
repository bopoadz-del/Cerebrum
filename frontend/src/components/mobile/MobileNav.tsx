import { MessageSquare, FileText, Folder, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MobileNavProps {
  activeTab: 'projects' | 'chat' | 'outcomes' | 'settings';
  onTabChange: (tab: 'projects' | 'chat' | 'outcomes' | 'settings') => void;
}

const navItems = [
  { id: 'projects' as const, label: 'Projects', icon: Folder },
  { id: 'chat' as const, label: 'Chat', icon: MessageSquare },
  { id: 'outcomes' as const, label: 'Outcomes', icon: FileText },
  { id: 'settings' as const, label: 'Settings', icon: Settings },
];

export function MobileNav({ activeTab, onTabChange }: MobileNavProps) {
  return (
    <nav className="h-16 bg-white border-t border-gray-200 flex items-center justify-around px-2">
      {navItems.map((item) => (
        <button
          key={item.id}
          onClick={() => onTabChange(item.id)}
          className={cn(
            'flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors',
            activeTab === item.id
              ? 'text-indigo-600'
              : 'text-gray-500'
          )}
        >
          <item.icon className={cn(
            'w-5 h-5',
            activeTab === item.id && 'fill-current'
          )} />
          <span className="text-xs font-medium">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
