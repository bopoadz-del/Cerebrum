"""
MetadataInspector.tsx - Property sidebar for BIM element inspection
"""

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Search as SearchIcon,
  ContentCopy as CopyIcon,
  Info as InfoIcon,
  Category as CategoryIcon,
  Straighten as MeasureIcon,
  Palette as MaterialIcon,
  Class as ClassificationIcon,
} from '@mui/icons-material';

// Types
interface PropertyValue {
  name: string;
  value: any;
  unit?: string;
  description?: string;
  property_type?: string;
}

interface PropertySet {
  name: string;
  description?: string;
  properties: PropertyValue[];
}

interface ElementMetadata {
  element_id: string;
  global_id: string;
  element_type: string;
  name: string;
  description?: string;
  property_sets: PropertySet[];
  quantity_sets: PropertySet[];
  material_info: {
    name?: string;
    category?: string;
    layers?: Array<{ material: string; thickness: number }>;
  };
  classification: {
    reference?: string;
    name?: string;
    source?: string;
  };
}

interface MetadataInspectorProps {
  metadata: ElementMetadata | null;
  onPropertyClick?: (property: PropertyValue) => void;
  onCopyValue?: (value: string) => void;
  expandedByDefault?: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index} style={{ height: '100%', overflow: 'auto' }}>
    {value === index && <Box sx={{ p: 2 }}>{children}</Box>}
  </div>
);

// Format property value for display
const formatValue = (value: any): string => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

// Property set accordion component
const PropertySetAccordion: React.FC<{
  propertySet: PropertySet;
  searchQuery: string;
  onCopyValue: (value: string) => void;
}> = ({ propertySet, searchQuery, onCopyValue }) => {
  const filteredProperties = propertySet.properties.filter(prop =>
    prop.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    formatValue(prop.value).toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (filteredProperties.length === 0) return null;

  return (
    <Accordion defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CategoryIcon fontSize="small" color="primary" />
          <Typography variant="subtitle2">{propertySet.name}</Typography>
          <Chip
            label={`${filteredProperties.length} properties`}
            size="small"
            variant="outlined"
          />
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Property</TableCell>
                <TableCell>Value</TableCell>
                <TableCell width={50} />
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredProperties.map((prop) => (
                <TableRow key={prop.name} hover>
                  <TableCell>
                    <Tooltip title={prop.description || ''}>
                      <Typography variant="body2">{prop.name}</Typography>
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {formatValue(prop.value)}
                      {prop.unit && (
                        <Typography component="span" variant="caption" color="text.secondary">
                          {' '}{prop.unit}
                        </Typography>
                      )}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Copy value">
                      <IconButton
                        size="small"
                        onClick={() => onCopyValue(formatValue(prop.value))}
                      >
                        <CopyIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </AccordionDetails>
    </Accordion>
  );
};

export const MetadataInspector: React.FC<MetadataInspectorProps> = ({
  metadata,
  onPropertyClick,
  onCopyValue,
  expandedByDefault = true,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  if (!metadata) {
    return (
      <Paper elevation={2} sx={{ height: '100%', p: 3, textAlign: 'center' }}>
        <InfoIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography color="text.secondary">
          Select an element to view its properties
        </Typography>
      </Paper>
    );
  }

  const handleCopy = (value: string) => {
    navigator.clipboard.writeText(value);
    onCopyValue?.(value);
  };

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" noWrap>
          {metadata.name || 'Unnamed Element'}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
          <Chip
            label={metadata.element_type}
            color="primary"
            size="small"
          />
          <Chip
            label={metadata.global_id.substring(0, 8) + '...'}
            variant="outlined"
            size="small"
            onDelete={() => handleCopy(metadata.global_id)}
            deleteIcon={<CopyIcon />}
          />
        </Box>
      </Box>

      {/* Search */}
      <Box sx={{ px: 2, py: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search properties..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onChange={(_, newValue) => setActiveTab(newValue)}
        variant="scrollable"
        scrollButtons="auto"
      >
        <Tab label="Properties" icon={<CategoryIcon />} iconPosition="start" />
        <Tab label="Quantities" icon={<MeasureIcon />} iconPosition="start" />
        <Tab label="Material" icon={<MaterialIcon />} iconPosition="start" />
        <Tab label="Classification" icon={<ClassificationIcon />} iconPosition="start" />
      </Tabs>

      {/* Properties Tab */}
      <TabPanel value={activeTab} index={0}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {metadata.property_sets.length === 0 ? (
            <Typography color="text.secondary" align="center">
              No property sets available
            </Typography>
          ) : (
            metadata.property_sets.map((pset) => (
              <PropertySetAccordion
                key={pset.name}
                propertySet={pset}
                searchQuery={searchQuery}
                onCopyValue={handleCopy}
              />
            ))
          )}
        </Box>
      </TabPanel>

      {/* Quantities Tab */}
      <TabPanel value={activeTab} index={1}>
        {metadata.quantity_sets.length === 0 ? (
          <Typography color="text.secondary" align="center">
            No quantity sets available
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Quantity</TableCell>
                  <TableCell>Value</TableCell>
                  <TableCell>Unit</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {metadata.quantity_sets.flatMap((qset) =>
                  qset.properties
                    .filter((q) =>
                      q.name.toLowerCase().includes(searchQuery.toLowerCase())
                    )
                    .map((q) => (
                      <TableRow key={`${qset.name}-${q.name}`} hover>
                        <TableCell>
                          <Typography variant="body2">{q.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {qset.name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {formatValue(q.value)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={q.unit || '-'} size="small" variant="outlined" />
                        </TableCell>
                      </TableRow>
                    ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </TabPanel>

      {/* Material Tab */}
      <TabPanel value={activeTab} index={2}>
        <List>
          <ListItem>
            <ListItemIcon>
              <MaterialIcon />
            </ListItemIcon>
            <ListItemText
              primary="Material Name"
              secondary={metadata.material_info.name || 'Not specified'}
            />
          </ListItem>
          <Divider />
          <ListItem>
            <ListItemIcon>
              <CategoryIcon />
            </ListItemIcon>
            <ListItemText
              primary="Category"
              secondary={metadata.material_info.category || 'Not specified'}
            />
          </ListItem>
          {metadata.material_info.layers && (
            <>
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Material Layers"
                  secondary={`${metadata.material_info.layers.length} layers`}
                />
              </ListItem>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Material</TableCell>
                      <TableCell>Thickness</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {metadata.material_info.layers.map((layer, index) => (
                      <TableRow key={index}>
                        <TableCell>{layer.material}</TableCell>
                        <TableCell>{layer.thickness} mm</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </List>
      </TabPanel>

      {/* Classification Tab */}
      <TabPanel value={activeTab} index={3}>
        <List>
          <ListItem>
            <ListItemIcon>
              <ClassificationIcon />
            </ListItemIcon>
            <ListItemText
              primary="Reference"
              secondary={metadata.classification.reference || 'Not classified'}
            />
          </ListItem>
          <Divider />
          <ListItem>
            <ListItemIcon>
              <InfoIcon />
            </ListItemIcon>
            <ListItemText
              primary="Name"
              secondary={metadata.classification.name || 'Not specified'}
            />
          </ListItem>
          <Divider />
          <ListItem>
            <ListItemIcon>
              <CategoryIcon />
            </ListItemIcon>
            <ListItemText
              primary="Source"
              secondary={metadata.classification.source || 'Not specified'}
            />
          </ListItem>
        </List>
      </TabPanel>
    </Paper>
  );
};

export default MetadataInspector;
