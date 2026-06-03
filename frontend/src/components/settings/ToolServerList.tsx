import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
          className="max-w-sm"
        />
        <Button onClick={handleNew}>
          <Plus className="mr-1 h-4 w-4" />
          New Tool Server
        </Button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <p className="text-sm text-muted-foreground">Loading tool servers...</p>
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-12">
          <p className="text-sm text-muted-foreground">
            No tool servers configured. Add one here or edit config/tool_servers.yaml.
          </p>
        </div>
      )}

      {filtered.map((server) => (
        <Card key={server.id}>
          <CardContent className="flex items-start justify-between py-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="font-medium">{server.name}</h3>
                <Badge variant="secondary">{server.type === 'mcp_stdio' ? 'MCP' : 'Standalone'}</Badge>
                <Badge variant={server.enabled ? 'default' : 'outline'}>
                  {server.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
              {server.description && (
                <p className="text-xs text-muted-foreground">{server.description}</p>
              )}
              {server.command && (
                <p className="text-xs text-muted-foreground font-mono">{server.command} {server.args.join(' ')}</p>
              )}
              {server.tool_count !== null && (
                <p className="text-xs text-muted-foreground">{server.tool_count} tool(s) defined</p>
              )}
              {server.tags.length > 0 && (
                <div className="flex gap-1 pt-1">
                  {server.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={() => handleEdit(server)} aria-label="Edit">
                <Pencil className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setDeleteTarget(server)} aria-label="Delete">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}

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
              Are you sure you want to delete &quot;{deleteTarget?.name}&quot;? This action cannot be undone.
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
