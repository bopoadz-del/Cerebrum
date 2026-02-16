import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Button,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  LinearProgress,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Switch,
  FormControlLabel,
  TextField,
  MenuItem,
  Select,
  InputLabel,
  FormControl,
} from '@mui/material';
import {
  Cloud as CloudIcon,
  CloudDone as CloudDoneIcon,
  CloudOff as CloudOffIcon,
  Sync as SyncIcon,
  Settings as SettingsIcon,
  Folder as FolderIcon,
  InsertDriveFile as FileIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  History as HistoryIcon,
  Storage as StorageIcon,
  Speed as SpeedIcon,
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
} from '@mui/icons-material';
import { useDriveAPI } from '../hooks/useDriveAPI';
import { DriveFilePicker } from '../components/DriveFilePicker';
import { useSnackbar } from '../hooks/useSnackbar';

// Types
interface SyncTask {
  task_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  files_synced: number;
  folders_synced: number;
  errors: string[];
}

interface DriveStats {
  total_syncs: number;
  successful_syncs: number;
  failed_syncs: number;
  total_files_synced: number;
  total_folders_synced: number;
  recent_tasks: SyncTask[];
}

interface Conflict {
  conflict_id: string;
  conflict_type: string;
  local_version?: {
    name: string;
    modified_time: string;
  };
  remote_version?: {
    name: string;
    modified_time: string;
  };
  detected_at: string;
  resolved: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index}>
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

