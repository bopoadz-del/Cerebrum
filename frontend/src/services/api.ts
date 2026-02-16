import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add tenant ID if available
    const tenantId = localStorage.getItem('tenant_id');
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId;
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle token expiration
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Enterprise API
export const enterpriseApi = {
  // Tenant Management
  getTenants: () => api.get('/enterprise/tenants'),
  createTenant: (data: any) => api.post('/enterprise/tenants', data),
  updateTenant: (id: string, data: any) => api.put(`/enterprise/tenants/${id}`, data),
  deleteTenant: (id: string) => api.delete(`/enterprise/tenants/${id}`),
  
  // SSO
  getSAMLProviders: () => api.get('/enterprise/sso/saml'),
  createSAMLProvider: (data: any) => api.post('/enterprise/sso/saml', data),
  getOIDCProviders: () => api.get('/enterprise/sso/oidc'),
  createOIDCProvider: (data: any) => api.post('/enterprise/sso/oidc', data),
  
  // SCIM
  getSCIMConfig: () => api.get('/enterprise/scim/config'),
  updateSCIMConfig: (data: any) => api.put('/enterprise/scim/config', data),
  
  // Audit Logs
  getAuditLogs: (params?: any) => api.get('/enterprise/audit-logs', { params }),
  
  // Analytics
  getAnalytics: (params?: any) => api.get('/enterprise/analytics', { params }),
  getDashboard: () => api.get('/enterprise/analytics/dashboard'),
  
  // Webhooks
  getWebhooks: () => api.get('/enterprise/webhooks'),
  createWebhook: (data: any) => api.post('/enterprise/webhooks', data),
  deleteWebhook: (id: string) => api.delete(`/enterprise/webhooks/${id}`),
  
  // Security
  getIPAllowlist: () => api.get('/enterprise/security/ip-allowlist'),
  updateIPAllowlist: (data: any) => api.put('/enterprise/security/ip-allowlist', data),
  setup2FA: () => api.post('/enterprise/security/2fa/setup'),
  verify2FA: (code: string) => api.post('/enterprise/security/2fa/verify', { code }),
  
  // Compliance
  getComplianceStatus: () => api.get('/enterprise/compliance/status'),
  getDPADetails: () => api.get('/enterprise/compliance/dpa'),
  
  // Bulk Operations
  bulkExport: (data: any) => api.post('/enterprise/bulk/export', data),
  bulkImport: (data: any) => api.post('/enterprise/bulk/import', data),
};

// Integrations API
export const integrationsApi = {
  // Connectors
  getConnectors: () => api.get('/integrations/connectors'),
  getConnector: (id: string) => api.get(`/integrations/connectors/${id}`),
  connect: (id: string) => api.post(`/integrations/connectors/${id}/connect`),
  disconnect: (id: string) => api.post(`/integrations/connectors/${id}/disconnect`),
  sync: (id: string) => api.post(`/integrations/connectors/${id}/sync`),
  updateConfig: (id: string, data: any) => api.put(`/integrations/connectors/${id}/config`, data),
  
  // Procore
  getProcoreAuthUrl: () => api.get('/integrations/procore/auth'),
  handleProcoreCallback: (code: string) => api.post('/integrations/procore/callback', { code }),
  syncProcoreProjects: () => api.post('/integrations/procore/sync/projects'),
  
  // Slack
  getSlackAuthUrl: () => api.get('/integrations/slack/auth'),
  handleSlackCallback: (code: string) => api.post('/integrations/slack/callback', { code }),
  sendSlackNotification: (data: any) => api.post('/integrations/slack/notify', data),
  
  // ERP
  getERPConnections: () => api.get('/integrations/erp/connections'),
  createERPConnection: (data: any) => api.post('/integrations/erp/connections', data),
  syncChartOfAccounts: (id: string) => api.post(`/integrations/erp/${id}/sync/chart-of-accounts`),
  
  // E-Signature
  getESignatureConnections: () => api.get('/integrations/esignature/connections'),
  createEnvelope: (data: any) => api.post('/integrations/esignature/envelopes', data),
  getEnvelopeStatus: (id: string) => api.get(`/integrations/esignature/envelopes/${id}/status`),
  
  // Zapier
  getZapierTriggers: () => api.get('/integrations/zapier/triggers'),
  getZapierActions: () => api.get('/integrations/zapier/actions'),
  createZapierHook: (data: any) => api.post('/integrations/zapier/hooks', data),
  
  // Microsoft 365
  getMicrosoftAuthUrl: () => api.get('/integrations/microsoft/auth'),
  createTeamsMeeting: (data: any) => api.post('/integrations/microsoft/teams/meeting', data),
  
  // CRM
  getCRMConnections: () => api.get('/integrations/crm/connections'),
  syncToCRM: (provider: string, data: any) => api.post(`/integrations/crm/${provider}/sync`, data),
  
  // Accounting
  getAccountingConnections: () => api.get('/integrations/accounting/connections'),
  createInvoice: (provider: string, data: any) => api.post(`/integrations/accounting/${provider}/invoices`, data),
  
  // File Storage
  getStorageConnections: () => api.get('/integrations/storage/connections'),
  uploadFile: (provider: string, data: any) => api.post(`/integrations/storage/${provider}/upload`, data),
  
  // Webhooks
  getWebhooks: () => api.get('/integrations/webhooks'),
  createWebhook: (data: any) => api.post('/integrations/webhooks', data),
  deleteWebhook: (id: string) => api.delete(`/integrations/webhooks/${id}`),
  regenerateWebhookSecret: (id: string) => api.post(`/integrations/webhooks/${id}/regenerate-secret`),
  
  // API Keys
  getAPIKeys: () => api.get('/integrations/api-keys'),
  createAPIKey: (data: any) => api.post('/integrations/api-keys', data),
  revokeAPIKey: (id: string) => api.delete(`/integrations/api-keys/${id}`),
};

