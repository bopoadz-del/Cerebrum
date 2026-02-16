import React, { useState, useEffect } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Button,
  Chip,
  Divider,
  Alert,
  LinearProgress,
} from '@mui/material';
import {
  ViewInAr as ModelIcon,
  Warning as ClashIcon,
  Schedule as ScheduleIcon,
  AttachMoney as CostIcon,
  Assessment as ReportIcon,
  CloudUpload as UploadIcon,
} from '@mui/icons-material';
import FederatedModelViewer from '../components/vdc/FederatedModelViewer';
import ClashDetectionPanel from '../components/vdc/ClashDetectionPanel';
import Schedule4D from '../components/vdc/Schedule4D';
import Cost5D from '../components/vdc/Cost5D';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`vdc-tabpanel-${index}`}
      aria-labelledby={`vdc-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface ProjectStats {
  totalModels: number;
  totalClashes: number;
  resolvedClashes: number;
  openClashes: number;
  criticalClashes: number;
  projectProgress: number;
  lastSync: string;
}

const VDC: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [stats, setStats] = useState<ProjectStats>({
    totalModels: 0,
    totalClashes: 0,
    resolvedClashes: 0,
    openClashes: 0,
    criticalClashes: 0,
    projectProgress: 0,
    lastSync: '-',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjectStats();
  }, []);

  const fetchProjectStats = async () => {
    try {
      // In production, fetch from API
      // const response = await fetch('/api/v1/vdc/dashboard/stats');
      // const data = await response.json();
      
      // Mock data for demonstration
      setStats({
        totalModels: 5,
        totalClashes: 23,
        resolvedClashes: 15,
        openClashes: 8,
        criticalClashes: 2,
        projectProgress: 65,
        lastSync: new Date().toLocaleString(),
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const getClashSeverityColor = (count: number) => {
    if (count === 0) return 'success';
    if (count < 5) return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ flexGrow: 1, p: 2 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Virtual Design & Construction
        </Typography>
        <Typography variant="body1" color="text.secondary">
          BIM coordination, clash detection, 4D scheduling, and 5D cost management
        </Typography>
      </Box>

      {/* Project Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ModelIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Models
                </Typography>
              </Box>
              <Typography variant="h4">{stats.totalModels}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ClashIcon color="error" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Total Clashes
                </Typography>
              </Box>
              <Typography variant="h4">{stats.totalClashes}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ClashIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Resolved
                </Typography>
              </Box>
              <Typography variant="h4">{stats.resolvedClashes}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ClashIcon 
                  color={getClashSeverityColor(stats.openClashes) as any} 
                  sx={{ mr: 1 }} 
                />
                <Typography variant="body2" color="text.secondary">
                  Open Clashes
                </Typography>
              </Box>
              <Typography variant="h4">{stats.openClashes}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ScheduleIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Progress
                </Typography>
              </Box>
              <Typography variant="h4">{stats.projectProgress}%</Typography>
              <LinearProgress 
                variant="determinate" 
                value={stats.projectProgress} 
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <UploadIcon color="info" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Last Sync
                </Typography>
              </Box>
              <Typography variant="body2">{stats.lastSync}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Critical Alerts */}
      {stats.criticalClashes > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <strong>{stats.criticalClashes} critical clash(es)</strong> require immediate attention
        </Alert>
      )}

      {/* Main Tabs */}
      <Paper elevation={1}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="VDC tools tabs"
        >
          <Tab icon={<ModelIcon />} label="Federated Models" />
          <Tab icon={<ClashIcon />} label="Clash Detection" />
          <Tab icon={<ScheduleIcon />} label="4D Schedule" />
          <Tab icon={<CostIcon />} label="5D Cost" />
          <Tab icon={<ReportIcon />} label="Reports" />
        </Tabs>

        <Divider />

        <TabPanel value={activeTab} index={0}>
          <FederatedModelViewer />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <ClashDetectionPanel />
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Schedule4D />
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          <Cost5D />
        </TabPanel>

        <TabPanel value={activeTab} index={4}>
          <Box>
            <Typography variant="h6" gutterBottom>
              VDC Reports
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardHeader title="Clash Reports" />
                  <CardContent>
                    <Button variant="outlined" fullWidth sx={{ mb: 1 }}>
                      Export PDF Report
                    </Button>
                    <Button variant="outlined" fullWidth sx={{ mb: 1 }}>
                      Export Excel Report
                    </Button>
                    <Button variant="outlined" fullWidth>
                      Export BCF
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardHeader title="Coordination Reports" />
                  <CardContent>
                    <Button variant="outlined" fullWidth sx={{ mb: 1 }}>
                      Model Quality Report
                    </Button>
                    <Button variant="outlined" fullWidth sx={{ mb: 1 }}>
                      Coordination Dashboard
                    </Button>
                    <Button variant="outlined" fullWidth>
                      COBie Export
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default VDC;
