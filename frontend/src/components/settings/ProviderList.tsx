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
          className="max-w-sm"
        />
        <Button onClick={handleNew}>
          <Plus className="mr-1 h-4 w-4" />
          New Provider
        </Button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <p className="text-sm text-muted-foreground">Loading providers...</p>
        </div>
      )}

      {!isLoading && filteredProviders.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-12">
          <p className="text-sm text-muted-foreground">
            No providers configured. Add providers via config/providers.yaml or create one here.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredProviders.map((provider) => (
          <Card key={provider.id} className="flex flex-col">
            <CardContent className="flex flex-col gap-2 py-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <h3 className="font-medium truncate">{provider.name}</h3>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => handleEdit(provider)}
                    aria-label="Edit"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setDeleteTarget(provider)}
                    aria-label="Delete"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={provider.provider_type === 'custom' ? 'secondary' : 'outline'}
                    className="text-xs"
                  >
                    {provider.provider_type === 'custom' ? 'Custom' : 'LiteLLM'}
                  </Badge>
                  {provider.has_api_key && (
                    <Badge variant="outline" className="text-xs">
                      API Key
                    </Badge>
                  )}
                </div>
                {provider.default_model && (
                  <p
                    className="text-xs text-muted-foreground font-mono truncate"
                    title={provider.default_model}
                  >
                    {provider.default_model}
                  </p>
                )}
                {provider.api_base && (
                  <p
                    className="text-xs text-muted-foreground truncate"
                    title={provider.api_base}
                  >
                    {provider.api_base}
                  </p>
                )}
                {provider.endpoint_url && (
                  <p
                    className="text-xs text-muted-foreground truncate"
                    title={provider.endpoint_url}
                  >
                    {provider.endpoint_url}
                  </p>
                )}
              </div>

              {provider.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-auto pt-1">
                  {provider.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
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
