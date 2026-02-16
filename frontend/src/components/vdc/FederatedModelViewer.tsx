import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Checkbox,
  Slider,
  Button,
  IconButton,
  Tooltip,
  Divider,
  Chip,
  FormControlLabel,
  Switch,
  LinearProgress,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  FitScreen as FitScreenIcon,
  Layers as LayersIcon,
  ColorLens as ColorIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

interface DisciplineModel {
  id: string;
  name: string;
  discipline: string;
  elementCount: number;
  color: string;
  visible: boolean;
  opacity: number;
  loaded: boolean;
}

interface ModelElement {
  id: string;
  name: string;
  type: string;
  discipline: string;
  visible: boolean;
}

const DISCIPLINE_COLORS: Record<string, string> = {
  architectural: '#E8B4B8',
  structural: '#A8D5BA',
  mep: '#9BB5CE',
  civil: '#D4A574',
  landscape: '#90EE90',
  fire: '#FF6B6B',
  interior: '#DDA0DD',
};

const FederatedModelViewer: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);
  const [models, setModels] = useState<DisciplineModel[]>([
    {
      id: '1',
      name: 'Architecture Model',
      discipline: 'architectural',
      elementCount: 1250,
      color: DISCIPLINE_COLORS.architectural,
      visible: true,
      opacity: 1.0,
      loaded: true,
    },
    {
      id: '2',
      name: 'Structural Model',
      discipline: 'structural',
      elementCount: 890,
      color: DISCIPLINE_COLORS.structural,
      visible: true,
      opacity: 1.0,
      loaded: true,
    },
    {
      id: '3',
      name: 'MEP Model',
      discipline: 'mep',
      elementCount: 2100,
      color: DISCIPLINE_COLORS.mep,
      visible: true,
      opacity: 1.0,
      loaded: true,
    },
  ]);
  const [selectedElements, setSelectedElements] = useState<string[]>([]);
  const [showGrid, setShowGrid] = useState(true);
  const [showAxes, setShowAxes] = useState(true);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    // Simulate loading models
    const timer = setTimeout(() => {
      setLoading(false);
      initializeViewer();
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  const initializeViewer = () => {
    // In production, initialize Three.js or similar 3D library
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Simple 2D representation for demo
    drawScene(ctx);
  };

  const drawScene = (ctx: CanvasRenderingContext2D) => {
    const canvas = ctx.canvas;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = '#e0e0e0';
      ctx.lineWidth = 1;
      for (let i = 0; i < canvas.width; i += 50) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, canvas.height);
        ctx.stroke();
      }
      for (let i = 0; i < canvas.height; i += 50) {
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(canvas.width, i);
        ctx.stroke();
      }
    }

    // Draw axes
    if (showAxes) {
      ctx.strokeStyle = '#ff0000';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(50, canvas.height - 50);
      ctx.lineTo(150, canvas.height - 50);
      ctx.stroke();

      ctx.strokeStyle = '#00ff00';
      ctx.beginPath();
      ctx.moveTo(50, canvas.height - 50);
      ctx.lineTo(50, canvas.height - 150);
      ctx.stroke();

      ctx.fillStyle = '#000';
      ctx.font = '12px Arial';
      ctx.fillText('X', 155, canvas.height - 45);
      ctx.fillText('Y', 45, canvas.height - 155);
    }

    // Draw model representations
    models.forEach((model, index) => {
      if (!model.visible) return;

      const offsetX = 200 + index * 150;
      const offsetY = 150 + index * 50;

      ctx.globalAlpha = model.opacity;
      ctx.fillStyle = model.color;
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 2;

      // Draw building outline
      ctx.beginPath();
      ctx.rect(offsetX, offsetY, 100, 150);
      ctx.fill();
      ctx.stroke();

      // Draw floors
      for (let i = 1; i < 5; i++) {
        ctx.beginPath();
        ctx.moveTo(offsetX, offsetY + i * 30);
        ctx.lineTo(offsetX + 100, offsetY + i * 30);
        ctx.stroke();
      }

      // Label
      ctx.fillStyle = '#000';
      ctx.globalAlpha = 1;
      ctx.font = 'bold 12px Arial';
      ctx.fillText(model.discipline, offsetX, offsetY - 10);
    });
  };

  const handleToggleModel = (modelId: string) => {
    setModels(prev =>
      prev.map(m =>
        m.id === modelId ? { ...m, visible: !m.visible } : m
      )
    );
  };

  const handleOpacityChange = (modelId: string, value: number) => {
    setModels(prev =>
      prev.map(m =>
        m.id === modelId ? { ...m, opacity: value } : m
      )
    );
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, 5));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev / 1.2, 0.2));
  };

  const handleFitToScreen = () => {
    setZoom(1);
  };

  const getVisibleElementCount = () => {
    return models
      .filter(m => m.visible)
      .reduce((sum, m) => sum + m.elementCount, 0);
  };

  return (
    <Box sx={{ display: 'flex', height: '600px' }}>
      {/* Sidebar - Model Controls */}
      <Paper sx={{ width: 300, overflow: 'auto', mr: 2 }}>
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Model Layers
          </Typography>

          <List dense>
            {models.map(model => (
              <React.Fragment key={model.id}>
                <ListItem>
                  <ListItemIcon>
                    <Checkbox
                      edge="start"
                      checked={model.visible}
                      onChange={() => handleToggleModel(model.id)}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Box
                          sx={{
                            width: 16,
                            height: 16,
                            backgroundColor: model.color,
                            mr: 1,
                            border: '1px solid #ccc',
                          }}
                        />
                        {model.name}
                      </Box>
                    }
                    secondary={`${model.elementCount.toLocaleString()} elements`}
                  />
                </ListItem>
                {model.visible && (
                  <ListItem sx={{ pl: 4 }}>
                    <Box sx={{ width: '100%' }}>
                      <Typography variant="caption" display="block">
                        Opacity: {Math.round(model.opacity * 100)}%
                      </Typography>
                      <Slider
                        size="small"
                        value={model.opacity}
                        min={0}
                        max={1}
                        step={0.1}
                        onChange={(_, value) =>
                          handleOpacityChange(model.id, value as number)
                        }
                      />
                    </Box>
                  </ListItem>
                )}
              </React.Fragment>
            ))}
          </List>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle2" gutterBottom>
            View Options
          </Typography>

          <FormControlLabel
            control={
              <Switch
                checked={showGrid}
                onChange={e => setShowGrid(e.target.checked)}
              />
            }
            label="Show Grid"
          />

          <FormControlLabel
            control={
              <Switch
                checked={showAxes}
                onChange={e => setShowAxes(e.target.checked)}
              />
            }
            label="Show Axes"
          />

          <Divider sx={{ my: 2 }} />

          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              icon={<LayersIcon />}
              label={`${getVisibleElementCount().toLocaleString()} elements`}
              size="small"
            />
            <Chip
              icon={<ColorIcon />}
              label={`${models.filter(m => m.visible).length} disciplines`}
              size="small"
            />
          </Box>
        </Box>
      </Paper>

      {/* Main Viewer */}
      <Paper sx={{ flex: 1, position: 'relative' }}>
        {/* Toolbar */}
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            left: 8,
            zIndex: 1,
            display: 'flex',
            gap: 1,
            backgroundColor: 'rgba(255,255,255,0.9)',
            p: 1,
            borderRadius: 1,
          }}
        >
          <Tooltip title="Zoom In">
            <IconButton size="small" onClick={handleZoomIn}>
              <ZoomInIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Zoom Out">
            <IconButton size="small" onClick={handleZoomOut}>
              <ZoomOutIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Fit to Screen">
            <IconButton size="small" onClick={handleFitToScreen}>
              <FitScreenIcon />
            </IconButton>
          </Tooltip>
          <Divider orientation="vertical" flexItem />
          <Typography variant="body2" sx={{ alignSelf: 'center' }}>
            Zoom: {Math.round(zoom * 100)}%
          </Typography>
        </Box>

        {/* Info Panel */}
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 1,
            backgroundColor: 'rgba(255,255,255,0.9)',
            p: 1,
            borderRadius: 1,
          }}
        >
          <Tooltip title="Model Information">
            <IconButton size="small">
              <InfoIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Canvas */}
        {loading ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
            }}
          >
            <LinearProgress sx={{ width: '50%', mb: 2 }} />
            <Typography>Loading federated model...</Typography>
          </Box>
        ) : (
          <canvas
            ref={canvasRef}
            width={800}
            height={600}
            style={{
              width: '100%',
              height: '100%',
              transform: `scale(${zoom})`,
              transformOrigin: 'center center',
            }}
          />
        )}

        {/* Bottom Status Bar */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            backgroundColor: 'rgba(0,0,0,0.7)',
            color: 'white',
            p: 1,
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <Typography variant="caption">
            Federated Model Viewer v1.0
          </Typography>
          <Typography variant="caption">
            {models.filter(m => m.visible).length} of {models.length} models visible
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default FederatedModelViewer;