// Portal API
export const portalApi = {
  // Companies
  getCompanies: () => api.get('/portal/companies'),
  getCompany: (id: string) => api.get(`/portal/companies/${id}`),
  createCompany: (data: any) => api.post('/portal/companies', data),
  updateCompany: (id: string, data: any) => api.put(`/portal/companies/${id}`, data),
  
  // ITBs
  getITBs: () => api.get('/portal/itbs'),
  createITB: (data: any) => api.post('/portal/itbs', data),
  
  // Bids
  getBids: () => api.get('/portal/bids'),
  submitBid: (data: any) => api.post('/portal/bids', data),
  getBid: (id: string) => api.get(`/portal/bids/${id}`),
  compareBids: (itbId: string) => api.get(`/portal/itbs/${itbId}/compare-bids`),
  
  // Payment Applications
  getPaymentApps: () => api.get('/portal/payment-apps'),
  createPaymentApp: (data: any) => api.post('/portal/payment-apps', data),
  getPaymentApp: (id: string) => api.get(`/portal/payment-apps/${id}`),
  approvePaymentApp: (id: string, data: any) => api.post(`/portal/payment-apps/${id}/approve`, data),
  
  // Schedule of Values
  getSOVs: () => api.get('/portal/payment-apps/sov'),
  createSOV: (data: any) => api.post('/portal/payment-apps/sov', data),
  
  // Daily Reports
  getDailyReports: () => api.get('/portal/daily-reports'),
  createDailyReport: (data: any) => api.post('/portal/daily-reports', data),
  getDailyReport: (id: string) => api.get(`/portal/daily-reports/${id}`),
  
  // Drawings
  getDrawingSets: () => api.get('/portal/drawings/sets'),
  getDrawings: (setId: string) => api.get(`/portal/drawings/sets/${setId}/drawings`),
  acknowledgeDrawing: (id: string) => api.post(`/portal/drawings/${id}/acknowledge`),
  
  // Submittals
  getSubmittals: () => api.get('/portal/submittals'),
  createSubmittal: (data: any) => api.post('/portal/submittals', data),
  submitSubmittal: (id: string) => api.post(`/portal/submittals/${id}/submit`),
  reviewSubmittal: (id: string, data: any) => api.post(`/portal/submittals/${id}/review`, data),
  
  // RFIs
  getRFIs: () => api.get('/portal/rfis'),
  createRFI: (data: any) => api.post('/portal/rfis', data),
  submitRFI: (id: string) => api.post(`/portal/rfis/${id}/submit`),
  answerRFI: (id: string, data: any) => api.post(`/portal/rfis/${id}/answer`, data),
  closeRFI: (id: string) => api.post(`/portal/rfis/${id}/close`),
  
  // Schedule
  getSchedule: () => api.get('/portal/schedule'),
  getLookahead: (weeks?: number) => api.get('/portal/schedule/lookahead', { params: { weeks } }),
  
  // Safety
  getSafetyMeetings: () => api.get('/portal/safety/meetings'),
  createSafetyMeeting: (data: any) => api.post('/portal/safety/meetings', data),
  getSafetyIncidents: () => api.get('/portal/safety/incidents'),
  reportIncident: (data: any) => api.post('/portal/safety/incidents', data),
  getOSHASummary: () => api.get('/portal/safety/osha-summary'),
  
  // Quality
  getInspections: () => api.get('/portal/quality/inspections'),
  createInspection: (data: any) => api.post('/portal/quality/inspections', data),
  getPunchList: () => api.get('/portal/quality/punch-list'),
  createPunchItem: (data: any) => api.post('/portal/quality/punch-list', data),
  completePunchItem: (id: string, data: any) => api.post(`/portal/quality/punch-list/${id}/complete`, data),
  
  // Transmittals
  getTransmittals: () => api.get('/portal/transmittals'),
  createTransmittal: (data: any) => api.post('/portal/transmittals', data),
  sendTransmittal: (id: string) => api.post(`/portal/transmittals/${id}/send`),
  respondToTransmittal: (id: string, data: any) => api.post(`/portal/transmittals/${id}/respond`, data),
  
  // Change Orders
  getChangeOrders: () => api.get('/portal/change-orders'),
  createChangeOrder: (data: any) => api.post('/portal/change-orders', data),
  submitChangeOrder: (id: string) => api.post(`/portal/change-orders/${id}/submit`),
  submitCOPricing: (id: string, data: any) => api.post(`/portal/change-orders/${id}/pricing`, data),
  
  // Closeout
  getCloseoutItems: () => api.get('/portal/closeout/items'),
  submitCloseoutItem: (id: string, data: any) => api.post(`/portal/closeout/items/${id}/submit`, data),
  getWarranties: () => api.get('/portal/closeout/warranties'),
  createWarranty: (data: any) => api.post('/portal/closeout/warranties', data),
  getLienWaivers: () => api.get('/portal/closeout/lien-waivers'),
  
  // Performance
  getScorecards: () => api.get('/portal/performance/scorecards'),
  getCompanyPerformance: (companyId: string) => api.get(`/portal/performance/companies/${companyId}`),
  getLeaderboard: () => api.get('/portal/performance/leaderboard'),
  
  // Messaging
  getConversations: () => api.get('/portal/messaging/conversations'),
  createConversation: (data: any) => api.post('/portal/messaging/conversations', data),
  getMessages: (conversationId: string) => api.get(`/portal/messaging/conversations/${conversationId}/messages`),
  sendMessage: (data: any) => api.post('/portal/messaging/messages', data),
  getAnnouncements: () => api.get('/portal/messaging/announcements'),
  
  // Time Tracking
  getTimeEntries: () => api.get('/portal/time-tracking/entries'),
  clockIn: (data: any) => api.post('/portal/time-tracking/clock-in', data),
  clockOut: (data: any) => api.post('/portal/time-tracking/clock-out', data),
  createManualEntry: (data: any) => api.post('/portal/time-tracking/entries', data),
  
  // Compliance
  getComplianceDocs: () => api.get('/portal/compliance/documents'),
  uploadComplianceDoc: (data: any) => api.post('/portal/compliance/documents', data),
  getComplianceSummary: () => api.get('/portal/compliance/summary'),
  checkCompliance: (companyId: string) => api.get(`/portal/compliance/check/${companyId}`),
};

