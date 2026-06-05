import { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToolServerStore } from '@/stores/toolServerStore';
import type { ToolServer, CreateToolServerRequest } from '@/types';

interface ToolServerFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  toolServer?: ToolServer;
  onSaved?: () => void;
}

export function ToolServerForm({ open, onOpenChange, toolServer, onSaved }: ToolServerFormProps) {
  const [formKey, setFormKey] = useState(0);

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) setFormKey((k) => k + 1);
    onOpenChange(nextOpen);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{toolServer ? 'Edit Tool Server' : 'New Tool Server'}</SheetTitle>
        </SheetHeader>
        {open && (
          <ToolServerFormInner
            key={formKey}
            toolServer={toolServer}
            onSaved={onSaved}
            onClose={() => onOpenChange(false)}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}

interface InnerProps {
  toolServer?: ToolServer;
  onSaved?: () => void;
  onClose: () => void;
}

function ToolServerFormInner({ toolServer, onSaved, onClose }: InnerProps) {
  const createToolServer = useToolServerStore((s) => s.createToolServer);
  const updateToolServer = useToolServerStore((s) => s.updateToolServer);
  const isEditMode = !!toolServer;

  const [name, setName] = useState(toolServer?.name ?? '');
  const [type, setType] = useState<'mcp_stdio' | 'standalone'>(toolServer?.type ?? 'mcp_stdio');
  const [command, setCommand] = useState(toolServer?.command ?? '');
  const [argsInput, setArgsInput] = useState(toolServer?.args?.join(', ') ?? '');
  const [envInput, setEnvInput] = useState('');
  const [toolsJson, setToolsJson] = useState(
    toolServer?.tools?.length ? JSON.stringify(toolServer.tools, null, 2) : '[]',
  );
  const [description, setDescription] = useState(toolServer?.description ?? '');
  const [tagsInput, setTagsInput] = useState(toolServer?.tags?.join(', ') ?? '');
  const [enabled, setEnabled] = useState(toolServer?.enabled ?? true);
  const [errors, setErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  const validate = (): boolean => {
    const newErrors: string[] = [];
    if (!name.trim()) newErrors.push('Name is required');
    if (type === 'mcp_stdio' && !command.trim()) newErrors.push('Command is required for MCP servers');
    if (type === 'standalone') {
      try {
        const parsed = JSON.parse(toolsJson);
        if (!Array.isArray(parsed) || parsed.length === 0) {
          newErrors.push('At least one tool definition is required for standalone type');
        }
      } catch {
        newErrors.push('Invalid JSON in tools definition');
      }
    }
    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;
    setIsSaving(true);
    try {
      const args = argsInput
        .split(',')
        .map((a) => a.trim())
        .filter((a) => a.length > 0);
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0);
      const env: Record<string, string> = {};
      envInput.split('\n').forEach((line) => {
        const eqIdx = line.indexOf('=');
        if (eqIdx > 0) {
          env[line.slice(0, eqIdx).trim()] = line.slice(eqIdx + 1).trim();
        }
      });

      let tools: { name: string; description: string; parameters: Record<string, unknown> }[] = [];
      if (type === 'standalone') {
        try {
          tools = JSON.parse(toolsJson);
        } catch {
          tools = [];
        }
      }

      const data: CreateToolServerRequest = {
        name: name.trim(),
        type,
        command: type === 'mcp_stdio' ? command.trim() || null : null,
        args: type === 'mcp_stdio' ? args : [],
        env: type === 'mcp_stdio' ? env : {},
        tools,
        description: description.trim(),
        tags,
        enabled,
      };

      if (isEditMode && toolServer) {
        await updateToolServer(toolServer.id, data);
      } else {
        await createToolServer(data);
      }

      onSaved?.();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error && err.message
          ? err.message
          : 'Failed to save tool server. Please try again.';
      setErrors([message]);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 px-4 pb-4">
      {errors.length > 0 && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {errors.map((e, i) => (
            <p key={i}>{e}</p>
          ))}
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="ts-name">Name</Label>
        <Input id="ts-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g., Filesystem Tools" />
      </div>

      <div className="space-y-2">
        <Label htmlFor="ts-type">Type</Label>
        <Select value={type} onValueChange={(v) => setType(v as 'mcp_stdio' | 'standalone')}>
          <SelectTrigger className="w-full" id="ts-type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="mcp_stdio">MCP Server (stdio)</SelectItem>
            <SelectItem value="standalone">Standalone Tool Definitions</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {type === 'mcp_stdio' && (
        <>
          <div className="space-y-2">
            <Label htmlFor="ts-command">Command</Label>
            <Input id="ts-command" value={command} onChange={(e) => setCommand(e.target.value)} placeholder="e.g., npx" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ts-args">Arguments (comma-separated)</Label>
            <Input
              id="ts-args"
              value={argsInput}
              onChange={(e) => setArgsInput(e.target.value)}
              placeholder="e.g., -y, @modelcontextprotocol/server-filesystem, /tmp"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ts-env">Environment Variables (one KEY=VALUE per line)</Label>
            <Textarea
              id="ts-env"
              value={envInput}
              onChange={(e) => setEnvInput(e.target.value)}
              placeholder={"API_KEY=your-key\nDEBUG=true"}
              rows={3}
            />
          </div>
        </>
      )}

      {type === 'standalone' && (
        <div className="space-y-2">
          <Label htmlFor="ts-tools">Tool Definitions (JSON array)</Label>
          <Textarea
            id="ts-tools"
            value={toolsJson}
            onChange={(e) => setToolsJson(e.target.value)}
            placeholder={'[\n  {"name": "my_tool", "description": "...", "parameters": {"type": "object"}}\n]'}
            rows={8}
            className="font-mono text-xs"
          />
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="ts-description">Description (optional)</Label>
        <Input id="ts-description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this tool server provides" />
      </div>

      <div className="space-y-2">
        <Label htmlFor="ts-tags">Tags (optional, comma-separated)</Label>
        <Input id="ts-tags" value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} placeholder="e.g., filesystem, readonly" />
      </div>

      <div className="space-y-2">
        <Label htmlFor="ts-enabled">Status</Label>
        <Select value={enabled ? 'enabled' : 'disabled'} onValueChange={(v) => setEnabled(v === 'enabled')}>
          <SelectTrigger className="w-full" id="ts-enabled">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="enabled">Enabled</SelectItem>
            <SelectItem value="disabled">Disabled</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex gap-2 pt-2">
        <Button onClick={handleSave} disabled={isSaving} className="flex-1">
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
        <Button variant="outline" onClick={onClose} className="flex-1">
          Cancel
        </Button>
      </div>
    </div>
  );
}
