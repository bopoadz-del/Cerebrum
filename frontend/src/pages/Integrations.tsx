import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Avatar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  CloudSync as SyncIcon,
  CheckCircle as ConnectedIcon,
  Error as ErrorIcon,
  Settings as SettingsIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Link as LinkIcon
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { integrationsApi } from '../services/api';

interface Connector {
  id: string;
  name: string;
  description: string;
  category: string;
  icon_url: string;
  status: 'connected' | 'disconnected' | 'error';
  last_sync_at?: string;
  settings?: Record<string, any>;
}

interface WebhookSubscription {
  id: string;
  event_type: string;
  endpoint_url: string;
  is_active: boolean;
  created_at: string;
}

const Integrations: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(0);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [webhookDialogOpen, setWebhookDialogOpen] = useState(false);
  const [newWebhook, setNewWebhook] = useState({ event_type: '', endpoint_url: '' });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const categories = [
    { id: 'all', label: 'All Integrations' },
    { id: 'project_management', label: 'Project Management' },
    { id: 'communication', label: 'Communication' },
    { id: 'accounting', label: 'Accounting' },
    { id: 'storage', label: 'File Storage' },
    { id: 'esignature', label: 'E-Signature' },
    { id: 'crm', label: 'CRM' }
  ];

  useEffect(() => {
    fetchConnectors();
    fetchWebhooks();
  }, []);

  const fetchConnectors = async () => {
    try {
      setLoading(true);
      const response = await integrationsApi.getConnectors();
      setConnectors(response.data);
    } catch (err: any) {
      setError('Failed to load integrations');
    } finally {
      setLoading(false);
    }
  };

  const fetchWebhooks = async () => {
    try {
      const response = await integrationsApi.getWebhooks();
      setWebhooks(response.data);
    } catch (err: any) {
      console.error('Failed to load webhooks');
    }
  };

  const handleConnect = async (connector: Connector) => {
    try {
      const response = await integrationsApi.connect(connector.id);
      if (response.data.auth_url) {
        window.location.href = response.data.auth_url;
      }
    } catch (err: any) {
      setError(`Failed to connect to ${connector.name}`);
    }
  };

  const handleDisconnect = async (connector: Connector) => {
    try {
      await integrationsApi.disconnect(connector.id);
      setSuccess(`${connector.name} disconnected successfully`);
      fetchConnectors();
    } catch (err: any) {
      setError(`Failed to disconnect ${connector.name}`);
    }
  };

  const handleSync = async (connector: Connector) => {
    try {
      await integrationsApi.sync(connector.id);
      setSuccess(`${connector.name} sync started`);
      fetchConnectors();
    } catch (err: any) {
      setError(`Failed to sync ${connector.name}`);
    }
  };

  const handleCreateWebhook = async () => {
    try {
      await integrationsApi.createWebhook(newWebhook);
      setSuccess('Webhook created successfully');
      setWebhookDialogOpen(false);
      setNewWebhook({ event_type: '', endpoint_url: '' });
      fetchWebhooks();
    } catch (err: any) {
      setError('Failed to create webhook');
    }
  };

  const handleDeleteWebhook = async (webhookId: string) => {
    try {
      await integrationsApi.deleteWebhook(webhookId);
      setSuccess('Webhook deleted successfully');
      fetchWebhooks();
    } catch (err: any) {
      setError('Failed to delete webhook');
    }
  };

  const filteredConnectors = activeTab === 0
    ? connectors
    : connectors.filter(c => c.category === categories[activeTab].id);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'success';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return <ConnectedIcon color="success" />;
      case 'error': return <ErrorIcon color="error" />;
      default: return <LinkIcon color="disabled" />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Integrations
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Tabs
        value={activeTab}
        onChange={(_, value) => setActiveTab(value)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ mb: 3 }}
      >
        {categories.map((cat) => (
          <Tab key={cat.id} label={cat.label} />
        ))}
      </Tabs>

      {loading ? (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {filteredConnectors.map((connector) => (
            <Grid item xs={12} sm={6} md={4} key={connector.id}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" mb={2}>
                    <Avatar
                      src={connector.icon_url}
                      alt={connector.name}
                      sx={{ width: 48, height: 48, mr: 2 }}
                    />
                    <Box flex={1}>
                      <Typography variant="h6">{connector.name}</Typography>
                      <Chip
                        size="small"
                        label={connector.status}
                        color={getStatusColor(connector.status) as any}
                        icon={getStatusIcon(connector.status)}
                      />
                    </Box>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {connector.description}
                  </Typography>
                  {connector.last_sync_at && (
                    <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                      Last sync: {new Date(connector.last_sync_at).toLocaleString()}
                    </Typography>
                  )}
                </CardContent>
                <CardActions>
                  {connector.status === 'connected' ? (
                    <>
                      <Button
                        size="small"
                        startIcon={<SyncIcon />}
                        onClick={() => handleSync(connector)}
                      >
                        Sync
                      </Button>
                      <Button
                        size="small"
                        startIcon={<SettingsIcon />}
                        onClick={() => {
                          setSelectedConnector(connector);
                          setConfigDialogOpen(true);
                        }}
                      >
                        Configure
                      </Button>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => handleDisconnect(connector)}
                      >
                        Disconnect
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => handleConnect(connector)}
                    >
                      Connect
                    </Button>
                  )}
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Box mt={4}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5">Webhook Subscriptions</Typography>
          <Button
            variant="contained"
            onClick={() => setWebhookDialogOpen(true)}
          >
            Add Webhook
          </Button>
        </Box>

        <Card>
          <List>
            {webhooks.map((webhook, index) => (
              <React.Fragment key={webhook.id}>
                {index > 0 && <Divider />}
                <ListItem
                  secondaryAction={
                    <IconButton
                      edge="end"
                      onClick={() => handleDeleteWebhook(webhook.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  }
                >
                  <ListItemAvatar>
                    <Avatar>
                      <SyncIcon />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={webhook.event_type}
                    secondary={webhook.endpoint_url}
                  />
                  <Chip
                    size="small"
                    label={webhook.is_active ? 'Active' : 'Inactive'}
                    color={webhook.is_active ? 'success' : 'default'}
                  />
                </ListItem>
              </React.Fragment>
            ))}
            {webhooks.length === 0 && (
              <ListItem>
                <ListItemText
                  primary="No webhooks configured"
                  secondary="Add a webhook to receive real-time notifications"
                />
              </ListItem>
            )}
          </List>
        </Card>
      </Box>

      {/* Webhook Dialog */}
      <Dialog open={webhookDialogOpen} onClose={() => setWebhookDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Webhook Subscription</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Event Type"
            value={newWebhook.event_type}
            onChange={(e) => setNewWebhook({ ...newWebhook, event_type: e.target.value })}
            margin="normal"
            placeholder="e.g., project.created, task.updated"
          />
          <TextField
            fullWidth
            label="Endpoint URL"
            value={newWebhook.endpoint_url}
            onChange={(e) => setNewWebhook({ ...newWebhook, endpoint_url: e.target.value })}
            margin="normal"
            placeholder="https://your-app.com/webhook"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWebhookDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateWebhook} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Connector Config Dialog */}
      <Dialog open={configDialogOpen} onClose={() => setConfigDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedConnector?.name} Configuration
        </DialogTitle>
        <DialogContent>
          {selectedConnector?.settings && (
            <Box mt={2}>
              {Object.entries(selectedConnector.settings).map(([key, value]) => (
                <TextField
                  key={key}
                  fullWidth
                  label={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  value={value as string}
                  margin="normal"
                  disabled
                />
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Integrations;
