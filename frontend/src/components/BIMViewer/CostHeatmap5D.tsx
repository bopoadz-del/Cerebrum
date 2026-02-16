"""
CostHeatmap5D.tsx - 5D cost visualization for BIM models
"""

import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Slider,
  Chip,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ToggleButton,
  ToggleButtonGroup,
  LinearProgress,
} from '@mui/material';
import {
  AttachMoney as MoneyIcon,
  BarChart as ChartIcon,
  Palette as PaletteIcon,
  TrendingUp as TrendingIcon,
  CalendarToday as CalendarIcon,
} from '@mui/icons-material';

// Types
interface CostData {
  elementId: string;
  globalId: string;
  elementType: string;
  name: string;
  materialCost: number;
  laborCost: number;
  equipmentCost: number;
  totalCost: number;
  quantity: number;
  unit: string;
  unitPrice: number;
}

interface CostHeatmap5DProps {
  costData: CostData[];
  visualizationMode?: 'total' | 'material' | 'labor' | 'equipment';
  colorScheme?: 'red' | 'blue' | 'green' | 'spectrum';
  onElementHover?: (elementId: string | null) => void;
  onElementClick?: (element: CostData) => void;
}

// Color schemes
const COLOR_SCHEMES: Record<string, string[]> = {
  red: ['#ffebee', '#ffcdd2', '#ef9a9a', '#e57373', '#ef5350', '#f44336', '#e53935', '#d32f2f'],
  blue: ['#e3f2fd', '#bbdefb', '#90caf9', '#64b5f6', '#42a5f5', '#2196f3', '#1e88e5', '#1565c0'],
  green: ['#e8f5e9', '#c8e6c9', '#a5d6a7', '#81c784', '#66bb6a', '#4caf50', '#43a047', '#2e7d32'],
  spectrum: ['#4caf50', '#8bc34a', '#cddc39', '#ffeb3b', '#ffc107', '#ff9800', '#ff5722', '#f44336'],
};

