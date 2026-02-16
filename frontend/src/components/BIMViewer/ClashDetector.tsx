
import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Slider,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Divider,
  LinearProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  ZoomIn as ZoomIcon,
  FilterList as FilterIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';

// Types
interface Clash {
  id: string;
  element1: {
    global_id: string;
    name: string;
    type: string;
  };
  element2: {
    global_id: string;
    name: string;
    type: string;
  };
  overlap_volume: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'new' | 'acknowledged' | 'resolved' | 'ignored';
}

interface ClashDetectorProps {
  fileId: string;
  onClashSelect?: (clash: Clash) => void;
  onRunDetection?: (tolerance: number, selectedTypes: string[]) => Promise<Clash[]>;
  elementTypes?: string[];
}

interface ClashFilter {
  severity: string[];
  status: string[];
  elementTypes: string[];
}

const SEVERITY_COLORS: Record<string, string> = {
  low: 'success',
  medium: 'warning',
  high: 'error',
  critical: 'error',
};

const STATUS_COLORS: Record<string, string> = {
  new: 'error',
  acknowledged: 'warning',
  resolved: 'success',
  ignored: 'default',
};

export const ClashDetector: React.FC<ClashDetectorProps> = ({
  fileId,
  onClashSelect,
  onRunDetection,
  elementTypes = [],
}) => {
  const [clashes, setClashes] = useState<Clash[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [tolerance, setTolerance] = useState(0.001);
  const [progress, setProgress] = useState(0);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [filter, setFilter] = useState<ClashFilter>({
    severity: ['low', 'medium', 'high', 'critical'],
    status: ['new', 'acknowledged'],
    elementTypes: [],
  });
  const [showFilterDialog, setShowFilterDialog] = useState(false);
  const [selectedClash, setSelectedClash] = useState<Clash | null>(null);

  const handleRunDetection = useCallback(async () => {
    if (!onRunDetection) return;

    setIsRunning(true);
    setProgress(0);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 500);

      const results = await onRunDetection(tolerance, selectedTypes);

      clearInterval(progressInterval);
      setProgress(100);
      setClashes(results);
    } catch (error) {
      console.error('Clash detection failed:', error);
    } finally {
      setIsRunning(false);
    }
  }, [onRunDetection, tolerance, selectedTypes]);

  const handleClashClick = useCallback((clash: Clash) => {
    setSelectedClash(clash);
    onClashSelect?.(clash);
  }, [onClashSelect]);

  const handleStatusChange = useCallback((clashId: string, newStatus: Clash['status']) => {
    setClashes((prev) =>
      prev.map((c) => (c.id === clashId ? { ...c, status: newStatus } : c))
    );
  }, []);

  const filteredClashes = clashes.filter((clash) => {
    return (
      filter.severity.includes(clash.severity) &&
      filter.status.includes(clash.status) &&
      (filter.elementTypes.length === 0 ||
        filter.elementTypes.includes(clash.element1.type) ||
        filter.elementTypes.includes(clash.element2.type))
    );
  });

  const clashStats = {
    total: clashes.length,
    critical: clashes.filter((c) => c.severity === 'critical').length,
    high: clashes.filter((c) => c.severity === 'high').length,
    medium: clashes.filter((c) => c.severity === 'medium').length,
    low: clashes.filter((c) => c.severity === 'low').length,
    new: clashes.filter((c) => c.status === 'new').length,
    resolved: clashes.filter((c) => c.status === 'resolved').length,
  };

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom>
          Clash Detection
        </Typography>

        {/* Stats */}
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          <Chip
            icon={<ErrorIcon />}
            label={`${clashStats.critical} Critical`}
            color="error"
            size="small"
          />
          <Chip
            icon={<WarningIcon />}
            label={`${clashStats.high} High`}
            color="warning"
            size="small"
          />
          <Chip
            label={`${clashStats.medium} Medium`}
            color="info"
            size="small"
          />
          <Chip
            icon={<CheckCircleIcon />}
            label={`${clashStats.low} Low`}
            color="success"
            size="small"
          />
        </Box>

        {/* Controls */}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <Box sx={{ minWidth: 200 }}>
            <Typography variant="caption" gutterBottom>
              Tolerance: {(tolerance * 1000).toFixed(1)} mm
            </Typography>
            <Slider
              value={tolerance}
              min={0.0001}
              max={0.01}
              step={0.0001}
              onChange={(_, value) => setTolerance(value as number)}
              disabled={isRunning}
            />
          </Box>

          <Button
            variant="contained"
            startIcon={isRunning ? <StopIcon /> : <PlayIcon />}
            onClick={handleRunDetection}
            disabled={isRunning}
          >
            {isRunning ? 'Running...' : 'Run Detection'}
          </Button>

          <Button
            variant="outlined"
            startIcon={<FilterIcon />}
            onClick={() => setShowFilterDialog(true)}
          >
            Filter
          </Button>

          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            disabled={clashes.length === 0}
          >
            Export
          </Button>
        </Box>

        {/* Progress */}
        {isRunning && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress variant="determinate" value={progress} />
            <Typography variant="caption" color="text.secondary">
              Analyzing model for clashes... {progress}%
            </Typography>
          </Box>
        )}
      </Box>

      {/* Clash List */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {filteredClashes.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            {clashes.length === 0 ? (
              <>
                <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
                <Typography color="text.secondary">
                  No clashes detected. Run detection to analyze the model.
                </Typography>
              </>
            ) : (
              <>
                <FilterIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography color="text.secondary">
                  No clashes match the current filter criteria.
                </Typography>
              </>
            )}
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Severity</TableCell>
                  <TableCell>Elements</TableCell>
                  <TableCell>Overlap</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredClashes.map((clash) => (
                  <TableRow
                    key={clash.id}
                    hover
                    selected={selectedClash?.id === clash.id}
                    onClick={() => handleClashClick(clash)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      <Chip
                        label={clash.severity.toUpperCase()}
                        color={SEVERITY_COLORS[clash.severity] as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{clash.element1.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        vs {clash.element2.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {(clash.overlap_volume * 1000000).toFixed(2)} cm³
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={clash.status}
                        color={STATUS_COLORS[clash.status] as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Zoom to clash">
                        <IconButton size="small">
                          <ZoomIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>

      {/* Filter Dialog */}
      <Dialog
        open={showFilterDialog}
        onClose={() => setShowFilterDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Filter Clashes</DialogTitle>
        <DialogContent>
          <Typography variant="subtitle2" gutterBottom>
            Severity
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
            {['critical', 'high', 'medium', 'low'].map((severity) => (
              <FormControlLabel
                key={severity}
                control={
                  <Checkbox
                    checked={filter.severity.includes(severity)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFilter((prev) => ({
                          ...prev,
                          severity: [...prev.severity, severity],
                        }));
                      } else {
                        setFilter((prev) => ({
                          ...prev,
                          severity: prev.severity.filter((s) => s !== severity),
                        }));
                      }
                    }}
                  />
                }
                label={severity.charAt(0).toUpperCase() + severity.slice(1)}
              />
            ))}
          </Box>

          <Typography variant="subtitle2" gutterBottom>
            Status
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
            {['new', 'acknowledged', 'resolved', 'ignored'].map((status) => (
              <FormControlLabel
                key={status}
                control={
                  <Checkbox
                    checked={filter.status.includes(status)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFilter((prev) => ({
                          ...prev,
                          status: [...prev.status, status],
                        }));
                      } else {
                        setFilter((prev) => ({
                          ...prev,
                          status: prev.status.filter((s) => s !== status),
                        }));
                      }
                    }}
                  />
                }
                label={status.charAt(0).toUpperCase() + status.slice(1)}
              />
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowFilterDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default ClashDetector;
