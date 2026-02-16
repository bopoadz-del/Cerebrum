import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { Visibility, Settings, Notifications } from '@mui/icons-material';
import { api } from '../../services/api';

interface Sensor {
  id: string;
  name: string;
  type: string;
  location: string;
  is_active: boolean;
}

interface SensorData {
  timestamp: string;
  [key: string]: any;
}

export const SensorDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [selectedSensor, setSelectedSensor] = useState<string | null>(null);
  const [sensorData, setSensorData] = useState<SensorData[]>([]);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    fetchSensors();
    fetchSummary();
  }, []);

  useEffect(() => {
    if (selectedSensor) {
      fetchSensorData(selectedSensor);
    }
  }, [selectedSensor]);

  const fetchSensors = async () => {
    try {
      const response = await api.get('/iot/sensors');
      setSensors(response.data);
    } catch (error) {
      console.error('Failed to fetch sensors:', error);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await api.get('/iot/sensors/summary');
      setSummary(response.data);
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  };

  const fetchSensorData = async (sensorId: string) => {
    try {
      const response = await api.get(`/iot/sensors/${sensorId}/data?hours=24`);
      setSensorData(response.data.data);
    } catch (error) {
      console.error('Failed to fetch sensor data:', error);
    }
  };

  const getSensorTypeColor = (type: string) => {
    const colors: { [key: string]: string } = {
      'concrete_maturity': 'primary',
      'structural_health': 'secondary',
      'temperature': 'success',
      'humidity': 'info',
      'vibration': 'warning',
      'strain': 'error'
    };
    return colors[type] || 'default';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        IoT Sensor Dashboard
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Sensors
              </Typography>
              <Typography variant="h4">
                {summary?.total_sensors || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Sensors
              </Typography>
              <Typography variant="h4">
                {summary?.active_sensors || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Data Points (24h)
              </Typography>
              <Typography variant="h4">
                {(summary?.data_points?.concrete_maturity || 0) +
                 (summary?.data_points?.structural_health || 0) +
                 (summary?.data_points?.environmental || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Alerts
              </Typography>
              <Typography variant="h4" color="error">
                0
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Tabs
        value={activeTab}
        onChange={(_, value) => setActiveTab(value)}
        sx={{ mb: 3 }}
      >
        <Tab label="All Sensors" />
        <Tab label="Concrete Maturity" />
        <Tab label="Structural Health" />
        <Tab label="Environmental" />
      </Tabs>

      {/* Sensors Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Sensor ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sensors.map((sensor) => (
              <TableRow
                key={sensor.id}
                selected={selectedSensor === sensor.id}
                onClick={() => setSelectedSensor(sensor.id)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>{sensor.id}</TableCell>
                <TableCell>{sensor.name}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={sensor.type}
                    color={getSensorTypeColor(sensor.type) as any}
                  />
                </TableCell>
                <TableCell>{sensor.location}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={sensor.is_active ? 'Active' : 'Inactive'}
                    color={sensor.is_active ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell>
                  <Tooltip title="View Details">
                    <IconButton size="small">
                      <Visibility />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Settings">
                    <IconButton size="small">
                      <Settings />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Alerts">
                    <IconButton size="small">
                      <Notifications />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Sensor Data Chart */}
      {selectedSensor && sensorData.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Sensor Data - {sensors.find(s => s.id === selectedSensor)?.name}
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={sensorData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <YAxis />
                <RechartsTooltip />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#8884d8"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default SensorDashboard;
