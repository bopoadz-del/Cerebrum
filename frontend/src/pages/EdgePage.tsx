import { Fragment, useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Cpu,
  Loader2,
  Plus,
  RefreshCw,
  Server,
} from 'lucide-react';
import { toast } from 'sonner';
import { ModuleHeader } from '@/components/ModuleHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  createDeployment,
  listDeviceDeployments,
  listDeviceHeartbeats,
  listEdgeDevices,
  registerEdgeDevice,
  type EdgeAdapter,
  type EdgeDeployment,
  type EdgeDevice,
  type EdgeHeartbeat,
} from '@/lib/edgeApi';
import { cn } from '@/lib/utils';

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'online':
      return 'default';
    case 'offline':
      return 'destructive';
    case 'degraded':
      return 'outline';
    default:
      return 'secondary';
  }
}

function formatWhen(value: string | null | undefined): string {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function DeviceDetail({ device }: { device: EdgeDevice }) {
  const [loading, setLoading] = useState(true);
  const [heartbeats, setHeartbeats] = useState<EdgeHeartbeat[]>([]);
  const [deployments, setDeployments] = useState<EdgeDeployment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deployOpen, setDeployOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [modelName, setModelName] = useState('site-safety');
  const [modelVersion, setModelVersion] = useState('v1');
  const [adapter, setAdapter] = useState<EdgeAdapter>('mock');
  const [artifactUri, setArtifactUri] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [hb, deps] = await Promise.all([
        listDeviceHeartbeats(device.external_id),
        listDeviceDeployments(device.external_id),
      ]);
      setHeartbeats(hb);
      setDeployments(deps);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load device detail');
    } finally {
      setLoading(false);
    }
  }, [device.external_id]);

  useEffect(() => {
    const timeout = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timeout);
  }, [load]);

  const handleCreateDeployment = async () => {
    if (!modelName.trim() || !modelVersion.trim()) {
      toast.error('Model name and version are required');
      return;
    }
    setCreating(true);
    try {
      await createDeployment({
        external_id: device.external_id,
        model_name: modelName.trim(),
        model_version: modelVersion.trim(),
        adapter,
        artifact_uri: artifactUri.trim() || undefined,
      });
      toast.success('Deployment created');
      setDeployOpen(false);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create deployment');
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading heartbeats and deployments…
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-2 py-2">
        <p className="text-sm text-rose-600">{error}</p>
        <Button variant="outline" size="sm" onClick={() => void load()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-3">
          <CardTitle className="text-sm font-medium">Recent heartbeats</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => void load()}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </CardHeader>
        <CardContent className="pt-0">
          {heartbeats.length === 0 ? (
            <p className="text-sm text-gray-500">No heartbeats yet.</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {heartbeats.map((hb) => (
                <div
                  key={hb.id}
                  className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2 text-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-gray-800">{formatWhen(hb.received_at)}</span>
                    {hb.active_model_version && (
                      <Badge variant="outline">model {hb.active_model_version}</Badge>
                    )}
                  </div>
                  <pre className="mt-1 overflow-x-auto text-[11px] text-gray-600">
                    {JSON.stringify(hb.metrics, null, 0)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-3">
          <CardTitle className="text-sm font-medium">Deployments</CardTitle>
          <Dialog open={deployOpen} onOpenChange={setDeployOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-1.5">
                <Plus className="h-3.5 w-3.5" />
                New
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create deployment</DialogTitle>
                <DialogDescription>
                  Record a model version for {device.name} ({device.external_id}).
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-3 py-2">
                <div className="space-y-1.5">
                  <Label htmlFor="model-name">Model name</Label>
                  <Input
                    id="model-name"
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="model-version">Model version</Label>
                  <Input
                    id="model-version"
                    value={modelVersion}
                    onChange={(e) => setModelVersion(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Adapter</Label>
                  <Select
                    value={adapter}
                    onValueChange={(v) => setAdapter(v as EdgeAdapter)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mock">mock</SelectItem>
                      <SelectItem value="tensorrt">tensorrt</SelectItem>
                      <SelectItem value="yolo">yolo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="artifact-uri">Artifact URI (optional)</Label>
                  <Input
                    id="artifact-uri"
                    value={artifactUri}
                    onChange={(e) => setArtifactUri(e.target.value)}
                    placeholder="s3://… or memory://"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDeployOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={() => void handleCreateDeployment()} disabled={creating}>
                  {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Create
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent className="pt-0">
          {deployments.length === 0 ? (
            <p className="text-sm text-gray-500">No deployments yet.</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {deployments.map((dep) => (
                <div
                  key={dep.id}
                  className="rounded-md border border-gray-100 px-3 py-2 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-gray-900">
                      {dep.model_name}@{dep.model_version}
                    </span>
                    <Badge variant="outline">{dep.status}</Badge>
                  </div>
                  <div className="text-gray-500 flex flex-wrap gap-x-3 gap-y-0.5">
                    <span>adapter {dep.adapter}</span>
                    <span>inferences {dep.inference_count}</span>
                    <span>errors {dep.error_count}</span>
                    {dep.average_latency_ms != null && (
                      <span>avg {dep.average_latency_ms.toFixed(1)} ms</span>
                    )}
                    {dep.latest_drift_score != null && (
                      <span>drift {dep.latest_drift_score.toFixed(3)}</span>
                    )}
                  </div>
                  {dep.retrain_requested_at && (
                    <p className="text-amber-700">
                      Retrain requested {formatWhen(dep.retrain_requested_at)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function EdgePage() {
  const [devices, setDevices] = useState<EdgeDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [externalId, setExternalId] = useState('');
  const [name, setName] = useState('');
  const [deviceType, setDeviceType] = useState('jetson_orin');
  const [softwareVersion, setSoftwareVersion] = useState('');
  const [capabilities, setCapabilities] = useState('vision');

  const loadDevices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listEdgeDevices();
      setDevices(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load edge devices');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => void loadDevices(), 0);
    return () => window.clearTimeout(timeout);
  }, [loadDevices]);

  const handleRegister = async () => {
    if (externalId.trim().length < 3 || !name.trim()) {
      toast.error('External ID (min 3 chars) and name are required');
      return;
    }
    setRegistering(true);
    try {
      await registerEdgeDevice({
        external_id: externalId.trim(),
        name: name.trim(),
        device_type: deviceType.trim() || 'generic',
        software_version: softwareVersion.trim() || undefined,
        capabilities: capabilities
          .split(',')
          .map((c) => c.trim())
          .filter(Boolean),
      });
      toast.success('Device registered');
      setRegisterOpen(false);
      setExternalId('');
      setName('');
      await loadDevices();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div className="min-h-[100dvh] bg-[#f9f9f9]">
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-3">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to chat
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-6xl p-6 md:p-8">
        <ModuleHeader
          title="Edge devices"
          description="Register edge nodes, monitor heartbeats, and track model deployments."
          icon={Cpu}
          iconColor="cyan"
          action={
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => void loadDevices()}>
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                Refresh
              </Button>
              <Dialog open={registerOpen} onOpenChange={setRegisterOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white">
                    <Plus className="h-3.5 w-3.5" />
                    Register device
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Register edge device</DialogTitle>
                    <DialogDescription>
                      Adds a tenant-scoped device to the Cerebrum edge control plane.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-3 py-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="external-id">External ID</Label>
                      <Input
                        id="external-id"
                        value={externalId}
                        onChange={(e) => setExternalId(e.target.value)}
                        placeholder="jetson-gate-01"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="device-name">Display name</Label>
                      <Input
                        id="device-name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Gate camera"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label htmlFor="device-type">Device type</Label>
                        <Input
                          id="device-type"
                          value={deviceType}
                          onChange={(e) => setDeviceType(e.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="sw-version">Software version</Label>
                        <Input
                          id="sw-version"
                          value={softwareVersion}
                          onChange={(e) => setSoftwareVersion(e.target.value)}
                          placeholder="1.0.0"
                        />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="capabilities">Capabilities (comma-separated)</Label>
                      <Input
                        id="capabilities"
                        value={capabilities}
                        onChange={(e) => setCapabilities(e.target.value)}
                        placeholder="vision, telemetry"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setRegisterOpen(false)}>
                      Cancel
                    </Button>
                    <Button
                      onClick={() => void handleRegister()}
                      disabled={registering}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white"
                    >
                      {registering && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Register
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          }
        />

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-20 text-gray-500">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading devices…
          </div>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-start gap-3 py-8">
              <p className="text-sm text-rose-600">{error}</p>
              <Button variant="outline" onClick={() => void loadDevices()}>
                Retry
              </Button>
            </CardContent>
          </Card>
        ) : devices.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
              <Server className="h-10 w-10 text-gray-300" />
              <div>
                <p className="font-medium text-gray-900">No edge devices yet</p>
                <p className="mt-1 text-sm text-gray-500">
                  Register a device to start receiving heartbeats and deployments.
                </p>
              </div>
              <Button
                onClick={() => setRegisterOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                Register device
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8" />
                    <TableHead>Device</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last heartbeat</TableHead>
                    <TableHead>Interval</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {devices.map((device) => {
                    const isOpen = expanded === device.external_id;
                    return (
                      <Fragment key={device.id}>
                        <TableRow
                          className={cn('cursor-pointer', isOpen && 'bg-gray-50')}
                          onClick={() =>
                            setExpanded(isOpen ? null : device.external_id)
                          }
                        >
                          <TableCell>
                            {isOpen ? (
                              <ChevronDown className="h-4 w-4 text-gray-400" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-gray-400" />
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="font-medium text-gray-900">{device.name}</div>
                            <div className="text-xs text-gray-500">{device.external_id}</div>
                          </TableCell>
                          <TableCell className="text-sm text-gray-600">
                            {device.device_type}
                          </TableCell>
                          <TableCell>
                            <Badge variant={statusVariant(device.status)}>
                              {device.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-gray-600">
                            {formatWhen(device.last_heartbeat_at)}
                          </TableCell>
                          <TableCell className="text-sm text-gray-600">
                            {device.heartbeat_interval_seconds}s
                          </TableCell>
                        </TableRow>
                        {isOpen && (
                          <TableRow>
                            <TableCell colSpan={6} className="bg-white px-4 py-4">
                              <DeviceDetail device={device} />
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
