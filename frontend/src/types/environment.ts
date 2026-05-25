// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export type EnvironmentType = 'byoe' | 'compose' | 'tmt';
export type EnvironmentStatus = 'idle' | 'provisioning' | 'ready' | 'error' | 'tearing_down';

export interface Environment {
  id: string;
  name: string;
  type: EnvironmentType;
  status: EnvironmentStatus;
  config: EnvironmentConfig;
  health: HealthCheckResult | null;
  created_at: string;
  updated_at: string;
}

export interface EnvironmentConfig {
  type: EnvironmentType;
  ssh?: SSHConfig;
  compose_file?: string;
  tmt_plan?: string;
  health_checks?: HealthCheck[];
}

export interface SSHConfig {
  host: string;
  port: number;
  user: string;
  key_path: string;
}

export interface HealthCheck {
  command: string;
  expect: string;
}

export interface HealthCheckResult {
  healthy: boolean;
  checks: { name: string; passed: boolean; message: string }[];
  checked_at: string;
}

export interface CreateEnvironmentRequest {
  name: string;
  type: EnvironmentType;
  config: EnvironmentConfig;
}
