import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { api } from '../services/api';

interface KPICard {
  id: string;
  title: string;
  value: number;
  unit: string;
  change_percent: number;
  trend: string;
  format: string;
}

interface DashboardData {
  kpis: KPICard[];
  charts: any;
  portfolio: any;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

export const DataWarehouse: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [nlQuery, setNlQuery] = useState('');
  const [queryResult, setQueryResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/warehouse/dashboard/executive');
      setDashboardData(response.data);
    } catch (err) {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleNlQuery = async () => {
    if (!nlQuery.trim()) return;
    
    try {
      setLoading(true);
      const response = await api.post('/warehouse/query/natural-language', {
        query: nlQuery
      });
      setQueryResult(response.data);
    } catch (err) {
      setError('Query failed');
    } finally {
      setLoading(false);
    }
  };

  const formatValue = (card: KPICard) => {
    if (card.format === 'currency') {
      return `$${card.value.toLocaleString()}`;
    }
    if (card.format === 'percentage') {
      return `${card.value}%`;
    }
    return card.value.toLocaleString();
  };

  const renderExecutiveDashboard = () => (
    <Grid container spacing={3}>
      {/* KPI Cards */}
      {dashboardData?.kpis.map((kpi) => (
        <Grid item xs={12} sm={6} md={4} key={kpi.id}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                {kpi.title}
              </Typography>
              <Typography variant="h4">
                {formatValue(kpi)}
              </Typography>
              <Chip
                size="small"
                label={`${kpi.change_percent > 0 ? '+' : ''}${kpi.change_percent}%`}
                color={kpi.change_percent >= 0 ? 'success' : 'error'}
              />
            </CardContent>
          </Card>
        </Grid>
      ))}

      {/* Charts */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Revenue Trend
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dashboardData?.charts?.revenue_trend?.datasets[0]?.data.map((v: number, i: number) => ({
                name: dashboardData?.charts?.revenue_trend?.labels[i],
                value: v
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#8884d8" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Revenue by Segment
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={dashboardData?.charts?.revenue_by_segment?.datasets[0]?.data.map((v: number, i: number) => ({
                    name: dashboardData?.charts?.revenue_by_segment?.labels[i],
                    value: v
                  }))}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  dataKey="value"
                >
                  {dashboardData?.charts?.revenue_by_segment?.datasets[0]?.data.map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderNlQuery = () => (
    <Box>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Natural Language Query
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Ask a question about your data..."
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleNlQuery()}
            />
            <Button
              variant="contained"
              onClick={handleNlQuery}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Query'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {queryResult && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Results
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              SQL: <code>{queryResult.sql}</code>
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              {queryResult.explanation}
            </Typography>
            <TableContainer component={Paper} sx={{ mt: 2 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    {queryResult.results.length > 0 &&
                      Object.keys(queryResult.results[0]).map((key) => (
                        <TableCell key={key}>{key}</TableCell>
                      ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {queryResult.results.map((row: any, index: number) => (
                    <TableRow key={index}>
                      {Object.values(row).map((value: any, i: number) => (
                        <TableCell key={i}>{value}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  );

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Data Warehouse
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Tabs
        value={activeTab}
        onChange={(_, value) => setActiveTab(value)}
        sx={{ mb: 3 }}
      >
        <Tab label="Executive Dashboard" />
        <Tab label="Natural Language Query" />
        <Tab label="Predictive Analytics" />
      </Tabs>

      {activeTab === 0 && renderExecutiveDashboard()}
      {activeTab === 1 && renderNlQuery()}
      {activeTab === 2 && (
        <Typography>Predictive Analytics Coming Soon</Typography>
      )}
    </Box>
  );
};

export default DataWarehouse;
