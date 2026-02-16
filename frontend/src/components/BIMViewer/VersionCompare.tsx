"""
VersionCompare.tsx - Diff view between BIM model versions
"""

import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Divider,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  Compare as CompareIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  Download as DownloadIcon,
  ChevronRight as ChevronRightIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';

// Types
interface ModelVersion {
  id: string;
  version: string;
  date: string;
  author: string;
  description: string;
  elementCount: number;
}

interface Change {
  id: string;
  globalId: string;
  elementType: string;
  name: string;
  changeType: 'added' | 'removed' | 'modified' | 'unchanged';
  properties?: {
    added: string[];
    removed: string[];
    modified: Array<{ property: string; oldValue: any; newValue: any }>;
  };
  geometryChanged: boolean;
  positionChanged: boolean;
}

interface VersionCompareProps {
  versions: ModelVersion[];
  baseVersion?: string;
  compareVersion?: string;
  onVersionSelect?: (baseId: string, compareId: string) => void;
  onChangeSelect?: (change: Change) => void;
  onExport?: (changes: Change[]) => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index} style={{ height: '100%', overflow: 'auto' }}>
    {value === index && <Box sx={{ p: 2 }}>{children}</Box>}
  </div>
);

const CHANGE_TYPE_COLORS: Record<string, string> = {
  added: 'success',
  removed: 'error',
  modified: 'warning',
  unchanged: 'default',
};

const CHANGE_TYPE_ICONS: Record<string, React.ElementType> = {
  added: AddIcon,
  removed: RemoveIcon,
  modified: EditIcon,
  unchanged: ChevronRightIcon,
};

