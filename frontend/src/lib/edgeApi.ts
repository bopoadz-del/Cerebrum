const API_URL = import.meta.env.VITE_API_URL || '';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1')
  ? API_URL
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

export type EdgeDeviceStatus = 'provisioning' | 'online' | 'offline' | 'degraded' | string;
export type EdgeAdapter = 'mock' | 'tensorrt' | 'yolo';

export interface EdgeDevice {
  id: string;
  external_id: string;
  name: string;
  device_type: string;
  status: EdgeDeviceStatus;
  software_version: string | null;
  capabilities: string[];
  hardware: Record<string, unknown>;
  last_heartbeat_at: string | null;
  heartbeat_interval_seconds: number;
}

export interface EdgeHeartbeat {
  id: string;
  received_at: string;
  metrics: Record<string, unknown>;
  active_model_version: string | null;
}

export interface EdgeDeployment {
  id: string;
  device_id: string;
  model_name: string;
  model_version: string;
  adapter: string;
  artifact_uri: string | null;
  artifact_sha256: string | null;
  status: string;
  inference_count: number;
  error_count: number;
  average_latency_ms: number | null;
  latest_drift_score: number | null;
  retrain_requested_at: string | null;
}

export interface DeviceRegistrationInput {
  external_id: string;
  name: string;
  device_type?: string;
  software_version?: string;
  capabilities?: string[];
  heartbeat_interval_seconds?: number;
}

export interface DeploymentCreateInput {
  external_id: string;
  model_name: string;
  model_version: string;
  adapter?: EdgeAdapter;
  artifact_uri?: string;
}

async function edgeFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}/edge${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') {
        detail = body.detail;
      } else if (Array.isArray(body?.detail)) {
        detail = body.detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ');
      }
    } catch {
      // keep default detail
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function listEdgeDevices(): Promise<EdgeDevice[]> {
  return edgeFetch<EdgeDevice[]>('/devices');
}

export function registerEdgeDevice(input: DeviceRegistrationInput): Promise<EdgeDevice> {
  return edgeFetch<EdgeDevice>('/devices/register', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function listDeviceHeartbeats(
  externalId: string,
  limit = 20,
): Promise<EdgeHeartbeat[]> {
  return edgeFetch<EdgeHeartbeat[]>(
    `/devices/${encodeURIComponent(externalId)}/heartbeats?limit=${limit}`,
  );
}

export function listDeviceDeployments(externalId: string): Promise<EdgeDeployment[]> {
  return edgeFetch<EdgeDeployment[]>(
    `/devices/${encodeURIComponent(externalId)}/deployments`,
  );
}

export function createDeployment(input: DeploymentCreateInput): Promise<EdgeDeployment> {
  return edgeFetch<EdgeDeployment>('/deployments', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}
