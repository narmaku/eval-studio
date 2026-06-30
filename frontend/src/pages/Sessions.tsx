import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useSessionHistoryStore } from '@/stores/sessionHistoryStore';
import { SessionEditSheet } from '@/components/sessions/SessionEditSheet';
import { DeleteConfirmDialog } from '@/components/ui/delete-confirm-dialog';
import { BarChart3, Pencil, Trash2 } from 'lucide-react';
import type { Session } from '@/types';

function formatDuration(startedAt: string | null, endedAt: string | null): string {
  if (!startedAt || !endedAt) return '--';
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime();
  const secs = Math.floor(ms / 1000);
  const mins = Math.floor(secs / 60);
  const remainSecs = secs % 60;
  return `${mins}m ${remainSecs}s`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

function statusBadge(status: string) {
  switch (status) {
    case 'active':
      return (
        <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
          Active
        </Badge>
      );
    case 'ended':
      return <Badge variant="secondary">Ended</Badge>;
    case 'scoring':
      return (
        <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
          Scoring...
        </Badge>
      );
    case 'completed':
      return (
        <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
          Scored
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export default function Sessions() {
  const { sessions, isLoading, error, fetchSessions, deleteSession } = useSessionHistoryStore();
  const navigate = useNavigate();
  const [editTarget, setEditTarget] = useState<Session | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Session | null>(null);

  useEffect(() => {
    void fetchSessions();
  }, [fetchSessions]);

  const messageCount = (transcript: Record<string, unknown>[] | null) => {
    if (!transcript) return 0;
    return transcript.filter((m) => m.role === 'user' || m.role === 'assistant').length;
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteSession(deleteTarget.id);
      toast.success(`Session "${deleteTarget.name ?? deleteTarget.id.slice(0, 8)}" deleted`);
    } catch {
      // error is already set in the store
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Sessions</h1>
        <p className="text-muted-foreground">
          Browse agent chat sessions. View transcripts, replay conversations, and score with
          different rubrics.
        </p>
      </div>
      <Separator />

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading sessions...</p>
        </div>
      )}

      {error && !isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <p className="text-destructive font-medium">Error loading sessions</p>
            <p className="text-muted-foreground text-sm">{error}</p>
          </div>
        </div>
      )}

      {!isLoading && !error && sessions.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">
            No sessions yet. Start an agent evaluation to create one.
          </p>
        </div>
      )}

      {!isLoading && !error && sessions.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Mode</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Messages</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.map((session) => (
              <TableRow
                key={session.id}
                className="cursor-pointer"
                onClick={() => navigate(`/sessions/${session.id}`)}
              >
                <TableCell className="font-medium">
                  {session.name ?? session.id.slice(0, 8)}
                </TableCell>
                <TableCell>
                  <Badge variant="outline">{session.mode}</Badge>
                </TableCell>
                <TableCell>{statusBadge(session.status)}</TableCell>
                <TableCell className="tabular-nums">{messageCount(session.transcript)}</TableCell>
                <TableCell className="tabular-nums">
                  {formatDuration(session.started_at, session.ended_at)}
                </TableCell>
                <TableCell className="tabular-nums">
                  {session.scores?.overall != null ? (
                    `${(session.scores.overall * 100).toFixed(0)}%`
                  ) : session.status === 'ended' ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/sessions/${session.id}`);
                      }}
                    >
                      <BarChart3 className="mr-1 h-3 w-3" />
                      Score
                    </Button>
                  ) : (
                    '--'
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {formatDate(session.started_at ?? session.created_at)}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditTarget(session);
                      }}
                      aria-label={`Edit ${session.name ?? session.id.slice(0, 8)}`}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(session);
                      }}
                      aria-label={`Delete ${session.name ?? session.id.slice(0, 8)}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Edit Sheet */}
      {editTarget && (
        <SessionEditSheet
          open={!!editTarget}
          onOpenChange={(open) => !open && setEditTarget(null)}
          session={editTarget}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete session"
        description="Are you sure you want to delete session"
        entityName={deleteTarget?.name ?? deleteTarget?.id.slice(0, 8) ?? ''}
        onConfirm={handleDelete}
        cascadeInfo="All results linked to this session will also be deleted."
      />
    </div>
  );
}
