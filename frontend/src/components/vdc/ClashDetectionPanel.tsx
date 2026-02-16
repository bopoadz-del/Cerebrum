import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
  Alert,
  AlertTitle,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  Checkbox,
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  CheckCircle as ResolveIcon,
  Block as IgnoreIcon,
  PictureAsPdf as PdfIcon,
  TableChart as ExcelIcon,
  FilterList as FilterIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

interface Clash {
  id: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'new' | 'active' | 'resolved' | 'ignored';
  elementA: {
    name: string;
    type: string;
    discipline: string;
  };
  elementB: {
    name: string;
    type: string;
    discipline: string;
  };
  intersection: {
    volume: number;
    penetrationDepth: number;
  };
  createdAt: string;
  gridLocation?: string;
  level?: string;
}

interface ClashResult {
  id: string;
  runAt: string;
  totalElements: number;
  pairsChecked: number;
  clashCount: number;
  executionTimeMs: number;
  clashes: Clash[];
}

const SEVERITY_COLORS: Record<string, any> = {
  critical: 'error',
  high: 'warning',
  medium: 'info',
  low: 'default',
};

const STATUS_COLORS: Record<string, any> = {
  new: 'error',
  active: 'warning',
  resolved: 'success',
  ignored: 'default',
};

const ClashDetectionPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [clashResult, setClashResult] = useState<ClashResult | null>(null);
  const [selectedClashes, setSelectedClashes] = useState<string[]>([]);
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [clashDetailOpen, setClashDetailOpen] = useState(false);
  const [selectedClash, setSelectedClash] = useState<Clash | null>(null);
  const [filters, setFilters] = useState({
    severity: 'all',
    status: 'all',
    discipline: 'all',
  });
  const [tolerance, setTolerance] = useState(0.001);

  // Mock data for demonstration
  const mockClashes: Clash[] = [
    {
      id: 'clash-001',
      type: 'hard_clash',
      severity: 'critical',
      status: 'new',
      elementA: {
        name: 'Column-C-01',
        type: 'IfcColumn',
        discipline: 'structural',
      },
      elementB: {
        name: 'Wall-W-05',
        type: 'IfcWall',
        discipline: 'architectural',
      },
      intersection: {
        volume: 0.125,
        penetrationDepth: 0.5,
      },
      createdAt: '2024-01-15T10:30:00Z',
      gridLocation: 'C-5',
      level: 'Level 2',
    },
    {
      id: 'clash-002',
      type: 'clearance',
      severity: 'high',
      status: 'active',
      elementA: {
        name: 'Duct-D-12',
        type: 'IfcDistributionElement',
        discipline: 'mep',
      },
      elementB: {
        name: 'Beam-B-08',
        type: 'IfcBeam',
        discipline: 'structural',
      },
      intersection: {
        volume: 0.05,
        penetrationDepth: 0.1,
      },
      createdAt: '2024-01-14T15:20:00Z',
      gridLocation: 'D-8',
      level: 'Level 3',
    },
    {
      id: 'clash-003',
      type: 'hard_clash',
      severity: 'medium',
      status: 'resolved',
      elementA: {
        name: 'Pipe-P-03',
        type: 'IfcDistributionElement',
        discipline: 'mep',
      },
      elementB: {
        name: 'Pipe-P-07',
        type: 'IfcDistributionElement',
        discipline: 'mep',
      },
      intersection: {
        volume: 0.02,
        penetrationDepth: 0.15,
      },
      createdAt: '2024-01-13T09:00:00Z',
      gridLocation: 'E-3',
      level: 'Level 1',
    },
  ];

  const handleRunClashDetection = async () => {
    setLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    setClashResult({
      id: `result-${Date.now()}`,
      runAt: new Date().toISOString(),
      totalElements: 4240,
      pairsChecked: 125000,
      clashCount: mockClashes.length,
      executionTimeMs: 1850,
      clashes: mockClashes,
    });
    
    setLoading(false);
  };

  const handleSelectClash = (clashId: string) => {
    setSelectedClashes(prev =>
      prev.includes(clashId)
        ? prev.filter(id => id !== clashId)
        : [...prev, clashId]
    );
  };

  const handleSelectAll = () => {
    if (selectedClashes.length === filteredClashes.length) {
      setSelectedClashes([]);
    } else {
      setSelectedClashes(filteredClashes.map(c => c.id));
    }
  };

  const handleResolveClash = (clashId: string) => {
    // In production, call API to resolve clash
    console.log('Resolving clash:', clashId);
  };

  const handleIgnoreClash = (clashId: string) => {
    // In production, call API to ignore clash
    console.log('Ignoring clash:', clashId);
  };

  const handleViewClash = (clash: Clash) => {
    setSelectedClash(clash);
    setClashDetailOpen(true);
  };

  const getFilteredClashes = () => {
    if (!clashResult) return [];
    
    return clashResult.clashes.filter(clash => {
      if (filters.severity !== 'all' && clash.severity !== filters.severity) return false;
      if (filters.status !== 'all' && clash.status !== filters.status) return false;
      if (filters.discipline !== 'all' && 
          clash.elementA.discipline !== filters.discipline &&
          clash.elementB.discipline !== filters.discipline) return false;
      return true;
    });
  };

  const filteredClashes = getFilteredClashes();

  const getClashStats = () => {
    if (!clashResult) return { critical: 0, high: 0, medium: 0, low: 0 };
    
    return clashResult.clashes.reduce(
      (stats, clash) => {
        stats[clash.severity]++;
        return stats;
      },
      { critical: 0, high: 0, medium: 0, low: 0 }
    );
  };

  const stats = getClashStats();

  return (
    <Box>
      {/* Header Actions */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            startIcon={<RunIcon />}
            onClick={handleRunClashDetection}
            disabled={loading}
          >
            Run Clash Detection
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRunClashDetection}
            disabled={loading || !clashResult}
          >
            Refresh
          </Button>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<FilterIcon />}
            onClick={() => setFilterDialogOpen(true)}
            disabled={!clashResult}
          >
            Filter
          </Button>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => setSettingsDialogOpen(true)}
          >
            Settings
          </Button>
          <Button
            variant="outlined"
            startIcon={<PdfIcon />}
            disabled={!clashResult}
          >
            Export PDF
          </Button>
          <Button
            variant="outlined"
            startIcon={<ExcelIcon />}
            disabled={!clashResult}
          >
            Export Excel
          </Button>
        </Box>
      </Box>

      {/* Progress */}
      {loading && (
        <Box sx={{ mb: 2 }}>
          <LinearProgress />
          <Typography variant="body2" sx={{ mt: 1 }}>
            Running clash detection...
          </Typography>
        </Box>
      )}

      {/* Results Summary */}
      {clashResult && (
        <>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography color="error" variant="h4">
                    {stats.critical}
                  </Typography>
                  <Typography variant="body2">Critical</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography color="warning.main" variant="h4">
                    {stats.high}
                  </Typography>
                  <Typography variant="body2">High</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography color="info.main" variant="h4">
                    {stats.medium}
                  </Typography>
                  <Typography variant="body2">Medium</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h4">{stats.low}</Typography>
                  <Typography variant="body2">Low</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Alert severity="info" sx={{ mb: 2 }}>
            <AlertTitle>Clash Detection Complete</AlertTitle>
            Checked {clashResult.pairsChecked.toLocaleString()} pairs from{' '}
            {clashResult.totalElements.toLocaleString()} elements in{' '}
            {clashResult.executionTimeMs}ms
          </Alert>

          {/* Clash Table */}
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={
                        selectedClashes.length === filteredClashes.length &&
                        filteredClashes.length > 0
                      }
                      onChange={handleSelectAll}
                    />
                  </TableCell>
                  <TableCell>ID</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Element A</TableCell>
                  <TableCell>Element B</TableCell>
                  <TableCell>Location</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredClashes.map(clash => (
                  <TableRow key={clash.id} hover>
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={selectedClashes.includes(clash.id)}
                        onChange={() => handleSelectClash(clash.id)}
                      />
                    </TableCell>
                    <TableCell>{clash.id}</TableCell>
                    <TableCell>
                      <Chip
                        label={clash.type.replace('_', ' ')}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={clash.severity}
                        color={SEVERITY_COLORS[clash.severity]}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={clash.status}
                        color={STATUS_COLORS[clash.status]}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{clash.elementA.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {clash.elementA.discipline}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{clash.elementB.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {clash.elementB.discipline}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{clash.gridLocation}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {clash.level}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Tooltip title="View">
                        <IconButton
                          size="small"
                          onClick={() => handleViewClash(clash)}
                        >
                          <ViewIcon />
                        </IconButton>
                      </Tooltip>
                      {clash.status !== 'resolved' && (
                        <Tooltip title="Resolve">
                          <IconButton
                            size="small"
                            onClick={() => handleResolveClash(clash.id)}
                          >
                            <ResolveIcon color="success" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {clash.status !== 'ignored' && (
                        <Tooltip title="Ignore">
                          <IconButton
                            size="small"
                            onClick={() => handleIgnoreClash(clash.id)}
                          >
                            <IgnoreIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {/* Filter Dialog */}
      <Dialog open={filterDialogOpen} onClose={() => setFilterDialogOpen(false)}>
        <DialogTitle>Filter Clashes</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Severity</InputLabel>
            <Select
              value={filters.severity}
              onChange={e =>
                setFilters({ ...filters, severity: e.target.value })
              }
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="critical">Critical</MenuItem>
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="low">Low</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filters.status}
              onChange={e =>
                setFilters({ ...filters, status: e.target.value })
              }
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="new">New</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="resolved">Resolved</MenuItem>
              <MenuItem value="ignored">Ignored</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFilterDialogOpen(false)}>Cancel</Button>
          <Button onClick={() => setFilterDialogOpen(false)} variant="contained">
            Apply
          </Button>
        </DialogActions>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog open={settingsDialogOpen} onClose={() => setSettingsDialogOpen(false)}>
        <DialogTitle>Clash Detection Settings</DialogTitle>
        <DialogContent>
          <TextField
            label="Tolerance (meters)"
            type="number"
            value={tolerance}
            onChange={e => setTolerance(parseFloat(e.target.value))}
            fullWidth
            sx={{ mt: 2 }}
            helperText="Minimum distance to consider as clash"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsDialogOpen(false)}>Cancel</Button>
          <Button onClick={() => setSettingsDialogOpen(false)} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Clash Detail Dialog */}
      <Dialog
        open={clashDetailOpen}
        onClose={() => setClashDetailOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Clash Details</DialogTitle>
        <DialogContent>
          {selectedClash && (
            <Box>
              <Typography variant="h6" gutterBottom>
                {selectedClash.id}
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">Element A</Typography>
                  <Typography>{selectedClash.elementA.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedClash.elementA.type} - {selectedClash.elementA.discipline}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">Element B</Typography>
                  <Typography>{selectedClash.elementB.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedClash.elementB.type} - {selectedClash.elementB.discipline}
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Intersection</Typography>
                  <Typography>
                    Volume: {selectedClash.intersection.volume} m³
                  </Typography>
                  <Typography>
                    Penetration: {selectedClash.intersection.penetrationDepth} m
                  </Typography>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClashDetailOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ClashDetectionPanel;
