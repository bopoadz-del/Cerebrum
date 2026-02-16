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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Alert,
  CircularProgress,
  LinearProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Badge
} from '@mui/material';
import {
  Business as CompanyIcon,
  Assignment as BidIcon,
  Payment as PaymentIcon,
  Assessment as ReportIcon,
  Architecture as DrawingIcon,
  SafetyCheck as SafetyIcon,
  Message as MessageIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  CheckCircle as ApprovedIcon,
  Schedule as PendingIcon,
  Error as RejectedIcon
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { portalApi } from '../services/api';

interface SubcontractorCompany {
  id: string;
  name: string;
  trade_type: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  status: string;
  performance_score?: number;
}

interface BidInvitation {
  id: string;
  project_name: string;
  trade_scope: string;
  bid_due_date: string;
  status: 'invited' | 'submitted' | 'awarded' | 'rejected';
}

interface PaymentApplication {
  id: string;
  application_number: string;
  period: string;
  total_completed: number;
  total_earned: number;
  status: string;
  submitted_at: string;
}

interface DailyReport {
  id: string;
  report_date: string;
  weather_conditions: string;
  manpower_count: number;
  work_completed: string;
  created_at: string;
}

const Subcontractor: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(0);
  const [companies, setCompanies] = useState<SubcontractorCompany[]>([]);
  const [bids, setBids] = useState<BidInvitation[]>([]);
  const [payments, setPayments] = useState<PaymentApplication[]>([]);
  const [dailyReports, setDailyReports] = useState<DailyReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Dialog states
  const [companyDialogOpen, setCompanyDialogOpen] = useState(false);
  const [bidDialogOpen, setBidDialogOpen] = useState(false);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);

  // Form states
  const [newCompany, setNewCompany] = useState({
    name: '',
    trade_type: '',
    contact_name: '',
    contact_email: '',
    contact_phone: ''
  });

  const [newBid, setNewBid] = useState({
    itb_id: '',
    total_price: 0,
    breakdown: [] as any[],
    notes: ''
  });

  const [newPayment, setNewPayment] = useState({
    sov_id: '',
    period_start: '',
    period_end: '',
    line_items: [] as any[]
  });

  const [newReport, setNewReport] = useState({
    report_date: '',
    weather_conditions: '',
    temperature_low: 0,
    temperature_high: 0,
    manpower: [] as any[],
    equipment: [] as any[],
    work_completed: '',
    issues: ''
  });

  const tradeTypes = [
    'General Contractor',
    'Electrical',
    'Plumbing',
    'HVAC',
    'Concrete',
    'Steel',
    'Drywall',
    'Painting',
    'Flooring',
    'Roofing',
    'Landscaping',
    'Other'
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [companiesRes, bidsRes, paymentsRes, reportsRes] = await Promise.all([
        portalApi.getCompanies(),
        portalApi.getBids(),
        portalApi.getPaymentApps(),
        portalApi.getDailyReports()
      ]);
      setCompanies(companiesRes.data);
      setBids(bidsRes.data);
      setPayments(paymentsRes.data);
      setDailyReports(reportsRes.data);
    } catch (err: any) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCompany = async () => {
    try {
      await portalApi.createCompany(newCompany);
      setSuccess('Company added successfully');
      setCompanyDialogOpen(false);
      setNewCompany({
        name: '',
        trade_type: '',
        contact_name: '',
        contact_email: '',
        contact_phone: ''
      });
      fetchData();
    } catch (err: any) {
      setError('Failed to add company');
    }
  };

  const handleSubmitBid = async () => {
    try {
      await portalApi.submitBid(newBid);
      setSuccess('Bid submitted successfully');
      setBidDialogOpen(false);
      fetchData();
    } catch (err: any) {
      setError('Failed to submit bid');
    }
  };

  const handleSubmitPayment = async () => {
    try {
      await portalApi.createPaymentApp(newPayment);
      setSuccess('Payment application submitted successfully');
      setPaymentDialogOpen(false);
      fetchData();
    } catch (err: any) {
      setError('Failed to submit payment application');
    }
  };

  const handleSubmitReport = async () => {
    try {
      await portalApi.createDailyReport(newReport);
      setSuccess('Daily report submitted successfully');
      setReportDialogOpen(false);
      fetchData();
    } catch (err: any) {
      setError('Failed to submit daily report');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'approved':
      case 'awarded':
        return 'success';
      case 'pending':
      case 'submitted':
        return 'warning';
      case 'rejected':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount / 100);
  };

  const renderCompanies = () => (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Subcontractor Companies</Typography>
        <Button
          variant="contained"
          onClick={() => setCompanyDialogOpen(true)}
        >
          Add Company
        </Button>
      </Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Company</TableCell>
              <TableCell>Trade</TableCell>
              <TableCell>Contact</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Performance</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {companies.map((company) => (
              <TableRow key={company.id}>
                <TableCell>
                  <Box display="flex" alignItems="center">
                    <Avatar sx={{ mr: 1 }}>
                      <CompanyIcon />
                    </Avatar>
                    {company.name}
                  </Box>
                </TableCell>
                <TableCell>{company.trade_type}</TableCell>
                <TableCell>
                  <Typography variant="body2">{company.contact_name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {company.contact_email}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={company.status}
                    color={getStatusColor(company.status) as any}
                  />
                </TableCell>
                <TableCell>
                  {company.performance_score && (
                    <Box display="flex" alignItems="center">
                      <LinearProgress
                        variant="determinate"
                        value={company.performance_score}
                        sx={{ width: 60, mr: 1 }}
                      />
                      <Typography variant="body2">
                        {company.performance_score}%
                      </Typography>
                    </Box>
                  )}
                </TableCell>
                <TableCell>
                  <IconButton size="small">
                    <ViewIcon />
                  </IconButton>
                  <IconButton size="small">
                    <EditIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  const renderBids = () => (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Bid Invitations</Typography>
        <Button
          variant="contained"
          onClick={() => setBidDialogOpen(true)}
        >
          Submit Bid
        </Button>
      </Box>
      <Grid container spacing={2}>
        {bids.map((bid) => (
          <Grid item xs={12} md={6} key={bid.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start">
                  <Box>
                    <Typography variant="h6">{bid.project_name}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {bid.trade_scope}
                    </Typography>
                  </Box>
                  <Chip
                    size="small"
                    label={bid.status}
                    color={getStatusColor(bid.status) as any}
                  />
                </Box>
                <Box mt={2}>
                  <Typography variant="body2">
                    <strong>Bid Due:</strong> {new Date(bid.bid_due_date).toLocaleDateString()}
                  </Typography>
                </Box>
              </CardContent>
              <CardActions>
                <Button size="small">View Details</Button>
                {bid.status === 'invited' && (
                  <Button size="small" variant="contained">
                    Submit Bid
                  </Button>
                )}
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );

  const renderPayments = () => (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Payment Applications</Typography>
        <Button
          variant="contained"
          onClick={() => setPaymentDialogOpen(true)}
        >
          New Application
        </Button>
      </Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Application #</TableCell>
              <TableCell>Period</TableCell>
              <TableCell>Total Completed</TableCell>
              <TableCell>Total Earned</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Submitted</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {payments.map((payment) => (
              <TableRow key={payment.id}>
                <TableCell>{payment.application_number}</TableCell>
                <TableCell>{payment.period}</TableCell>
                <TableCell>{formatCurrency(payment.total_completed)}</TableCell>
                <TableCell>{formatCurrency(payment.total_earned)}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={payment.status}
                    color={getStatusColor(payment.status) as any}
                  />
                </TableCell>
                <TableCell>
                  {new Date(payment.submitted_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <IconButton size="small">
                    <ViewIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  const renderDailyReports = () => (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Daily Reports</Typography>
        <Button
          variant="contained"
          onClick={() => setReportDialogOpen(true)}
        >
          Submit Report
        </Button>
      </Box>
      <Grid container spacing={2}>
        {dailyReports.map((report) => (
          <Grid item xs={12} md={6} key={report.id}>
            <Card>
              <CardContent>
                <Typography variant="h6">
                  {new Date(report.report_date).toLocaleDateString()}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Weather: {report.weather_conditions}
                </Typography>
                <Box mt={1}>
                  <Typography variant="body2">
                    <strong>Manpower:</strong> {report.manpower_count} workers
                  </Typography>
                </Box>
                <Typography variant="body2" mt={1}>
                  {report.work_completed.substring(0, 100)}...
                </Typography>
              </CardContent>
              <CardActions>
                <Button size="small">View Full Report</Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Subcontractor Portal
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
        sx={{ mb: 3 }}
      >
        <Tab icon={<CompanyIcon />} label="Companies" />
        <Tab icon={<BidIcon />} label="Bids" />
        <Tab icon={<PaymentIcon />} label="Payments" />
        <Tab icon={<ReportIcon />} label="Daily Reports" />
        <Tab icon={<DrawingIcon />} label="Drawings" />
        <Tab icon={<SafetyIcon />} label="Safety" />
        <Tab icon={<MessageIcon />} label="Messages" />
      </Tabs>

      {activeTab === 0 && renderCompanies()}
      {activeTab === 1 && renderBids()}
      {activeTab === 2 && renderPayments()}
      {activeTab === 3 && renderDailyReports()}
      {activeTab === 4 && <Typography>Drawings - Coming Soon</Typography>}
      {activeTab === 5 && <Typography>Safety - Coming Soon</Typography>}
      {activeTab === 6 && <Typography>Messages - Coming Soon</Typography>}

      {/* Company Dialog */}
      <Dialog open={companyDialogOpen} onClose={() => setCompanyDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Subcontractor Company</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Company Name"
            value={newCompany.name}
            onChange={(e) => setNewCompany({ ...newCompany, name: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            select
            label="Trade Type"
            value={newCompany.trade_type}
            onChange={(e) => setNewCompany({ ...newCompany, trade_type: e.target.value })}
            margin="normal"
          >
            {tradeTypes.map((trade) => (
              <MenuItem key={trade} value={trade}>
                {trade}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            fullWidth
            label="Contact Name"
            value={newCompany.contact_name}
            onChange={(e) => setNewCompany({ ...newCompany, contact_name: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Contact Email"
            value={newCompany.contact_email}
            onChange={(e) => setNewCompany({ ...newCompany, contact_email: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Contact Phone"
            value={newCompany.contact_phone}
            onChange={(e) => setNewCompany({ ...newCompany, contact_phone: e.target.value })}
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCompanyDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateCompany} variant="contained">
            Add Company
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Subcontractor;