// Auth API
export const authApi = {
  login: (email: string, password: string) => 
    api.post('/auth/login', { email, password }),
  
  register: (data: any) => 
    api.post('/auth/register', data),
  
  logout: () => 
    api.post('/auth/logout'),
  
  refreshToken: (refreshToken: string) => 
    api.post('/auth/refresh', { refresh_token: refreshToken }),
  
  forgotPassword: (email: string) => 
    api.post('/auth/forgot-password', { email }),
  
  resetPassword: (token: string, password: string) => 
    api.post('/auth/reset-password', { token, password }),
  
  verifyEmail: (token: string) => 
    api.post('/auth/verify-email', { token }),
  
  getCurrentUser: () => 
    api.get('/auth/me'),
  
  updateProfile: (data: any) => 
    api.put('/auth/me', data),
  
  changePassword: (oldPassword: string, newPassword: string) => 
    api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
  
  // SAML
  initiateSAML: (providerId: string) => 
    api.get(`/auth/saml/${providerId}/login`),
  
  handleSAMLCallback: (providerId: string, data: any) => 
    api.post(`/auth/saml/${providerId}/acs`, data),
  
  // OIDC
  initiateOIDC: (providerId: string) => 
    api.get(`/auth/oidc/${providerId}/login`),
  
  handleOIDCCallback: (providerId: string, code: string) => 
    api.post(`/auth/oidc/${providerId}/callback`, { code }),
};

export default api;