export const CostHeatmap5D: React.FC<CostHeatmap5DProps> = ({
  costData,
  visualizationMode = 'total',
  colorScheme = 'spectrum',
  onElementHover,
  onElementClick,
}) => {
  const [mode, setMode] = useState(visualizationMode);
  const [scheme, setScheme] = useState(colorScheme);
  const [costRange, setCostRange] = useState<[number, number]>([0, 100]);

  // Calculate statistics
  const stats = useMemo(() => {
    const costs = costData.map((d) => d.totalCost);
    const materialCosts = costData.map((d) => d.materialCost);
    const laborCosts = costData.map((d) => d.laborCost);
    const equipmentCosts = costData.map((d) => d.equipmentCost);

    return {
      totalProjectCost: costs.reduce((a, b) => a + b, 0),
      totalMaterialCost: materialCosts.reduce((a, b) => a + b, 0),
      totalLaborCost: laborCosts.reduce((a, b) => a + b, 0),
      totalEquipmentCost: equipmentCosts.reduce((a, b) => a + b, 0),
      averageCost: costs.reduce((a, b) => a + b, 0) / costs.length || 0,
      maxCost: Math.max(...costs, 0),
      minCost: Math.min(...costs, Infinity),
      elementCount: costData.length,
    };
  }, [costData]);

  // Get cost value based on mode
  const getCostValue = useCallback(
    (data: CostData): number => {
      switch (mode) {
        case 'material':
          return data.materialCost;
        case 'labor':
          return data.laborCost;
        case 'equipment':
          return data.equipmentCost;
        default:
          return data.totalCost;
      }
    },
    [mode]
  );

  // Get color for cost value
  const getColor = useCallback(
    (cost: number): string => {
      const colors = COLOR_SCHEMES[scheme];
      const maxCost = stats.maxCost || 1;
      const normalizedCost = cost / maxCost;
      const index = Math.min(Math.floor(normalizedCost * colors.length), colors.length - 1);
      return colors[index];
    },
    [scheme, stats.maxCost]
  );

  // Group by element type
  const costByType = useMemo(() => {
    const grouped: Record<string, { count: number; totalCost: number; elements: CostData[] }> = {};

    costData.forEach((data) => {
      if (!grouped[data.elementType]) {
        grouped[data.elementType] = { count: 0, totalCost: 0, elements: [] };
      }
      grouped[data.elementType].count++;
      grouped[data.elementType].totalCost += getCostValue(data);
      grouped[data.elementType].elements.push(data);
    });

    return Object.entries(grouped)
      .map(([type, data]) => ({ type, ...data }))
      .sort((a, b) => b.totalCost - a.totalCost);
  }, [costData, getCostValue]);

  // Top expensive elements
  const topExpensive = useMemo(() => {
    return [...costData]
      .sort((a, b) => getCostValue(b) - getCostValue(a))
      .slice(0, 10);
  }, [costData, getCostValue]);

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom>
          5D Cost Visualization
        </Typography>

        {/* Summary Stats */}
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
          <Chip
            icon={<MoneyIcon />}
            label={`Total: $${stats.totalProjectCost.toLocaleString()}`}
            color="primary"
          />
          <Chip label={`${stats.elementCount} Elements`} variant="outlined" />
          <Chip
            label={`Avg: $${stats.averageCost.toFixed(2)}`}
            variant="outlined"
          />
        </Box>

        {/* Cost Breakdown */}
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Material
            </Typography>
            <LinearProgress
              variant="determinate"
              value={(stats.totalMaterialCost / stats.totalProjectCost) * 100}
              sx={{ height: 8, borderRadius: 1 }}
            />
            <Typography variant="caption">
              ${stats.totalMaterialCost.toLocaleString()}
            </Typography>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Labor
            </Typography>
            <LinearProgress
              variant="determinate"
              value={(stats.totalLaborCost / stats.totalProjectCost) * 100}
              color="success"
              sx={{ height: 8, borderRadius: 1 }}
            />
            <Typography variant="caption">
              ${stats.totalLaborCost.toLocaleString()}
            </Typography>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Equipment
            </Typography>
            <LinearProgress
              variant="determinate"
              value={(stats.totalEquipmentCost / stats.totalProjectCost) * 100}
              color="warning"
              sx={{ height: 8, borderRadius: 1 }}
            />
            <Typography variant="caption">
              ${stats.totalEquipmentCost.toLocaleString()}
            </Typography>
          </Box>
        </Box>

        {/* Controls */}
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={(_, newMode) => newMode && setMode(newMode)}
            size="small"
          >
            <ToggleButton value="total">Total</ToggleButton>
            <ToggleButton value="material">Material</ToggleButton>
            <ToggleButton value="labor">Labor</ToggleButton>
            <ToggleButton value="equipment">Equipment</ToggleButton>
          </ToggleButtonGroup>

          <FormControl sx={{ minWidth: 120 }} size="small">
            <InputLabel>Color Scheme</InputLabel>
            <Select value={scheme} onChange={(e) => setScheme(e.target.value)} label="Color Scheme">
              <MenuItem value="spectrum">Spectrum</MenuItem>
              <MenuItem value="red">Red</MenuItem>
              <MenuItem value="blue">Blue</MenuItem>
              <MenuItem value="green">Green</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Box>

      {/* Content */}
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
        {/* Legend */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Cost Legend
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption">Low</Typography>
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              {COLOR_SCHEMES[scheme].map((color, i) => (
                <Box
                  key={i}
                  sx={{
                    width: 24,
                    height: 16,
                    backgroundColor: color,
                    border: '1px solid #ccc',
                  }}
                />
              ))}
            </Box>
            <Typography variant="caption">High</Typography>
          </Box>
        </Box>

        {/* Cost by Element Type */}
        <Typography variant="subtitle2" gutterBottom>
          Cost by Element Type
        </Typography>
        <TableContainer sx={{ mb: 3 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Count</TableCell>
                <TableCell>Total Cost</TableCell>
                <TableCell>Avg Cost</TableCell>
                <TableCell>% of Total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {costByType.map((item) => (
                <TableRow key={item.type} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          backgroundColor: getColor(item.totalCost / item.count),
                          borderRadius: 0.5,
                        }}
                      />
                      {item.type}
                    </Box>
                  </TableCell>
                  <TableCell>{item.count}</TableCell>
                  <TableCell>${item.totalCost.toLocaleString()}</TableCell>
                  <TableCell>${(item.totalCost / item.count).toFixed(2)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={(item.totalCost / stats.totalProjectCost) * 100}
                        sx={{ width: 60, height: 6 }}
                      />
                      {((item.totalCost / stats.totalProjectCost) * 100).toFixed(1)}%
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Top Expensive Elements */}
        <Typography variant="subtitle2" gutterBottom>
          Top 10 Most Expensive Elements
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Element</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Cost</TableCell>
                <TableCell>Quantity</TableCell>
                <TableCell>Unit Price</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {topExpensive.map((element) => (
                <TableRow
                  key={element.elementId}
                  hover
                  onClick={() => onElementClick?.(element)}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          backgroundColor: getColor(getCostValue(element)),
                          borderRadius: 0.5,
                        }}
                      />
                      {element.name}
                    </Box>
                  </TableCell>
                  <TableCell>{element.elementType}</TableCell>
                  <TableCell>${getCostValue(element).toLocaleString()}</TableCell>
                  <TableCell>
                    {element.quantity} {element.unit}
                  </TableCell>
                  <TableCell>${element.unitPrice.toFixed(2)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Paper>
  );
};

export default CostHeatmap5D;
