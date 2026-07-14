import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
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
import { cn } from '@/lib/utils';
import {
  getModeBadgeClasses,
  getModeLabel,
  getStatusPillClasses,
  getScoreColorClass,
  formatMonoTimestamp,
} from '@/lib/designUtils';
import { extractSessionMetadata } from '@/lib/metadataUtils';
import { MetadataBadges } from '@/components/ui/MetadataBadges';
import type { Session } from '@/types';

function formatDuration(startedAt: string | null, endedAt: string | null): string {
  if (!startedAt || !endedAt) return '--';
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime();
  const secs = Math.floor(ms / 1000);
  const mins = Math.floor(secs / 60);
  const remainSecs = secs % 60;
  return `${mins}m ${remainSecs}s`;
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
        <h1 className="text-[25px] font-semibold tracking-[-0.02em]">Sessions</h1>
        <p className="text-[13px] text-text-2">
          Browse agent chat sessions. View transcripts, replay conversations, and score with
          different rubrics.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <p className="text-[13px] text-text-3">Loading sessions...</p>
        </div>
      )}

      {error && !isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <p className="text-[13px] font-medium text-fail">Error loading sessions</p>
            <p className="text-[12px] text-text-3">{error}</p>
          </div>
        </div>
      )}

      {!isLoading && !error && sessions.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <p className="text-[13px] text-text-3">
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
              <TableHead>Config</TableHead>
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
                  <span
                    className={cn(
                      'rounded-[6px] px-2 py-0.5 text-[10px] font-semibold uppercase',
                      getModeBadgeClasses(session.mode),
                    )}
                  >
                    {getModeLabel(session.mode)}
                  </span>
                </TableCell>
                <TableCell>
                  <MetadataBadges
                    metadata={extractSessionMetadata(session.agent_config)}
                    maxInline={3}
                    compact
                  />
                </TableCell>
                <TableCell>
                  <span
                    className={cn(
                      'rounded-full px-2.5 py-0.5 text-[10.5px] font-medium capitalize',
                      getStatusPillClasses(session.status),
                    )}
                  >
                    {session.status}
                  </span>
                </TableCell>
                <TableCell className="tabular-nums">{messageCount(session.transcript)}</TableCell>
                <TableCell className="tabular-nums">
                  {formatDuration(session.started_at, session.ended_at)}
                </TableCell>
                <TableCell>
                  {session.scores?.overall != null ? (
                    <span
                      className={cn(
                        'font-mono font-semibold tabular-nums',
                        getScoreColorClass(session.scores.overall),
                      )}
                    >
                      {(session.scores.overall * 100).toFixed(0)}%
                    </span>
                  ) : session.status === 'ended' ? (
                    <button
                      className="inline-flex items-center rounded-[7px] border border-border px-2 py-1 text-[11px] font-medium text-text-2 transition-colors hover:bg-surface-3"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/sessions/${session.id}`);
                      }}
                    >
                      <BarChart3 className="mr-1 h-3 w-3" />
                      Score
                    </button>
                  ) : (
                    <span className="font-mono text-text-3 tabular-nums">--</span>
                  )}
                </TableCell>
                <TableCell>
                  <span className="font-mono text-[11px] text-text-2">
                    {formatMonoTimestamp(session.started_at ?? session.created_at)}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <button
                      className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditTarget(session);
                      }}
                      aria-label={`Edit ${session.name ?? session.id.slice(0, 8)}`}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(session);
                      }}
                      aria-label={`Delete ${session.name ?? session.id.slice(0, 8)}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
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