export const GoogleDrive: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [syncStats, setSyncStats] = useState<DriveStats | null>(null);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [showFilePicker, setShowFilePicker] = useState(false);
  const [syncInProgress, setSyncInProgress] = useState(false);
  const [syncProgress, setSyncProgress] = useState(0);
  const [settings, setSettings] = useState({
    autoSync: true,
    syncInterval: 30,
    conflictResolution: 'last_modified_wins',
    notifyOnConflict: true,
  });

  const {
    getAuthUrl,
    checkAuth,
    revokeAuth,
    startSync,
    getSyncStatus,
    getUserStats,
    getConflicts,
    scheduleSync,
    isLoading,
    error,
  } = useDriveAPI();

  const { showSnackbar } = useSnackbar();

  // Check authentication status
  useEffect(() => {
    const checkAuthentication = async () => {
      try {
        const authStatus = await checkAuth();
        setIsAuthenticated(authStatus.authenticated);
      } catch (err) {
        console.error('Auth check failed:', err);
      }
    };
    checkAuthentication();
  }, [checkAuth]);

  // Load stats when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadUserStats();
      loadConflicts();
    }
  }, [isAuthenticated]);

  const loadUserStats = useCallback(async () => {
    try {
      const stats = await getUserStats();
      setSyncStats(stats);
    } catch (err) {
      showSnackbar('Failed to load sync stats', 'error');
    }
  }, [getUserStats, showSnackbar]);

  const loadConflicts = useCallback(async () => {
    try {
      const conflictData = await getConflicts();
      setConflicts(conflictData.conflicts || []);
    } catch (err) {
      console.error('Failed to load conflicts:', err);
    }
  }, [getConflicts]);

  const handleAuthenticate = async () => {
    setAuthLoading(true);
    try {
      const { auth_url } = await getAuthUrl();
      // Open auth URL in popup
      const width = 500;
      const height = 600;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      
      const popup = window.open(
        auth_url,
        'Google Drive Auth',
        `width=${width},height=${height},left=${left},top=${top}`
      );

      // Poll for popup close
      const pollTimer = setInterval(() => {
        if (popup?.closed) {
          clearInterval(pollTimer);
          checkAuth().then(status => {
            setIsAuthenticated(status.authenticated);
            if (status.authenticated) {
              showSnackbar('Successfully connected to Google Drive', 'success');
            }
          });
          setAuthLoading(false);
        }
      }, 500);
    } catch (err) {
      showSnackbar('Authentication failed', 'error');
      setAuthLoading(false);
    }
  };

  const handleRevoke = async () => {
    try {
      await revokeAuth();
      setIsAuthenticated(false);
      showSnackbar('Google Drive connection revoked', 'info');
    } catch (err) {
      showSnackbar('Failed to revoke connection', 'error');
    }
  };

  const handleStartSync = async (fullResync = false) => {
    setSyncInProgress(true);
    setSyncProgress(0);
    
    try {
      const result = await startSync({ full_resync: fullResync });
      showSnackbar('Sync started', 'info');
      
      // Poll for sync status
      const pollInterval = setInterval(async () => {
        try {
          const status = await getSyncStatus(result.task_id);
          
          if (status.status === 'completed') {
            clearInterval(pollInterval);
            setSyncInProgress(false);
            setSyncProgress(100);
            showSnackbar('Sync completed successfully', 'success');
            loadUserStats();
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            setSyncInProgress(false);
            showSnackbar(`Sync failed: ${status.error_message}`, 'error');
          } else {
            // Update progress
            setSyncProgress((prev) => Math.min(prev + 10, 90));
          }
        } catch (err) {
          clearInterval(pollInterval);
          setSyncInProgress(false);
        }
      }, 2000);
    } catch (err) {
      showSnackbar('Failed to start sync', 'error');
      setSyncInProgress(false);
    }
  };

  const handleScheduleSync = async () => {
    try {
      await scheduleSync(settings.syncInterval);
      showSnackbar(`Sync scheduled every ${settings.syncInterval} minutes`, 'success');
    } catch (err) {
      showSnackbar('Failed to schedule sync', 'error');
    }
  };

  const handleFileSelect = (files: any[]) => {
    showSnackbar(`Selected ${files.length} file(s)`, 'success');
    setShowFilePicker(false);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'running':
        return <SyncIcon color="primary" className="spin" />;
      default:
        return <ScheduleIcon color="action" />;
    }
  };

  if (!isAuthenticated) {
    return (
      <Container maxWidth="md" sx={{ py: 8 }}>
        <Paper elevation={3} sx={{ p: 6, textAlign: 'center' }}>
          <CloudOffIcon sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h4" gutterBottom>
            Connect to Google Drive
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
            Sync your files with Google Drive for seamless collaboration and backup.
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<CloudIcon />}
            onClick={handleAuthenticate}
            disabled={authLoading}
          >
            {authLoading ? <CircularProgress size={24} /> : 'Connect Google Drive'}
          </Button>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <CloudDoneIcon color="success" sx={{ fontSize: 40 }} />
          <Box>
            <Typography variant="h4">Google Drive</Typography>
            <Typography variant="body2" color="text.secondary">
              Connected and syncing
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<FolderIcon />}
            onClick={() => setShowFilePicker(true)}
          >
            Browse Files
          </Button>
          <Button
            variant="contained"
            startIcon={<SyncIcon />}
            onClick={() => handleStartSync()}
            disabled={syncInProgress}
          >
            {syncInProgress ? 'Syncing...' : 'Sync Now'}
          </Button>
          <Button variant="outlined" color="error" onClick={handleRevoke}>
            Disconnect
          </Button>
        </Box>
      </Box>

      {/* Sync Progress */}
      {syncInProgress && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <SyncIcon sx={{ mr: 1 }} className="spin" />
            <Typography variant="body1">Sync in progress...</Typography>
          </Box>
          <LinearProgress variant="determinate" value={syncProgress} />
        </Paper>
      )}

      {/* Stats Cards */}
      {syncStats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <SyncIcon color="primary" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h4">{syncStats.total_syncs}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Syncs
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <StorageIcon color="success" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h4">{syncStats.total_files_synced}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Files Synced
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <FolderIcon color="info" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h4">{syncStats.total_folders_synced}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Folders Synced
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <WarningIcon 
                    color={conflicts.length > 0 ? 'warning' : 'success'} 
                    sx={{ mr: 2 }} 
                  />
                  <Box>
                    <Typography variant="h4">{conflicts.length}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Pending Conflicts
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Tabs */}
      <Paper>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab label="Sync History" icon={<HistoryIcon />} iconPosition="start" />
          <Tab label="Conflicts" icon={<WarningIcon />} iconPosition="start" />
          <Tab label="Settings" icon={<SettingsIcon />} iconPosition="start" />
        </Tabs>

        {/* Sync History Tab */}
        <TabPanel value={activeTab} index={0}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Status</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Completed</TableCell>
                  <TableCell>Files</TableCell>
                  <TableCell>Folders</TableCell>
                  <TableCell>Errors</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {syncStats?.recent_tasks.map((task) => (
                  <TableRow key={task.task_id}>
                    <TableCell>{getStatusIcon(task.status)}</TableCell>
                    <TableCell>{new Date(task.started_at).toLocaleString()}</TableCell>
                    <TableCell>
                      {task.completed_at 
                        ? new Date(task.completed_at).toLocaleString() 
                        : '-'}
                    </TableCell>
                    <TableCell>{task.files_synced}</TableCell>
                    <TableCell>{task.folders_synced}</TableCell>
                    <TableCell>
                      {task.errors.length > 0 ? (
                        <Chip 
                          label={`${task.errors.length} errors`} 
                          color="error" 
                          size="small" 
                        />
                      ) : (
                        '-'
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {!syncStats?.recent_tasks.length && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary">No sync history</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Conflicts Tab */}
        <TabPanel value={activeTab} index={1}>
          {conflicts.length === 0 ? (
            <Alert severity="success">No pending conflicts</Alert>
          ) : (
            <List>
              {conflicts.map((conflict) => (
                <React.Fragment key={conflict.conflict_id}>
                  <ListItem>
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText
                      primary={conflict.conflict_type}
                      secondary={
                        <Box>
                          <Typography variant="body2">
                            Local: {conflict.local_version?.name || 'N/A'}
                          </Typography>
                          <Typography variant="body2">
                            Remote: {conflict.remote_version?.name || 'N/A'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Detected: {new Date(conflict.detected_at).toLocaleString()}
                          </Typography>
                        </Box>
                      }
                    />
                    <Button variant="outlined" size="small">
                      Resolve
                    </Button>
                  </ListItem>
                  <Divider />
                </React.Fragment>
              ))}
            </List>
          )}
        </TabPanel>

        {/* Settings Tab */}
        <TabPanel value={activeTab} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Sync Settings
              </Typography>
              
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoSync}
                    onChange={(e) => setSettings({ ...settings, autoSync: e.target.checked })}
                  />
                }
                label="Enable automatic sync"
              />
              
              <FormControl fullWidth sx={{ mt: 2 }}>
                <InputLabel>Sync Interval</InputLabel>
                <Select
                  value={settings.syncInterval}
                  onChange={(e) => setSettings({ ...settings, syncInterval: Number(e.target.value) })}
                  disabled={!settings.autoSync}
                >
                  <MenuItem value={5}>Every 5 minutes</MenuItem>
                  <MenuItem value={15}>Every 15 minutes</MenuItem>
                  <MenuItem value={30}>Every 30 minutes</MenuItem>
                  <MenuItem value={60}>Every hour</MenuItem>
                </Select>
              </FormControl>
              
              <FormControl fullWidth sx={{ mt: 2 }}>
                <InputLabel>Conflict Resolution</InputLabel>
                <Select
                  value={settings.conflictResolution}
                  onChange={(e) => setSettings({ ...settings, conflictResolution: e.target.value })}
                >
                  <MenuItem value="last_modified_wins">Last Modified Wins</MenuItem>
                  <MenuItem value="local_wins">Local Always Wins</MenuItem>
                  <MenuItem value="remote_wins">Remote Always Wins</MenuItem>
                  <MenuItem value="manual">Manual Resolution</MenuItem>
                </Select>
              </FormControl>
              
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.notifyOnConflict}
                    onChange={(e) => setSettings({ ...settings, notifyOnConflict: e.target.checked })}
                  />
                }
                label="Notify on conflict"
                sx={{ mt: 2 }}
              />
              
              <Box sx={{ mt: 3 }}>
                <Button
                  variant="contained"
                  onClick={handleScheduleSync}
                  disabled={!settings.autoSync}
                >
                  Apply Schedule
                </Button>
              </Box>
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>

      {/* File Picker Dialog */}
      <Dialog
        open={showFilePicker}
        onClose={() => setShowFilePicker(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{ sx: { height: '80vh' } }}
      >
        <DialogContent sx={{ p: 0 }}>
          <DriveFilePicker
            onSelect={handleFileSelect}
            onCancel={() => setShowFilePicker(false)}
            multiSelect
          />
        </DialogContent>
      </Dialog>
    </Container>
  );
};

export default GoogleDrive;
