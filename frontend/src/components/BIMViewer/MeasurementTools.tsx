"""
MeasurementTools.tsx - Distance, area, and angle measurement tools for BIM
"""

import React, { useState, useCallback, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Divider,
  Tooltip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Straighten as DistanceIcon,
  SquareFoot as AreaIcon,
  RotateRight as AngleIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
  Save as SaveIcon,
  Clear as ClearIcon,
  Undo as UndoIcon,
} from '@mui/icons-material';

// Types
type MeasurementType = 'distance' | 'area' | 'angle';
type MeasurementUnit = 'm' | 'cm' | 'mm' | 'ft' | 'in';

interface Point3D {
  x: number;
  y: number;
  z: number;
}

interface Measurement {
  id: string;
  type: MeasurementType;
  points: Point3D[];
  value: number;
  unit: MeasurementUnit;
  label?: string;
  timestamp: Date;
}

interface MeasurementToolsProps {
  onMeasurementStart?: (type: MeasurementType) => void;
  onMeasurementPoint?: (point: Point3D) => void;
  onMeasurementComplete?: (measurement: Measurement) => void;
  onMeasurementDelete?: (id: string) => void;
  defaultUnit?: MeasurementUnit;
}

const UNIT_CONVERSIONS: Record<MeasurementUnit, number> = {
  m: 1,
  cm: 0.01,
  mm: 0.001,
  ft: 0.3048,
  in: 0.0254,
};

