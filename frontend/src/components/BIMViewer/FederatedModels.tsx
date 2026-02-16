"""
FederatedModels.tsx - Multi-discipline model merging for BIM
"""

import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Button,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Tooltip,
  Checkbox,
  FormControlLabel,
  Alert,
} from '@mui/material';
import {
  MergeType as MergeIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  ColorLens as ColorIcon,
  Transform as TransformIcon,
  Upload as UploadIcon,
  Architecture as ArchitectureIcon,
  ElectricalServices as MepIcon,
  Landscape as LandscapeIcon,
  Engineering as StructuralIcon,
} from '@mui/icons-material';

// Types
interface ModelDiscipline {
  id: string;
  name: string;
  discipline: 'architectural' | 'structural' | 'mep' | 'landscape' | 'other';
  fileName: string;
  fileSize: number;
  uploadDate: string;
  color: string;
  visible: boolean;
  opacity: number;
  transform: {
    x: number;
    y: number;
    z: number;
    rotationX: number;
    rotationY: number;
    rotationZ: number;
    scale: number;
  };
  elementCount: number;
  isAligned: boolean;
}

interface FederatedModelsProps {
  models: ModelDiscipline[];
  onModelsChange?: (models: ModelDiscipline[]) => void;
  onModelUpload?: (file: File, discipline: string) => Promise<ModelDiscipline>;
  onModelDelete?: (modelId: string) => void;
  onModelVisibilityChange?: (modelId: string, visible: boolean) => void;
  onModelTransformChange?: (modelId: string, transform: ModelDiscipline['transform']) => void;
  onMerge?: (modelIds: string[]) => Promise<void>;
}

const DISCIPLINE_COLORS: Record<string, string> = {
  architectural: '#4CAF50',
  structural: '#2196F3',
  mep: '#FF9800',
  landscape: '#8BC34A',
  other: '#9E9E9E',
};

const DISCIPLINE_ICONS: Record<string, React.ElementType> = {
  architectural: ArchitectureIcon,
  structural: StructuralIcon,
  mep: MepIcon,
  landscape: LandscapeIcon,
  other: ArchitectureIcon,
};