export const VersionCompare: React.FC<VersionCompareProps> = ({
  versions,
  baseVersion,
  compareVersion,
  onVersionSelect,
  onChangeSelect,
  onExport,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedBase, setSelectedBase] = useState(baseVersion || '');
  const [selectedCompare, setSelectedCompare] = useState(compareVersion || '');
  const [isComparing, setIsComparing] = useState(false);
  const [changes, setChanges] = useState<Change[]>([]);
  const [filter, setFilter] = useState<string[]>(['added', 'removed', 'modified']);

  const handleCompare = useCallback(async () => {
    if (!selectedBase || !selectedCompare) return;

    setIsComparing(true);

    try {
      // This would call the API to get comparison results
      // For now, simulate with mock data
      await new Promise((resolve) => setTimeout(resolve, 2000));

      const mockChanges: Change[] = [
        {
          id: '1',
          globalId: 'abc123',
          elementType: 'IfcWall',
          name: 'Wall-001',
          changeType: 'added',
          geometryChanged: true,
          positionChanged: false,
        },
        {
          id: '2',
          globalId: 'def456',
          elementType: 'IfcDoor',
          name: 'Door-002',
          changeType: 'modified',
          properties: {
            added: ['FireRating'],
            removed: [],
            modified: [{ property: 'Height', oldValue: 2100, newValue: 2400 }],
          },
          geometryChanged: false,
          positionChanged: true,
        },
        {
          id: '3',
          globalId: 'ghi789',
          elementType: 'IfcWindow',
          name: 'Window-003',
          changeType: 'removed',
          geometryChanged: true,
          positionChanged: false,
        },
      ];

      setChanges(mockChanges);
      onVersionSelect?.(selectedBase, selectedCompare);
    } finally {
      setIsComparing(false);
    }
  }, [selectedBase, selectedCompare, onVersionSelect]);

  const filteredChanges = changes.filter((change) => filter.includes(change.changeType));

  const changeStats = {
    added: changes.filter((c) => c.changeType === 'added').length,
    removed: changes.filter((c) => c.changeType === 'removed').length,
    modified: changes.filter((c) => c.changeType === 'modified').length,
    unchanged: changes.filter((c) => c.changeType === 'unchanged').length,
  };

  const toggleFilter = (type: string) => {
    setFilter((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom>
          Version Compare
        </Typography>

        {/* Version Selection */}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Base Version</InputLabel>
            <Select
              value={selectedBase}
              onChange={(e) => setSelectedBase(e.target.value)}
              label="Base Version"
              size="small"
            >
              {versions.map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.version} - {v.date}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <CompareIcon color="action" />

          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Compare Version</InputLabel>
            <Select
              value={selectedCompare}
              onChange={(e) => setSelectedCompare(e.target.value)}
              label="Compare Version"
              size="small"
            >
              {versions.map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.version} - {v.date}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="contained"
            startIcon={<CompareIcon />}
            onClick={handleCompare}
            disabled={!selectedBase || !selectedCompare || isComparing}
          >
            {isComparing ? 'Comparing...' : 'Compare'}
          </Button>
        </Box>

        {/* Progress */}
        {isComparing && <LinearProgress sx={{ mt: 2 }} />}
      </Box>

      {/* Results */}
      {changes.length > 0 && (
        <>
          {/* Stats */}
          <Box sx={{ px: 2, py: 1, bgcolor: 'grey.50' }}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip
                icon={<AddIcon />}
                label={`${changeStats.added} Added`}
                color="success"
                size="small"
                onClick={() => toggleFilter('added')}
                variant={filter.includes('added') ? 'filled' : 'outlined'}
              />
              <Chip
                icon={<RemoveIcon />}
                label={`${changeStats.removed} Removed`}
                color="error"
                size="small"
                onClick={() => toggleFilter('removed')}
                variant={filter.includes('removed') ? 'filled' : 'outlined'}
              />
              <Chip
                icon={<EditIcon />}
                label={`${changeStats.modified} Modified`}
                color="warning"
                size="small"
                onClick={() => toggleFilter('modified')}
                variant={filter.includes('modified') ? 'filled' : 'outlined'}
              />
              <Box sx={{ flexGrow: 1 }} />
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                size="small"
                onClick={() => onExport?.(changes)}
              >
                Export
              </Button>
            </Box>
          </Box>

          {/* Tabs */}
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="scrollable"
          >
            <Tab label="Changes List" />
            <Tab label="Property Changes" />
            <Tab label="Geometry Changes" />
          </Tabs>

          {/* Changes List Tab */}
          <TabPanel value={activeTab} index={0}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Element</TableCell>
                    <TableCell>Change</TableCell>
                    <TableCell>Geometry</TableCell>
                    <TableCell>Position</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredChanges.map((change) => {
                    const ChangeIcon = CHANGE_TYPE_ICONS[change.changeType];
                    return (
                      <TableRow
                        key={change.id}
                        hover
                        onClick={() => onChangeSelect?.(change)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>
                          <Chip
                            icon={<ChangeIcon />}
                            label={change.changeType}
                            color={CHANGE_TYPE_COLORS[change.changeType] as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">{change.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {change.elementType}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {change.changeType === 'modified' && change.properties && (
                            <Box>
                              {change.properties.modified.map((mod) => (
                                <Typography key={mod.property} variant="caption" display="block">
                                  {mod.property}: {mod.oldValue} → {mod.newValue}
                                </Typography>
                              ))}
                            </Box>
                          )}
                        </TableCell>
                        <TableCell>
                          {change.geometryChanged ? (
                            <Chip label="Changed" color="warning" size="small" />
                          ) : (
                            <Chip label="Same" size="small" variant="outlined" />
                          )}
                        </TableCell>
                        <TableCell>
                          {change.positionChanged ? (
                            <Chip label="Moved" color="warning" size="small" />
                          ) : (
                            <Chip label="Same" size="small" variant="outlined" />
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </TabPanel>

          {/* Property Changes Tab */}
          <TabPanel value={activeTab} index={1}>
            {filteredChanges
              .filter((c) => c.changeType === 'modified' && c.properties)
              .map((change) => (
                <Box key={change.id} sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">{change.name}</Typography>
                  {change.properties?.modified.map((mod) => (
                    <Box key={mod.property} sx={{ ml: 2, my: 1 }}>
                      <Typography variant="body2">{mod.property}</Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          label={String(mod.oldValue)}
                          size="small"
                          color="error"
                          variant="outlined"
                        />
                        <ChevronRightIcon />
                        <Chip
                          label={String(mod.newValue)}
                          size="small"
                          color="success"
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                  ))}
                  <Divider sx={{ my: 1 }} />
                </Box>
              ))}
          </TabPanel>

          {/* Geometry Changes Tab */}
          <TabPanel value={activeTab} index={2}>
            <List>
              {filteredChanges
                .filter((c) => c.geometryChanged || c.positionChanged)
                .map((change) => (
                  <ListItem key={change.id}>
                    <ListItemIcon>
                      {change.geometryChanged ? <EditIcon color="warning" /> : <CompareIcon />}
                    </ListItemIcon>
                    <ListItemText
                      primary={change.name}
                      secondary={
                        <Box>
                          {change.geometryChanged && (
                            <Chip label="Geometry Changed" size="small" color="warning" sx={{ mr: 1 }} />
                          )}
                          {change.positionChanged && (
                            <Chip label="Position Changed" size="small" color="info" />
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
            </List>
          </TabPanel>
        </>
      )}
    </Paper>
  );
};

export default VersionCompare;
