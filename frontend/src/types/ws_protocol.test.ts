/**
 * WS protocol conformance: validate that FE WS message fixtures satisfy
 * the backend-generated JSON-schema snapshot.
 *
 * If this test fails, the FE WS types have drifted from the backend
 * Pydantic models in backend/app/schemas/ws_chat.py.
 */
import Ajv from 'ajv';
import { describe, expect, it } from 'vitest';

import wsProtocol from './generated/ws_protocol.json';

const ajv = new Ajv({ strict: false });

/**
 * Resolve $ref pointers within a single schema object.
 * Pydantic's model_json_schema() uses local $defs + $ref for nested models.
 */
function resolveRefs(schema: Record<string, unknown>): Record<string, unknown> {
  const defs = (schema.$defs ?? {}) as Record<string, unknown>;
  const resolved = { ...schema };
  delete resolved.$defs;

  if (resolved.properties) {
    const props = { ...(resolved.properties as Record<string, Record<string, unknown>>) };
    for (const [key, prop] of Object.entries(props)) {
      if (prop.$ref && typeof prop.$ref === 'string') {
        const refName = prop.$ref.replace('#/$defs/', '');
        if (defs[refName]) {
          props[key] = defs[refName] as Record<string, unknown>;
        }
      }
    }
    resolved.properties = props;
  }
  return resolved;
}

// Map backend Pydantic class names → FE fixture samples that must validate.
// Each fixture is a minimal valid WS message the FE would construct or consume.

const FIXTURES: Record<string, Record<string, unknown>> = {
  ConnectedMsg: {
    type: 'connected',
    timestamp: '2024-01-01T00:00:00+00:00',
    sender: 'system',
    session_id: 'sess-1',
    data: { session_id: 'sess-1' },
  },
  MessageChunk: {
    type: 'message_chunk',
    timestamp: '2024-01-01T00:00:00+00:00',
    sender: 'agent',
    session_id: 'sess-1',
    data: { content: 'Hello', message_id: 'msg-1' },
  },
  MessageComplete: {
    type: 'message_complete',
    timestamp: '2024-01-01T00:00:00+00:00',
    sender: 'agent',
    session_id: 'sess-1',
    data: { content: 'Hello world', message_id: 'msg-1', tool_calls: [] },
  },
  ToolCallMsg: {
    type: 'tool_call',
    timestamp: '2024-01-01T00:00:00+00:00',
    sender: 'agent',
    session_id: 'sess-1',
    data: { id: 'tc-1', tool_name: 'search', arguments: {} },
  },
  ToolExecutingMsg: {
    type: 'tool_executing',
    timestamp: '2024-01-01T00:00:00+00:00',
    sender: 'system',
    session_id: 'sess-1',
    data: { tool_call_id: 'tc-1', tool_name: 'search' },
  },
  ToolResultMsg: {
    type: 'tool_result',
    timestamp: '2024-01-01T00:00:00+00:00',
    sender: 'system',
    session_id: 'sess-1',
    data: {
      tool_call_id: 'tc-1',
      tool_name: 'search',
      result: 'found 3 results',
      is_error: false,
      duration_ms: 150,
    },
  },
  SessionEndedMsg: {
    type: 'session_ended',
    timestamp: '2024-01-01T00:00:00+00:00',
    sender: 'system',
    session_id: 'sess-1',
    data: { status: 'ended', ended_at: '2024-01-01T00:01:00+00:00' },
  },
  ErrorMsg: {
    type: 'error',
    timestamp: '2024-01-01T00:00:00+00:00',
    sender: 'system',
    session_id: 'sess-1',
    data: { message: 'Something went wrong', code: null },
  },
};

describe('WS protocol conformance', () => {
  const schemas = wsProtocol as Record<string, Record<string, unknown>>;

  it('snapshot contains all expected envelope types', () => {
    const expectedTypes = [
      'ConnectedMsg',
      'MessageChunk',
      'MessageComplete',
      'ToolCallMsg',
      'ToolExecutingMsg',
      'ToolResultMsg',
      'SessionEndedMsg',
      'ErrorMsg',
    ];
    for (const t of expectedTypes) {
      expect(schemas).toHaveProperty(t);
    }
  });

  for (const [name, fixture] of Object.entries(FIXTURES)) {
    it(`${name} fixture validates against backend schema`, () => {
      const rawSchema = schemas[name];
      expect(rawSchema).toBeDefined();
      const schema = resolveRefs(rawSchema!);
      const validate = ajv.compile(schema);
      const valid = validate(fixture);
      if (!valid) {
        throw new Error(
          `${name} fixture failed validation:\n${JSON.stringify(validate.errors, null, 2)}`,
        );
      }
    });
  }

  it('all envelope types have matching FE fixtures', () => {
    for (const name of Object.keys(schemas)) {
      expect(
        Object.keys(FIXTURES),
        `Missing FE fixture for backend envelope type: ${name}`,
      ).toContain(name);
    }
  });

  it('all envelope schemas share base fields (timestamp, sender, session_id)', () => {
    for (const [_name, schema] of Object.entries(schemas)) {
      const props = schema.properties as Record<string, unknown>;
      expect(props).toHaveProperty('timestamp');
      expect(props).toHaveProperty('sender');
      expect(props).toHaveProperty('session_id');
      // type literal discriminator
      expect(props).toHaveProperty('type');
    }
  });
});
