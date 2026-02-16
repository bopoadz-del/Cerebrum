"""
DriveFilePicker.tsx - Google Drive File Browser UI with Recursive Folder Tree
"""

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  TreeView,
  TreeItem,
  Checkbox,
  IconButton,
  Typography,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
  Breadcrumbs,
  Link,
  Paper,
  Divider,
  Button,
  Tooltip,
} from '@mui/material';
import {
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  InsertDriveFile as FileIcon,
  Image as ImageIcon,
  Description as DocIcon,
  TableChart as SpreadsheetIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
  ChevronRight as ChevronRightIcon,
  ExpandMore as ExpandMoreIcon,
  CloudUpload as UploadIcon,
  CloudDownload as DownloadIcon,
} from '@mui/icons-material';
import { useDriveAPI } from '../hooks/useDriveAPI';

// Types
interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  size?: number;
  modifiedTime?: string;
  isFolder: boolean;
  parents: string[];
  webViewLink?: string;
}

interface FolderNode {
  id: string;
  name: string;
  children: (FolderNode | DriveFile)[];
  isLoaded: boolean;
  isLoading: boolean;
}

interface DriveFilePickerProps {
  onSelect?: (files: DriveFile[]) => void;
  onCancel?: () => void;
  multiSelect?: boolean;
  allowedMimeTypes?: string[];
  initialFolderId?: string;
  showUploadButton?: boolean;
  showDownloadButton?: boolean;
  title?: string;
}

// MIME type icon mapping
const getFileIcon = (mimeType: string, isOpen?: boolean) => {
  if (mimeType === 'application/vnd.google-apps.folder') {
    return isOpen ? <FolderOpenIcon color="primary" /> : <FolderIcon color="primary" />;
  }
  if (mimeType.startsWith('image/')) return <ImageIcon color="action" />;
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return <SpreadsheetIcon color="success" />;
  if (mimeType.includes('document') || mimeType.includes('pdf')) return <DocIcon color="info" />;
  return <FileIcon color="action" />;
};

// Format file size
const formatFileSize = (bytes?: number): string => {
  if (!bytes) return '';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

// Format date
const formatDate = (dateString?: string): string => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString();
};

