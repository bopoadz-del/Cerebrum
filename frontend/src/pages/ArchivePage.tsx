import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Archive, Search, FileText, Image as ImageIcon, FileDigit } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { STORAGE_KEYS } from '@/context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

interface ArchivedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  created_at: string;
}

export default function ArchivePage() {
  const [files, setFiles] = useState<ArchivedFile[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
        const response = await fetch(`${API_BASE}/documents`, {
          headers: { 'Authorization': token ? `Bearer ${token}` : '' },
        });
        
        if (!response.ok) throw new Error('Failed to fetch files');
        
        const data = await response.json();
        setFiles(data.documents || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load files');
        setFiles([]);
      } finally {
        setLoading(false);
      }
    };

    fetchFiles();
  }, []);

  const filteredFiles = files.filter((file) =>
    file.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getFileIcon = (type: string) => {
    if (type.includes('pdf')) return <FileText className="w-5 h-5 text-red-500" />;
    if (type.includes('image')) return <ImageIcon className="w-5 h-5 text-blue-500" />;
    return <FileDigit className="w-5 h-5 text-gray-500" />;
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="Archive"
        description="Browse and search archived files"
        icon={Archive}
        iconColor="gray"
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </motion.div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredFiles.map((file) => (
            <Card key={file.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  {getFileIcon(file.type)}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {(file.size / 1024).toFixed(1)} KB • {new Date(file.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!loading && filteredFiles.length === 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-12">
          <Archive className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No files found</p>
        </motion.div>
      )}
    </div>
  );
}
