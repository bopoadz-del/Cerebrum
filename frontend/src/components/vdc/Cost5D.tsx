import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  AttachMoney as MoneyIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Warning as WarningIcon,
  PieChart as PieChartIcon,
  BarChart as BarChartIcon,
  GetApp as ExportIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';

interface CostItem {
  id: string;
  name: string;
  category: string;
  trade: string;
  unitCost: number;
  quantity: number;
  unitOfMeasure: string;
  totalCost: number;
  budgetAmount: number;
  actualAmount: number;
  variance: number;
  variancePercent: number;
  elementIds: string[];
}

interface CostSummary {
  totalBudget: number;
  totalActual: number;
  totalVariance: number;
  variancePercent: number;
  byCategory: Record<string, { budget: number; actual: number }>;
  byTrade: Record<string, { budget: number; actual: number }>;
}

interface HeatmapPoint {
  x: number;
  y: number;
  z: number;
  costDensity: number;
  totalCost: number;
  colorValue: number;
}

const Cost5D: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [costItems, setCostItems] = useState<CostItem[]>([]);
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapPoint[]>([]);
  const [selectedTrade, setSelectedTrade] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');

  useEffect(() => {
    // Simulate loading cost data
    const timer = setTimeout(() => {
      loadMockData();
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const loadMockData = () => {
    const mockCostItems: CostItem[] = [
      {
        id: 'cost-001',
        name: 'Concrete Foundation',
        category: 'Materials',
        trade: 'Concrete',
        unitCost: 150.0,
        quantity: 500.0,
        unitOfMeasure: 'm³',
        totalCost: 75000.0,
        budgetAmount: 75000.0,
        actualAmount: 78000.0,
        variance: 3000.0,
        variancePercent: 4.0,
        elementIds: ['elem-001', 'elem-002'],
      },
      {
        id: 'cost-002',
        name: 'Structural Steel',
        category: 'Materials',
        trade: 'Steel',
        unitCost: 2500.0,
        quantity: 100.0,
        unitOfMeasure: 'ton',
        totalCost: 250000.0,
        budgetAmount: 250000.0,
        actualAmount: 245000.0,
        variance: -5000.0,
        variancePercent: -2.0,
        elementIds: ['elem-003', 'elem-004', 'elem-005'],
      },
      {
        id: 'cost-003',
        name: 'MEP Rough-in',
        category: 'Labor',
        trade: 'MEP',
        unitCost: 75.0,
        quantity: 1000.0,
        unitOfMeasure: 'hr',
        totalCost: 75000.0,
        budgetAmount: 70000.0,
        actualAmount: 75000.0,
        variance: 5000.0,
        variancePercent: 7.1,
        elementIds: ['elem-006', 'elem-007'],
      },
      {
        id: 'cost-004',
        name: 'HVAC Equipment',
        category: 'Equipment',
        trade: 'MEP',
        unitCost: 15000.0,
        quantity: 10.0,
        unitOfMeasure: 'ea',
        totalCost: 150000.0,
        budgetAmount: 150000.0,
        actualAmount: 148500.0,
        variance: -1500.0,
        variancePercent: -1.0,
        elementIds: ['elem-008'],
      },
      {
        id: 'cost-005',
        name: 'Interior Finishes',
        category: 'Materials',
        trade: 'Interior',
        unitCost: 50.0,
        quantity: 5000.0,
        unitOfMeasure: 'm²',
        totalCost: 250000.0,
        budgetAmount: 240000.0,
        actualAmount: 250000.0,
        variance: 10000.0,
        variancePercent: 4.2,
        elementIds: ['elem-009', 'elem-010'],
      },
    ];

    setCostItems(mockCostItems);

    const mockSummary: CostSummary = {
      totalBudget: 785000.0,
      totalActual: 795500.0,
      totalVariance: 10500.0,
      variancePercent: 1.34,
      byCategory: {
        Materials: { budget: 575000, actual: 585000 },
        Labor: { budget: 70000, actual: 75000 },
        Equipment: { budget: 150000, actual: 148500 },
        Overhead: { budget: 50000, actual: 50000 },
      },
      byTrade: {
        Concrete: { budget: 75000, actual: 78000 },
        Steel: { budget: 250000, actual: 245000 },
        MEP: { budget: 225000, actual: 223500 },
        Interior: { budget: 240000, actual: 250000 },
      },
    };

    setSummary(mockSummary);

    // Mock heatmap data
    const mockHeatmap: HeatmapPoint[] = Array.from({ length: 50 }, (_, i) => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      z: Math.random() * 50,
      costDensity: Math.random() * 1000,
      totalCost: Math.random() * 50000,
      colorValue: Math.random(),
    }));

    setHeatmap(mockHeatmap);
  };

  const getFilteredCostItems = () => {
    return costItems.filter(item => {
      if (selectedTrade !== 'all' && item.trade !== selectedTrade) return false;
      if (selectedCategory !== 'all' && item.category !== selectedCategory)
        return false;
      return true;
    });
  };

  const getVarianceColor = (variance: number) => {
    if (variance > 0) return 'error';
    if (variance < 0) return 'success';
    return 'default';
  };

  const getVarianceIcon = (variance: number) => {
    if (variance > 0) return <TrendingUpIcon color="error" />;
    if (variance < 0) return <TrendingDownIcon color="success" />;
    return null;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const trades = ['all', ...Array.from(new Set(costItems.map(item => item.trade)))];
  const categories = ['all', ...Array.from(new Set(costItems.map(item => item.category)))];

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2 }}>Loading 5D cost data...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Budget
                </Typography>
                <Typography variant="h4">
                  {formatCurrency(summary.totalBudget)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Actual Cost
                </Typography>
                <Typography variant="h4">
                  {formatCurrency(summary.totalActual)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Variance
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Typography
                    variant="h4"
                    color={summary.totalVariance > 0 ? 'error' : 'success'}
                  >
                    {formatCurrency(Math.abs(summary.totalVariance))}
                  </Typography>
                  {getVarianceIcon(summary.totalVariance)}
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {summary.variancePercent > 0 ? '+' : ''}
                  {summary.variancePercent.toFixed(2)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Cost Items
                </Typography>
                <Typography variant="h4">{costItems.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Trade</InputLabel>
              <Select
                value={selectedTrade}
                onChange={e => setSelectedTrade(e.target.value)}
              >
                {trades.map(trade => (
                  <MenuItem key={trade} value={trade}>
                    {trade === 'all' ? 'All Trades' : trade}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Category</InputLabel>
              <Select
                value={selectedCategory}
                onChange={e => setSelectedCategory(e.target.value)}
              >
                {categories.map(cat => (
                  <MenuItem key={cat} value={cat}>
                    {cat === 'all' ? 'All Categories' : cat}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Button
              variant="outlined"
              startIcon={<ExportIcon />}
              fullWidth
            >
              Export to Excel
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Tabs */}
      <Paper>
        <Tabs
          value={activeTab}
          onChange={(_, value) => setActiveTab(value)}
          variant="scrollable"
        >
          <Tab icon={<BarChartIcon />} label="Cost Items" />
          <Tab icon={<PieChartIcon />} label="By Category" />
          <Tab icon={<PieChartIcon />} label="By Trade" />
          <Tab icon={<MoneyIcon />} label="Cost Heatmap" />
        </Tabs>

        {/* Cost Items Tab */}
        {activeTab === 0 && (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Trade</TableCell>
                  <TableCell align="right">Unit Cost</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Total Cost</TableCell>
                  <TableCell align="right">Budget</TableCell>
                  <TableCell align="right">Actual</TableCell>
                  <TableCell align="right">Variance</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {getFilteredCostItems().map(item => (
                  <TableRow key={item.id} hover>
                    <TableCell>{item.name}</TableCell>
                    <TableCell>
                      <Chip label={item.category} size="small" />
                    </TableCell>
                    <TableCell>{item.trade}</TableCell>
                    <TableCell align="right">
                      {formatCurrency(item.unitCost)}/{item.unitOfMeasure}
                    </TableCell>
                    <TableCell align="right">
                      {item.quantity.toLocaleString()}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(item.totalCost)}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(item.budgetAmount)}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(item.actualAmount)}
                    </TableCell>
                    <TableCell align="right">
                      <Chip
                        label={`${item.variancePercent > 0 ? '+' : ''}${item.variancePercent.toFixed(1)}%`}
                        color={getVarianceColor(item.variance) as any}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* By Category Tab */}
        {activeTab === 1 && summary && (
          <Box sx={{ p: 2 }}>
            <Grid container spacing={2}>
              {Object.entries(summary.byCategory).map(([category, values]) => (
                <Grid item xs={12} md={6} key={category}>
                  <Card>
                    <CardHeader title={category} />
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Budget: {formatCurrency(values.budget)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Actual: {formatCurrency(values.actual)}
                      </Typography>
                      <Box sx={{ mt: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={(values.actual / values.budget) * 100}
                          color={
                            values.actual > values.budget ? 'error' : 'success'
                          }
                        />
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        {((values.actual / values.budget) * 100).toFixed(1)}% of budget
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* By Trade Tab */}
        {activeTab === 2 && summary && (
          <Box sx={{ p: 2 }}>
            <Grid container spacing={2}>
              {Object.entries(summary.byTrade).map(([trade, values]) => (
                <Grid item xs={12} md={6} key={trade}>
                  <Card>
                    <CardHeader title={trade} />
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Budget: {formatCurrency(values.budget)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Actual: {formatCurrency(values.actual)}
                      </Typography>
                      <Box sx={{ mt: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={(values.actual / values.budget) * 100}
                          color={
                            values.actual > values.budget ? 'error' : 'success'
                          }
                        />
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        {((values.actual / values.budget) * 100).toFixed(1)}% of budget
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Cost Heatmap Tab */}
        {activeTab === 3 && (
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Cost Density Heatmap
            </Typography>
            <Box
              sx={{
                height: 400,
                backgroundColor: '#f5f5f5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 1,
                position: 'relative',
              }}
            >
              {/* Simple heatmap visualization */}
              <Box
                sx={{
                  width: '100%',
                  height: '100%',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                {heatmap.map((point, index) => (
                  <Box
                    key={index}
                    sx={{
                      position: 'absolute',
                      left: `${point.x}%`,
                      top: `${point.y}%`,
                      width: 20,
                      height: 20,
                      borderRadius: '50%',
                      backgroundColor: `rgba(255, 0, 0, ${point.colorValue})`,
                      transform: 'translate(-50%, -50%)',
                    }}
                    title={`Cost: ${formatCurrency(point.totalCost)}`}
                  />
                ))}
              </Box>
              <Box
                sx={{
                  position: 'absolute',
                  bottom: 16,
                  right: 16,
                  backgroundColor: 'rgba(255,255,255,0.9)',
                  p: 1,
                  borderRadius: 1,
                }}
              >
                <Typography variant="caption">Cost Density</Typography>
                <Box
                  sx={{
                    width: 100,
                    height: 10,
                    background: 'linear-gradient(to right, rgba(255,0,0,0), rgba(255,0,0,1))',
                    mt: 0.5,
                  }}
                />
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption">Low</Typography>
                  <Typography variant="caption">High</Typography>
                </Box>
              </Box>
            </Box>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default Cost5D;