export const MeasurementTools: React.FC<MeasurementToolsProps> = ({
  onMeasurementStart,
  onMeasurementPoint,
  onMeasurementComplete,
  onMeasurementDelete,
  defaultUnit = 'm',
}) => {
  const [activeTool, setActiveTool] = useState<MeasurementType | null>(null);
  const [unit, setUnit] = useState<MeasurementUnit>(defaultUnit);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [currentPoints, setCurrentPoints] = useState<Point3D[]>([]);
  const [isMeasuring, setIsMeasuring] = useState(false);
  const measurementIdCounter = useRef(0);

  const generateId = () => {
    measurementIdCounter.current += 1;
    return `meas_${measurementIdCounter.current}`;
  };

  // Calculate distance between two points
  const calculateDistance = (p1: Point3D, p2: Point3D): number => {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const dz = p2.z - p1.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  };

  // Calculate area of polygon (assuming planar)
  const calculateArea = (points: Point3D[]): number => {
    if (points.length < 3) return 0;

    // Use shoelace formula projected onto best-fit plane
    // Simplified: project onto XY plane
    let area = 0;
    const n = points.length;

    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      area += points[i].x * points[j].y;
      area -= points[j].x * points[i].y;
    }

    return Math.abs(area) / 2;
  };

  // Calculate angle between three points
  const calculateAngle = (p1: Point3D, p2: Point3D, p3: Point3D): number => {
    const v1 = { x: p1.x - p2.x, y: p1.y - p2.y, z: p1.z - p2.z };
    const v2 = { x: p3.x - p2.x, y: p3.y - p2.y, z: p3.z - p2.z };

    const dot = v1.x * v2.x + v1.y * v2.y + v1.z * v2.z;
    const mag1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y + v1.z * v1.z);
    const mag2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y + v2.z * v2.z);

    if (mag1 === 0 || mag2 === 0) return 0;

    const cosAngle = dot / (mag1 * mag2);
    return Math.acos(Math.max(-1, Math.min(1, cosAngle))) * (180 / Math.PI);
  };

  const handleToolSelect = useCallback(
    (type: MeasurementType) => {
      setActiveTool(type);
      setCurrentPoints([]);
      setIsMeasuring(true);
      onMeasurementStart?.(type);
    },
    [onMeasurementStart]
  );

  const handlePointAdd = useCallback(
    (point: Point3D) => {
      if (!activeTool || !isMeasuring) return;

      const newPoints = [...currentPoints, point];
      setCurrentPoints(newPoints);
      onMeasurementPoint?.(point);

      // Check if measurement is complete
      if (activeTool === 'distance' && newPoints.length === 2) {
        const distance = calculateDistance(newPoints[0], newPoints[1]);
        const measurement: Measurement = {
          id: generateId(),
          type: 'distance',
          points: newPoints,
          value: distance / UNIT_CONVERSIONS[unit],
          unit,
          timestamp: new Date(),
        };
        setMeasurements((prev) => [...prev, measurement]);
        onMeasurementComplete?.(measurement);
        setCurrentPoints([]);
        setIsMeasuring(false);
      } else if (activeTool === 'area' && newPoints.length >= 3) {
        // Allow completing area measurement by clicking first point again
        const firstPoint = newPoints[0];
        const lastPoint = newPoints[newPoints.length - 1];
        const distToFirst = calculateDistance(lastPoint, firstPoint);

        if (distToFirst < 0.1 && newPoints.length > 3) {
          // Close the polygon
          const area = calculateArea(newPoints.slice(0, -1));
          const measurement: Measurement = {
            id: generateId(),
            type: 'area',
            points: newPoints.slice(0, -1),
            value: area / (UNIT_CONVERSIONS[unit] * UNIT_CONVERSIONS[unit]),
            unit,
            timestamp: new Date(),
          };
          setMeasurements((prev) => [...prev, measurement]);
          onMeasurementComplete?.(measurement);
          setCurrentPoints([]);
          setIsMeasuring(false);
        }
      } else if (activeTool === 'angle' && newPoints.length === 3) {
        const angle = calculateAngle(newPoints[0], newPoints[1], newPoints[2]);
        const measurement: Measurement = {
          id: generateId(),
          type: 'angle',
          points: newPoints,
          value: angle,
          unit,
          timestamp: new Date(),
        };
        setMeasurements((prev) => [...prev, measurement]);
        onMeasurementComplete?.(measurement);
        setCurrentPoints([]);
        setIsMeasuring(false);
      }
    },
    [activeTool, currentPoints, isMeasuring, onMeasurementComplete, onMeasurementPoint, unit]
  );

  const handleDelete = useCallback(
    (id: string) => {
      setMeasurements((prev) => prev.filter((m) => m.id !== id));
      onMeasurementDelete?.(id);
    },
    [onMeasurementDelete]
  );

  const handleClearAll = useCallback(() => {
    setMeasurements([]);
    setCurrentPoints([]);
    setIsMeasuring(false);
  }, []);

  const handleUndo = useCallback(() => {
    if (currentPoints.length > 0) {
      setCurrentPoints((prev) => prev.slice(0, -1));
    } else if (measurements.length > 0) {
      const lastMeasurement = measurements[measurements.length - 1];
      handleDelete(lastMeasurement.id);
    }
  }, [currentPoints.length, measurements, handleDelete]);

  const formatValue = (measurement: Measurement): string => {
    switch (measurement.type) {
      case 'distance':
        return `${measurement.value.toFixed(3)} ${measurement.unit}`;
      case 'area':
        return `${measurement.value.toFixed(3)} ${measurement.unit}²`;
      case 'angle':
        return `${measurement.value.toFixed(1)}°`;
      default:
        return measurement.value.toString();
    }
  };

  const getMeasurementIcon = (type: MeasurementType) => {
    switch (type) {
      case 'distance':
        return <DistanceIcon />;
      case 'area':
        return <AreaIcon />;
      case 'angle':
        return <AngleIcon />;
    }
  };

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom>
          Measurement Tools
        </Typography>

        {/* Tool Selection */}
        <ToggleButtonGroup
          value={activeTool}
          exclusive
          onChange={(_, value) => value && handleToolSelect(value)}
          fullWidth
          sx={{ mb: 2 }}
        >
          <ToggleButton value="distance">
            <Tooltip title="Distance">
              <DistanceIcon />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="area">
            <Tooltip title="Area">
              <AreaIcon />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="angle">
            <Tooltip title="Angle">
              <AngleIcon />
            </Tooltip>
          </ToggleButton>
        </ToggleButtonGroup>

        {/* Unit Selection */}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 80 }}>
            <InputLabel>Unit</InputLabel>
            <Select value={unit} onChange={(e) => setUnit(e.target.value as MeasurementUnit)} label="Unit">
              <MenuItem value="m">m</MenuItem>
              <MenuItem value="cm">cm</MenuItem>
              <MenuItem value="mm">mm</MenuItem>
              <MenuItem value="ft">ft</MenuItem>
              <MenuItem value="in">in</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ flexGrow: 1 }} />

          <Tooltip title="Undo">
            <IconButton onClick={handleUndo} size="small">
              <UndoIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Clear All">
            <IconButton onClick={handleClearAll} size="small" color="error">
              <ClearIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Current Measurement Status */}
        {isMeasuring && (
          <Box sx={{ mt: 2, p: 1, bgcolor: 'primary.light', borderRadius: 1 }}>
            <Typography variant="body2" color="primary.contrastText">
              {activeTool === 'distance' && 'Click two points to measure distance'}
              {activeTool === 'area' && `Click points to define area (${currentPoints.length} points). Click first point to close.`}
              {activeTool === 'angle' && 'Click three points to measure angle (vertex second)'}
            </Typography>
            {currentPoints.length > 0 && (
              <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                Points: {currentPoints.length}
              </Typography>
            )}
          </Box>
        )}
      </Box>

      {/* Measurements List */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {measurements.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <DistanceIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography color="text.secondary">
              No measurements yet. Select a tool and click in the 3D view to measure.
            </Typography>
          </Box>
        ) : (
          <List>
            {measurements.map((measurement, index) => (
              <React.Fragment key={measurement.id}>
                <ListItem>
                  <ListItemIcon>{getMeasurementIcon(measurement.type)}</ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body1" fontWeight="medium">
                          {formatValue(measurement)}
                        </Typography>
                        <Chip
                          label={measurement.type}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                    }
                    secondary={`${measurement.points.length} points • ${measurement.timestamp.toLocaleTimeString()}`}
                  />
                  <ListItemSecondaryAction>
                    <Tooltip title="Copy value">
                      <IconButton
                        edge="end"
                        onClick={() => navigator.clipboard.writeText(formatValue(measurement))}
                        size="small"
                      >
                        <CopyIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        edge="end"
                        onClick={() => handleDelete(measurement.id)}
                        size="small"
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        )}
      </Box>

      {/* Summary */}
      {measurements.length > 0 && (
        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider', bgcolor: 'grey.50' }}>
          <Typography variant="subtitle2" gutterBottom>
            Summary
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip
              icon={<DistanceIcon />}
              label={`${measurements.filter((m) => m.type === 'distance').length} Distances`}
              size="small"
            />
            <Chip
              icon={<AreaIcon />}
              label={`${measurements.filter((m) => m.type === 'area').length} Areas`}
              size="small"
            />
            <Chip
              icon={<AngleIcon />}
              label={`${measurements.filter((m) => m.type === 'angle').length} Angles`}
              size="small"
            />
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default MeasurementTools;
