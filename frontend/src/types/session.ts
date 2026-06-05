// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export type SessionMode = 'live' | 'simulated';
export type SessionStatus = 'active' | 'ended' | 'scoring' | 'completed' | 'failed';
export type MessageSender = 'user' | 'agent' | 'system' | 'judge';

export interface SessionScores {
  overall: number;
  passed: boolean;
  reasoning: string | null;
  breakdown: Record<string, number> | null;
}

export interface Session {
  id: string;
  evaluation_id: string | null;
  name: string | null;
  mode: SessionMode;
  status: SessionStatus;
  transcript: Record<string, unknown>[] | null;
  agent_config: Record<string, unknown> | null;
  judge_config_snapshot: Record<string, unknown> | null;
  scores: SessionScores | null;
  error: string | null;
  started_at: string;
  ended_at: string | null;
  created_at: string;
}

export interface Message {
  id: string;
  sender: MessageSender;
  content: string;
  timestamp: string;
  tool_calls?: ToolCall[];
}

export type ToolCallStatus = 'pending' | 'executing' | 'completed' | 'error';

export interface ToolCall {
  id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: unknown;
  duration_ms: number;
  timestamp: string;
  message_id?: string;
  status?: ToolCallStatus;
}

export interface SessionScore {
  turn_number: number | null; // null means session-level score
  dimensions: Record<string, number>;
  overall: number;
  judge_reasoning: string;
}

export interface CreateSessionRequest {
  evaluation_id?: string;
  name?: string;
  mode: SessionMode;
  agent_config?: {
    provider_id?: string;
    litellm_model?: string;
    api_base?: string;
    system_prompt?: string;
    evaluator_id?: string;
    tool_server_ids?: string[];
    harness_id?: string;
  };
  judge_config?: {
    provider_id?: string;
  };
  environment_id?: string;
  scenario_id?: string;
}

export interface SendMessageRequest {
  content: string;
}

// --- WebSocket message types ---

export type WsMessageType =
  | 'message_chunk'
  | 'message_complete'
  | 'tool_call'
  | 'tool_executing'
  | 'tool_result'
  | 'score'
  | 'status'
  | 'error';

export interface WsEnvelope {
  type: WsMessageType;
  data: unknown;
  timestamp: string;
  sender: MessageSender;
  session_id: string;
}

export interface WsMessageChunk {
  type: 'message_chunk';
  data: { content: string; message_id: string };
}

export interface WsMessageComplete {
  type: 'message_complete';
  data: { content: string; message_id: string; tool_calls?: ToolCall[] };
}

export interface WsToolCallMessage {
  type: 'tool_call';
  data: ToolCall;
}

export interface WsScoreMessage {
  type: 'score';
  data: SessionScore;
}

export interface WsStatusMessage {
  type: 'status';
  data: { status: SessionStatus };
}

export interface WsToolExecutingMessage {
  type: 'tool_executing';
  data: { tool_call_id: string; tool_name: string };
}

export interface WsToolResultMessage {
  type: 'tool_result';
  data: {
    tool_call_id: string;
    tool_name: string;
    result: string;
    is_error: boolean;
    duration_ms: number;
  };
}

export interface WsErrorMessage {
  type: 'error';
  data: { message: string; code?: string };
}

