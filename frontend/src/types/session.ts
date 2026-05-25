// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export type SessionMode = 'live' | 'simulated';
export type SessionStatus = 'active' | 'ended' | 'scoring' | 'completed' | 'failed';
export type MessageSender = 'user' | 'agent' | 'system' | 'judge';

export interface Session {
  id: string;
  evaluation_id: string;
  mode: SessionMode;
  status: SessionStatus;
  environment_id: string | null;
  scenario_id: string | null;
  messages: Message[];
  tool_calls: ToolCall[];
  scores: SessionScore[];
  started_at: string;
  ended_at: string | null;
  turn_count: number;
}

export interface Message {
  id: string;
  sender: MessageSender;
  content: string;
  timestamp: string;
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: unknown;
  duration_ms: number;
  timestamp: string;
}

export interface SessionScore {
  turn_number: number | null; // null means session-level score
  dimensions: Record<string, number>;
  overall: number;
  judge_reasoning: string;
}

export interface CreateSessionRequest {
  evaluation_id: string;
  mode: SessionMode;
  environment_id?: string;
  scenario_id?: string;
}

export interface SendMessageRequest {
  content: string;
}