export const DriveFilePicker: React.FC<DriveFilePickerProps> = ({
  onSelect,
  onCancel,
  multiSelect = true,
  allowedMimeTypes,
  initialFolderId = 'root',
  showUploadButton = true,
  showDownloadButton = true,
  title = 'Select Files from Google Drive',
}) => {
  const [folderTree, setFolderTree] = useState<FolderNode | null>(null);
  const [currentFolderId, setCurrentFolderId] = useState<string>(initialFolderId);
  const [currentFiles, setCurrentFiles] = useState<DriveFile[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [expandedNodes, setExpandedNodes] = useState<string[]>([initialFolderId]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [breadcrumbPath, setBreadcrumbPath] = useState<{ id: string; name: string }[]>([
    { id: 'root', name: 'My Drive' },
  ]);

  const { listFiles, getFolderTree, searchFiles, isAuthenticated } = useDriveAPI();

  // Load folder contents
  const loadFolderContents = useCallback(async (folderId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const files = await listFiles(folderId);
      setCurrentFiles(files);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load folder contents');
    } finally {
      setLoading(false);
    }
  }, [listFiles]);

  // Load folder tree
  const loadFolderTree = useCallback(async () => {
    try {
      const tree = await getFolderTree(initialFolderId);
      setFolderTree(tree);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load folder tree');
    }
  }, [getFolderTree, initialFolderId]);

  // Initial load
  useEffect(() => {
    if (isAuthenticated) {
      loadFolderTree();
      loadFolderContents(initialFolderId);
    }
  }, [isAuthenticated, initialFolderId, loadFolderTree, loadFolderContents]);

  // Handle folder click
  const handleFolderClick = async (folderId: string, folderName: string) => {
    setCurrentFolderId(folderId);
    await loadFolderContents(folderId);
    
    // Update breadcrumbs
    const existingIndex = breadcrumbPath.findIndex(b => b.id === folderId);
    if (existingIndex >= 0) {
      setBreadcrumbPath(breadcrumbPath.slice(0, existingIndex + 1));
    } else {
      setBreadcrumbPath([...breadcrumbPath, { id: folderId, name: folderName }]);
    }
  };

  // Handle file selection
  const handleFileSelect = (file: DriveFile) => {
    if (!multiSelect) {
      setSelectedFiles(new Set([file.id]));
      return;
    }

    const newSelected = new Set(selectedFiles);
    if (newSelected.has(file.id)) {
      newSelected.delete(file.id);
    } else {
      newSelected.add(file.id);
    }
    setSelectedFiles(newSelected);
  };

  // Handle select all
  const handleSelectAll = () => {
    if (selectedFiles.size === currentFiles.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(currentFiles.map(f => f.id)));
    }
  };

  // Handle search
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      await loadFolderContents(currentFolderId);
      return;
    }

    setLoading(true);
    try {
      const results = await searchFiles(searchQuery);
      setCurrentFiles(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  // Handle confirm selection
  const handleConfirm = () => {
    const selected = currentFiles.filter(f => selectedFiles.has(f.id));
    onSelect?.(selected);
  };

  // Render tree node
  const renderTreeNode = (node: FolderNode | DriveFile): React.ReactNode => {
    if ('children' in node) {
      // It's a folder node
      return (
        <TreeItem
          key={node.id}
          nodeId={node.id}
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', py: 0.5 }}>
              <FolderIcon sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="body2">{node.name}</Typography>
            </Box>
          }
        >
          {node.children.map(child => renderTreeNode(child))}
        </TreeItem>
      );
    }
    
    // It's a file
    return (
      <TreeItem
        key={node.id}
        nodeId={node.id}
        label={
          <Box sx={{ display: 'flex', alignItems: 'center', py: 0.5 }}>
            {getFileIcon(node.mimeType)}
            <Typography variant="body2" sx={{ ml: 1 }}>
              {node.name}
            </Typography>
          </Box>
        }
      />
    );
  };

  // Filter files by MIME type
  const filteredFiles = allowedMimeTypes
    ? currentFiles.filter(f => 
        allowedMimeTypes.some(type => f.mimeType.includes(type)) || f.isFolder
      )
    : currentFiles;

  if (!isAuthenticated) {
    return (
      <Alert severity="warning">
        Please authenticate with Google Drive first.
      </Alert>
    );
  }

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <TextField
            size="small"
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ flexGrow: 1 }}
          />
          <Tooltip title="Refresh">
            <IconButton onClick={() => loadFolderContents(currentFolderId)}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          {showUploadButton && (
            <Button
              variant="outlined"
              startIcon={<UploadIcon />}
              size="small"
            >
              Upload
            </Button>
          )}
        </Box>
      </Box>

      {/* Breadcrumbs */}
      <Box sx={{ px: 2, py: 1, bgcolor: 'grey.50' }}>
        <Breadcrumbs separator={<ChevronRightIcon fontSize="small" />}>
          {breadcrumbPath.map((crumb, index) => (
            <Link
              key={crumb.id}
              component="button"
              variant="body2"
              onClick={() => handleFolderClick(crumb.id, crumb.name)}
              underline={index === breadcrumbPath.length - 1 ? 'none' : 'hover'}
              color={index === breadcrumbPath.length - 1 ? 'text.primary' : 'inherit'}
              disabled={index === breadcrumbPath.length - 1}
            >
              {crumb.name}
            </Link>
          ))}
        </Breadcrumbs>
      </Box>

      {/* Main Content */}
      <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
        {/* Folder Tree Sidebar */}
        <Box
          sx={{
            width: 280,
            borderRight: 1,
            borderColor: 'divider',
            overflow: 'auto',
            p: 1,
          }}
        >
          <Typography variant="subtitle2" sx={{ mb: 1, px: 1 }}>
            Folders
          </Typography>
          {folderTree && (
            <TreeView
              defaultCollapseIcon={<ExpandMoreIcon />}
              defaultExpandIcon={<ChevronRightIcon />}
              expanded={expandedNodes}
              selected={currentFolderId}
              onNodeToggle={(_, nodeIds) => setExpandedNodes(nodeIds)}
              onNodeSelect={(_, nodeId) => {
                const folder = currentFiles.find(f => f.id === nodeId && f.isFolder);
                if (folder) {
                  handleFolderClick(nodeId, folder.name);
                }
              }}
            >
              {renderTreeNode(folderTree)}
            </TreeView>
          )}
        </Box>

        {/* File List */}
        <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              {/* File List Header */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  p: 1,
                  bgcolor: 'grey.100',
                  borderRadius: 1,
                  mb: 1,
                }}
              >
                {multiSelect && (
                  <Checkbox
                    checked={selectedFiles.size === filteredFiles.length && filteredFiles.length > 0}
                    indeterminate={selectedFiles.size > 0 && selectedFiles.size < filteredFiles.length}
                    onChange={handleSelectAll}
                  />
                )}
                <Typography variant="subtitle2" sx={{ flexGrow: 1, ml: multiSelect ? 0 : 1 }}>
                  Name
                </Typography>
                <Typography variant="subtitle2" sx={{ width: 100 }}>
                  Size
                </Typography>
                <Typography variant="subtitle2" sx={{ width: 120 }}>
                  Modified
                </Typography>
                {showDownloadButton && <Box sx={{ width: 50 }} />}
              </Box>

              {/* File Items */}
              {filteredFiles.map((file) => (
                <Box
                  key={file.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    p: 1,
                    borderRadius: 1,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'grey.50' },
                    bgcolor: selectedFiles.has(file.id) ? 'primary.50' : 'transparent',
                  }}
                  onClick={() => file.isFolder ? handleFolderClick(file.id, file.name) : handleFileSelect(file)}
                >
                  {multiSelect && !file.isFolder && (
                    <Checkbox
                      checked={selectedFiles.has(file.id)}
                      onChange={() => handleFileSelect(file)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  )}
                  {multiSelect && file.isFolder && <Box sx={{ width: 42 }} />}
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1, ml: multiSelect ? 0 : 1 }}>
                    {getFileIcon(file.mimeType)}
                    <Typography variant="body2" sx={{ ml: 1 }}>
                      {file.name}
                    </Typography>
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ width: 100 }}>
                    {formatFileSize(file.size)}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ width: 120 }}>
                    {formatDate(file.modifiedTime)}
                  </Typography>
                  
                  {showDownloadButton && !file.isFolder && (
                    <Tooltip title="Download">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          // Trigger download
                        }}
                      >
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              ))}

              {filteredFiles.length === 0 && !loading && (
                <Box sx={{ textAlign: 'center', p: 4, color: 'text.secondary' }}>
                  <Typography>No files found</Typography>
                </Box>
              )}
            </>
          )}
        </Box>
      </Box>

      {/* Footer */}
      <Divider />
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mr: 'auto', alignSelf: 'center' }}>
          {selectedFiles.size} file(s) selected
        </Typography>
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={selectedFiles.size === 0}
        >
          Select
        </Button>
      </Box>
    </Paper>
  );
};

export default DriveFilePicker;
