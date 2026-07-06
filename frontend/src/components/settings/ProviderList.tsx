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
import { useProviderStore } from '@/stores/providerStore';
import { ProviderForm } from './ProviderForm';
import type { Provider } from '@/types';

export function ProviderList() {
  const providers = useProviderStore((s) => s.providers);
  const isLoading = useProviderStore((s) => s.isLoading);
  const fetchProviders = useProviderStore((s) => s.fetchProviders);
  const deleteProvider = useProviderStore((s) => s.deleteProvider);

  const [filter, setFilter] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Provider | null>(null);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const filteredProviders = filter
    ? providers.filter((p) => p.name.toLowerCase().includes(filter.toLowerCase()))
    : providers;

  const handleEdit = (provider: Provider) => {
    setEditingProvider(provider);
    setFormOpen(true);
  };

  const handleNew = () => {
    setEditingProvider(undefined);
    setFormOpen(true);
  };

  const handleSaved = () => {
    fetchProviders();
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteProvider(deleteTarget.id);
    } catch {
      await fetchProviders();
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder="Filter providers..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-[260px]"
        />
        <button
          className="inline-flex items-center rounded-[9px] bg-primary px-4 py-2.5 text-[13px] font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
          onClick={handleNew}
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          New Provider
        </button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <p className="text-[13px] text-text-3">Loading providers...</p>
        </div>
      )}

      {!isLoading && filteredProviders.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-[14px] border border-dashed border-border py-12">
          <p className="text-[13px] text-text-3">
            No providers configured. Add providers via config/providers.yaml or create one here.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredProviders.map((provider) => (
          <div
            key={provider.id}
            className="flex flex-col rounded-[14px] border border-border bg-card p-5 shadow-sm transition-all hover:shadow"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-[14px] font-semibold">{provider.name}</h3>
              </div>
              <div className="flex items-center gap-0.5 shrink-0">
                <button
                  className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                  onClick={() => handleEdit(provider)}
                  aria-label="Edit"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                  onClick={() => setDeleteTarget(provider)}
                  aria-label="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div className="mt-2 space-y-1.5">
              <div className="flex items-center gap-2">
                {provider.provider_type === 'custom' ? (
                  <span className="rounded-full bg-warn-bg px-2 py-0.5 text-[10px] font-medium text-warn">
                    Custom
                  </span>
                ) : (
                  <span className="rounded-full bg-pass-bg px-2 py-0.5 text-[10px] font-medium text-pass">
                    LiteLLM
                  </span>
                )}
                {provider.rate_limited && (
                  <span className="rounded-[5px] bg-surface-3 px-1.5 py-0.5 text-[10px] text-text-3">
                    Rate Limited
                  </span>
                )}
                {provider.has_api_key && (
                  <span className="rounded-[5px] bg-surface-3 px-1.5 py-0.5 text-[10px] text-text-3">
                    API Key
                  </span>
                )}
              </div>
              {provider.default_model && (
                <p
                  className="truncate font-mono text-[11px] text-text-2"
                  title={provider.default_model}
                >
                  {provider.default_model}
                </p>
              )}
              {provider.api_base && (
                <p className="truncate font-mono text-[11px] text-text-3" title={provider.api_base}>
                  {provider.api_base}
                </p>
              )}
              {provider.endpoint_url && (
                <p
                  className="truncate font-mono text-[11px] text-text-3"
                  title={provider.endpoint_url}
                >
                  {provider.endpoint_url}
                </p>
              )}
            </div>

            {provider.tags.length > 0 && (
              <div className="mt-auto flex flex-wrap gap-1 pt-2">
                {provider.tags.map((tag) => (
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

      <ProviderForm
        open={formOpen}
        onOpenChange={setFormOpen}
        provider={editingProvider}
        onSaved={handleSaved}
      />

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Provider</AlertDialogTitle>
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
