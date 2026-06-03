export interface Harness {
  id: string;
  name: string;
  type: 'builtin' | 'subprocess';
  binary_path: string | null;
  description: string;
  supported_features: string[];
  output_format: string | null;
  default: boolean;
  enabled: boolean;
  version: string | null;
}
