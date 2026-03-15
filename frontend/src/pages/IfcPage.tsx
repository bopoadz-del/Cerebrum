import { useState } from 'react';
import { motion } from 'framer-motion';
import { Building2, Box, Layers } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { STORAGE_KEYS } from '@/context/AuthContext';

const ACCEPTED_FORMATS = ['.ifc', '.ifczip'];
const MAX_FILE_SIZE = 500; // MB

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

interface IFCResult {
  file_id: string;
  filename: string;
  status: string;
  schema?: string;
  entities?: number;
  element_counts?: Array<{ type: string; count: number; description: string }>;
  spaces?: Array<{ name: string; level: string; area: string }>;
  building_info?: {
    name: string;
    description: string;
    site_area?: string;
    building_height?: string;
    floors?: number;
    rooms?: number;
  };
}

export default function IfcPage() {
  const [result, setResult] = useState<IFCResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (files: File[]) => {
    if (files.length === 0) return;
    
    setIsAnalyzing(true);
    setError(null);
    setResult(null);
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      
      // Upload file
      const uploadResponse = await fetch(`${API_BASE}/bim/upload`, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: formData,
      });
      
      if (!uploadResponse.ok) {
        const err = await uploadResponse.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed: ${uploadResponse.status}`);
      }
      
      const uploadData = await uploadResponse.json();
      
      // Get element counts
      const elementsResponse = await fetch(`${API_BASE}/bim/files/${uploadData.file_id}/elements`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' },
      });
      
      const elementsData = elementsResponse.ok ? await elementsResponse.json() : { elements: [] };
      
      // Get rooms/spaces
      const roomsResponse = await fetch(`${API_BASE}/bim/files/${uploadData.file_id}/rooms`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' },
      });
      
      const roomsData = roomsResponse.ok ? await roomsResponse.json() : { rooms: [] };
      
      // Transform to display format
      const elementCounts = elementsData.elements?.reduce((acc: any, el: any) => {
        const type = el.type || 'Unknown';
        acc[type] = (acc[type] || 0) + 1;
        return acc;
      }, {});
      
      setResult({
        file_id: uploadData.file_id,
        filename: file.name,
        status: 'completed',
        entities: elementsData.elements?.length || 0,
        element_counts: Object.entries(elementCounts || {}).map(([type, count]) => ({
          type,
          count: count as number,
          description: type.replace('Ifc', ''),
        })),
        spaces: roomsData.rooms?.map((r: any) => ({
          name: r.name || 'Unnamed',
          level: r.level || 'Unknown',
          area: r.area ? `${r.area} m²` : 'N/A',
        })),
      });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process IFC file');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="IFC Analysis"
        description="Analyze Building Information Modeling (BIM) files"
        icon={Building2}
        iconColor="cyan"
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <FileUpload
          acceptedFormats={ACCEPTED_FORMATS}
          maxFileSize={MAX_FILE_SIZE}
          onUpload={handleUpload}
        />
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6"
        >
          <p className="text-red-600">{error}</p>
        </motion.div>
      )}

      {isAnalyzing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-12"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-gray-600">Parsing IFC model...</span>
          </div>
        </motion.div>
      )}

      {result && !isAnalyzing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* File Info */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">{result.filename}</CardTitle>
                  <p className="text-sm text-gray-500 mt-1">IFC Model Analysis</p>
                </div>
                <Badge className="bg-cyan-100 text-cyan-700">{result.status}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Total Entities</p>
                  <p className="text-lg font-semibold text-gray-900">{result.entities?.toLocaleString()}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Element Types</p>
                  <p className="text-lg font-semibold text-gray-900">{result.element_counts?.length || 0}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Spaces</p>
                  <p className="text-lg font-semibold text-gray-900">{result.spaces?.length || 0}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">File ID</p>
                  <p className="text-lg font-semibold text-gray-900 truncate">{result.file_id?.slice(0, 8)}...</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Content Tabs */}
          <Tabs defaultValue="elements" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="elements">Elements</TabsTrigger>
              <TabsTrigger value="spaces">Spaces</TabsTrigger>
            </TabsList>

            <TabsContent value="elements">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Element Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {result.element_counts?.map((element, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-cyan-50 flex items-center justify-center">
                            <Box className="w-5 h-5 text-cyan-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{element.description}</p>
                            <p className="text-sm text-gray-500">{element.type}</p>
                          </div>
                        </div>
                        <Badge variant="outline" className="text-lg px-3">
                          {element.count.toLocaleString()}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="spaces">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Spaces</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {result.spaces?.map((space, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
                            <Layers className="w-5 h-5 text-indigo-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{space.name}</p>
                            <p className="text-sm text-gray-500">{space.level}</p>
                          </div>
                        </div>
                        <Badge variant="outline">{space.area}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </div>
  );
}
