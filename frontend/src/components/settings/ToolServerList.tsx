import { useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { useToolServerStore } from '@/stores/toolServerStore';
import { ToolServerForm } from './ToolServerForm';
import { cn } from '@/lib/utils';
import type { ToolServer } from '@/types';

export function ToolServerList() {
  const toolServers = useToolServerStore((s) => s.toolServers);
  const isLoading = useToolServerStore((s) => s.isLoading);
  const fetchToolServers = useToolServerStore((s) => s.fetchToolServers);
  const deleteToolServer = useToolServerStore((s) => s.deleteToolServer);

  const [filter, setFilter] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<ToolServer | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<ToolServer | null>(null);

  useEffect(() => {
    fetchToolServers();
  }, [fetchToolServers]);

  const filtered = filter
    ? toolServers.filter((s) => s.name.toLowerCase().includes(filter.toLowerCase()))
    : toolServers;

  const handleEdit = (server: ToolServer) => {
    setEditingServer(server);
    setFormOpen(true);
  };

  const handleNew = () => {
    setEditingServer(undefined);
    setFormOpen(true);
  };

  const handleSaved = () => {
    fetchToolServers();
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteToolServer(deleteTarget.id);
    } catch {
      await fetchToolServers();
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder="Filter tool servers..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-[260px]"
        />
        <button
          className="inline-flex items-center rounded-[9px] bg-primary px-4 py-2.5 text-[13px] font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
          onClick={handleNew}
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          New Tool Server
        </button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <p className="text-[13px] text-text-3">Loading tool servers...</p>
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-[14px] border border-dashed border-border py-12">
          <p className="text-[13px] text-text-3">
            No tool servers configured. Add one here or edit config/tool_servers.yaml.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((server) => (
          <div
            key={server.id}
            className="flex flex-col rounded-[14px] border border-border bg-card p-5 shadow-sm transition-all hover:shadow"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-[14px] font-semibold">{server.name}</h3>
              </div>
              <div className="flex items-center gap-0.5 shrink-0">
                <button
                  className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                  onClick={() => handleEdit(server)}
                  aria-label="Edit"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                  onClick={() => setDeleteTarget(server)}
                  aria-label="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div className="mt-2 space-y-1.5">
              <div className="flex items-center gap-2">
                {server.type === 'mcp_stdio' ? (
                  <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">
                    MCP
                  </span>
                ) : (
                  <span className="rounded-[5px] bg-surface-3 px-1.5 py-0.5 text-[10px] text-text-3">
                    Standalone
                  </span>
                )}
                <span className="flex items-center gap-1 text-[11px] text-text-2">
                  <span
                    className={cn(
                      'inline-block h-2 w-2 rounded-full',
                      server.enabled ? 'bg-pass' : 'bg-fail',
                    )}
                  />
                  {server.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              {server.description && (
                <p className="text-[12px] text-text-2 line-clamp-2">{server.description}</p>
              )}
              {server.command && (
                <p
                  className="truncate font-mono text-[11px] text-text-2"
                  title={`${server.command} ${server.args.join(' ')}`}
                >
                  {server.command} {server.args.join(' ')}
                </p>
              )}
              {server.tool_count !== null && (
                <p className="text-[11px] text-text-3">{server.tool_count} tool(s)</p>
              )}
            </div>

            {server.tags.length > 0 && (
              <div className="mt-auto flex flex-wrap gap-1 pt-2">
                {server.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-[5px] bg-surface-3 px-1.5 py-0.5 text-[10px] text-text-3"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <ToolServerForm
        open={formOpen}
        onOpenChange={setFormOpen}
        toolServer={editingServer}
        onSaved={handleSaved}
      />

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Tool Server</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deleteTarget?.name}&quot;? This action cannot
              be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
