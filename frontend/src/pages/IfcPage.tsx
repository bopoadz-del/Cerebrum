import { useState } from 'react';
import { motion } from 'framer-motion';
import { Building2, Box, Layers, Ruler, Info } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AnalysisResult } from '@/types';

const ACCEPTED_FORMATS = ['.ifc', '.ifczip'];
const MAX_FILE_SIZE = 200; // MB

const mockResult: AnalysisResult = {
  id: '1',
  moduleId: 'ifc',
  fileName: 'Building-Model.ifc',
  status: 'completed',
  createdAt: new Date(),
  completedAt: new Date(),
  summary: 'IFC model analysis completed. 15,847 entities across 42 types.',
  details: {
    schema: 'IFC4',
    entities: 15847,
    types: 42,
    relationships: 28456,
    properties: 45623,
    buildingInfo: {
      name: 'Office Building A',
      description: '5-story commercial office building',
      siteArea: '2,500 m²',
      buildingHeight: '22.5 m',
      floors: 5,
      rooms: 156,
    },
    elementCounts: [
      { type: 'IfcWall', count: 487, description: 'Walls' },
      { type: 'IfcDoor', count: 89, description: 'Doors' },
      { type: 'IfcWindow', count: 234, description: 'Windows' },
      { type: 'IfcSlab', count: 45, description: 'Slabs' },
      { type: 'IfcColumn', count: 128, description: 'Columns' },
      { type: 'IfcBeam', count: 256, description: 'Beams' },
      { type: 'IfcRoof', count: 12, description: 'Roofs' },
      { type: 'IfcStair', count: 8, description: 'Stairs' },
    ],
    spaces: [
      { name: 'Lobby', level: 'Ground', area: '450 m²' },
      { name: 'Office Zone A', level: '1-4', area: '1,200 m²' },
      { name: 'Office Zone B', level: '1-4', area: '980 m²' },
      { name: 'Conference Center', level: '2', area: '320 m²' },
      { name: 'Parking', level: 'Basement', area: '1,800 m²' },
    ],
  },
};

export default function IfcPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleUpload = async (_files: File[]) => {
    setIsAnalyzing(true);
    await new Promise((resolve) => setTimeout(resolve, 3000));
    setResult(mockResult);
    setIsAnalyzing(false);
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
          {/* Building Info */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">
                    {((result.details as any)?.buildingInfo as { name: string })?.name}
                  </CardTitle>
                  <p className="text-sm text-gray-500 mt-1">
                    {((result.details as any)?.buildingInfo as { description: string })?.description}
                  </p>
                </div>
                <Badge className="bg-cyan-100 text-cyan-700">
                  {((result.details as any)?.schema as string)}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Site Area</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {((result.details as any)?.buildingInfo as { siteArea: string })?.siteArea}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Building Height</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {((result.details as any)?.buildingInfo as { buildingHeight: string })?.buildingHeight}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Floors</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {((result.details as any)?.buildingInfo as { floors: number })?.floors}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Rooms</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {((result.details as any)?.buildingInfo as { rooms: number })?.rooms}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Content Tabs */}
          <Tabs defaultValue="elements" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="elements">Elements</TabsTrigger>
              <TabsTrigger value="spaces">Spaces</TabsTrigger>
              <TabsTrigger value="stats">Statistics</TabsTrigger>
            </TabsList>

            <TabsContent value="elements">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Element Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {((result.details as any)?.elementCounts as Array<{
                      type: string;
                      count: number;
                      description: string;
                    }>)?.map((element, index) => (
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
                    {((result.details as any)?.spaces as Array<{
                      name: string;
                      level: string;
                      area: string;
                    }>)?.map((space, index) => (
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

            <TabsContent value="stats">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="p-4 flex items-center gap-3">
                    <Box className="w-5 h-5 text-indigo-500" />
                    <div>
                      <p className="text-sm text-gray-500">Entities</p>
                      <p className="font-semibold">{((result.details as any)?.entities as number).toLocaleString()}</p>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4 flex items-center gap-3">
                    <Layers className="w-5 h-5 text-emerald-500" />
                    <div>
                      <p className="text-sm text-gray-500">Types</p>
                      <p className="font-semibold">{(result.details as any)?.types as number}</p>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4 flex items-center gap-3">
                    <Ruler className="w-5 h-5 text-amber-500" />
                    <div>
                      <p className="text-sm text-gray-500">Relationships</p>
                      <p className="font-semibold">
                        {((result.details as any)?.relationships as number).toLocaleString()}
                      </p>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4 flex items-center gap-3">
                    <Info className="w-5 h-5 text-purple-500" />
                    <div>
                      <p className="text-sm text-gray-500">Properties</p>
                      <p className="font-semibold">
                        {((result.details as any)?.properties as number).toLocaleString()}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </div>
  );
}
