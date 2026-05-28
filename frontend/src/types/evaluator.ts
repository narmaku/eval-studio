export interface EvaluatorInfo {
  id: string;
  name: string;
  description: string;
  modes: string[];
  builtin: boolean;
  available: boolean;
  defaults: Record<string, unknown>;
  config_schema: Record<string, unknown>;
}
