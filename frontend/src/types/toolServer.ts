export interface StandaloneToolDef {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ToolServer {
  id: string;
  name: string;
  type: 'mcp_stdio' | 'standalone';
  command: string | null;
  args: string[];
  env_keys: string[];
  tools: StandaloneToolDef[];
  description: string;
  tags: string[];
  enabled: boolean;
  tool_count: number | null;
}

export interface CreateToolServerRequest {
  name: string;
  type: 'mcp_stdio' | 'standalone';
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  tools?: StandaloneToolDef[];
  description?: string;
  tags?: string[];
  enabled?: boolean;
}

export type UpdateToolServerRequest = Partial<CreateToolServerRequest>;