export const FederatedModels: React.FC<FederatedModelsProps> = ({
  models,
  onModelsChange,
  onModelUpload,
  onModelDelete,
  onModelVisibilityChange,
  onModelTransformChange,
  onMerge,
}) => {
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set());
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showTransformDialog, setShowTransformDialog] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelDiscipline | null>(null);
  const [uploadDiscipline, setUploadDiscipline] = useState('architectural');
  const [isMerging, setIsMerging] = useState(false);

  const handleModelSelect = useCallback((modelId: string) => {
    setSelectedModels((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(modelId)) {
        newSet.delete(modelId);
      } else {
        newSet.add(modelId);
      }
      return newSet;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedModels.size === models.length) {
      setSelectedModels(new Set());
    } else {
      setSelectedModels(new Set(models.map((m) => m.id)));
    }
  }, [models, selectedModels.size]);

  const handleVisibilityToggle = useCallback((modelId: string) => {
    const model = models.find((m) => m.id === modelId);
    if (model) {
      onModelVisibilityChange?.(modelId, !model.visible);
    }
  }, [models, onModelVisibilityChange]);

  const handleTransformEdit = useCallback((model: ModelDiscipline) => {
    setEditingModel(model);
    setShowTransformDialog(true);
  }, []);

  const handleTransformSave = useCallback((transform: ModelDiscipline['transform']) => {
    if (editingModel) {
      onModelTransformChange?.(editingModel.id, transform);
      setShowTransformDialog(false);
      setEditingModel(null);
    }
  }, [editingModel, onModelTransformChange]);

  const handleMerge = useCallback(async () => {
    if (selectedModels.size < 2) return;

    setIsMerging(true);
    try {
      await onMerge?.(Array.from(selectedModels));
    } finally {
      setIsMerging(false);
    }
  }, [selectedModels, onMerge]);

  const handleFileUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file && onModelUpload) {
        await onModelUpload(file, uploadDiscipline);
        setShowUploadDialog(false);
      }
    },
    [onModelUpload, uploadDiscipline]
  );

  const disciplineCounts = models.reduce((acc, model) => {
    acc[model.discipline] = (acc[model.discipline] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const totalElements = models.reduce((sum, model) => sum + model.elementCount, 0);

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom>
          Federated Models
        </Typography>

        {/* Summary */}
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          <Chip label={`${models.length} Models`} color="primary" size="small" />
          <Chip label={`${totalElements.toLocaleString()} Elements`} size="small" />
          {Object.entries(disciplineCounts).map(([discipline, count]) => (
            <Chip
              key={discipline}
              label={`${discipline}: ${count}`}
              size="small"
              sx={{ backgroundColor: DISCIPLINE_COLORS[discipline], color: 'white' }}
            />
          ))}
        </Box>

        {/* Actions */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => setShowUploadDialog(true)}
            size="small"
          >
            Add Model
          </Button>
          <Button
            variant="outlined"
            startIcon={<MergeIcon />}
            onClick={handleMerge}
            disabled={selectedModels.size < 2 || isMerging}
            size="small"
          >
            {isMerging ? 'Merging...' : `Merge (${selectedModels.size})`}
          </Button>
          <Button
            variant="outlined"
            onClick={handleSelectAll}
            size="small"
          >
            {selectedModels.size === models.length ? 'Deselect All' : 'Select All'}
          </Button>
        </Box>
      </Box>

      {/* Model List */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {models.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <ArchitectureIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography color="text.secondary">
              No models loaded. Add models to create a federated view.
            </Typography>
          </Box>
        ) : (
          <List>
            {models.map((model) => {
              const DisciplineIcon = DISCIPLINE_ICONS[model.discipline];
              const isSelected = selectedModels.has(model.id);

              return (
                <React.Fragment key={model.id}>
                  <ListItem
                    selected={isSelected}
                    onClick={() => handleModelSelect(model.id)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <ListItemIcon>
                      <Checkbox checked={isSelected} />
                    </ListItemIcon>
                    <ListItemIcon>
                      <DisciplineIcon sx={{ color: model.color }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={model.name}
                      secondary={
                        <Box>
                          <Typography variant="caption" display="block">
                            {model.discipline.charAt(0).toUpperCase() +
                              model.discipline.slice(1)}{' '}
                            • {model.elementCount.toLocaleString()} elements
                          </Typography>
                          <Typography variant="caption" display="block" color="text.secondary">
                            {!model.isAligned && (
                              <Alert severity="warning" sx={{ py: 0, mt: 1 }}>
                                Not aligned
                              </Alert>
                            )}
                          </Typography>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title={model.visible ? 'Hide' : 'Show'}>
                        <IconButton
                          edge="end"
                          onClick={() => handleVisibilityToggle(model.id)}
                        >
                          {model.visible ? <VisibilityIcon /> : <VisibilityOffIcon />}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Transform">
                        <IconButton edge="end" onClick={() => handleTransformEdit(model)}>
                          <TransformIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          edge="end"
                          onClick={() => onModelDelete?.(model.id)}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </ListItem>
                  <Divider />
                </React.Fragment>
              );
            })}
          </List>
        )}
      </Box>

      {/* Upload Dialog */}
      <Dialog open={showUploadDialog} onClose={() => setShowUploadDialog(false)}>
        <DialogTitle>Add Model</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Discipline</InputLabel>
            <Select
              value={uploadDiscipline}
              onChange={(e) => setUploadDiscipline(e.target.value)}
              label="Discipline"
            >
              <MenuItem value="architectural">Architectural</MenuItem>
              <MenuItem value="structural">Structural</MenuItem>
              <MenuItem value="mep">MEP</MenuItem>
              <MenuItem value="landscape">Landscape</MenuItem>
              <MenuItem value="other">Other</MenuItem>
            </Select>
          </FormControl>
          <Box sx={{ mt: 2 }}>
            <input
              accept=".ifc"
              type="file"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              id="model-upload-input"
            />
            <label htmlFor="model-upload-input">
              <Button variant="outlined" component="span" fullWidth>
                Select IFC File
              </Button>
            </label>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowUploadDialog(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* Transform Dialog */}
      <Dialog
        open={showTransformDialog}
        onClose={() => setShowTransformDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Transform Model</DialogTitle>
        <DialogContent>
          {editingModel && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
              <Typography variant="subtitle2">Translation</Typography>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="X"
                  type="number"
                  value={editingModel.transform.x}
                  onChange={(e) =>
                    setEditingModel({
                      ...editingModel,
                      transform: { ...editingModel.transform, x: parseFloat(e.target.value) },
                    })
                  }
                  size="small"
                />
                <TextField
                  label="Y"
                  type="number"
                  value={editingModel.transform.y}
                  onChange={(e) =>
                    setEditingModel({
                      ...editingModel,
                      transform: { ...editingModel.transform, y: parseFloat(e.target.value) },
                    })
                  }
                  size="small"
                />
                <TextField
                  label="Z"
                  type="number"
                  value={editingModel.transform.z}
                  onChange={(e) =>
                    setEditingModel({
                      ...editingModel,
                      transform: { ...editingModel.transform, z: parseFloat(e.target.value) },
                    })
                  }
                  size="small"
                />
              </Box>

              <Typography variant="subtitle2">Rotation (degrees)</Typography>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="X"
                  type="number"
                  value={editingModel.transform.rotationX}
                  onChange={(e) =>
                    setEditingModel({
                      ...editingModel,
                      transform: {
                        ...editingModel.transform,
                        rotationX: parseFloat(e.target.value),
                      },
                    })
                  }
                  size="small"
                />
                <TextField
                  label="Y"
                  type="number"
                  value={editingModel.transform.rotationY}
                  onChange={(e) =>
                    setEditingModel({
                      ...editingModel,
                      transform: {
                        ...editingModel.transform,
                        rotationY: parseFloat(e.target.value),
                      },
                    })
                  }
                  size="small"
                />
                <TextField
                  label="Z"
                  type="number"
                  value={editingModel.transform.rotationZ}
                  onChange={(e) =>
                    setEditingModel({
                      ...editingModel,
                      transform: {
                        ...editingModel.transform,
                        rotationZ: parseFloat(e.target.value),
                      },
                    })
                  }
                  size="small"
                />
              </Box>

              <Typography variant="subtitle2">Scale</Typography>
              <Slider
                value={editingModel.transform.scale}
                min={0.1}
                max={10}
                step={0.1}
                onChange={(_, value) =>
                  setEditingModel({
                    ...editingModel,
                    transform: { ...editingModel.transform, scale: value as number },
                  })
                }
                valueLabelDisplay="auto"
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTransformDialog(false)}>Cancel</Button>
          <Button
            onClick={() => editingModel && handleTransformSave(editingModel.transform)}
            variant="contained"
          >
            Apply
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default FederatedModels;
