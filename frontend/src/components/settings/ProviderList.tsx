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

      {filteredProviders.map((provider) => (
        <Card key={provider.id}>
          <CardContent className="flex items-start justify-between py-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="font-medium">{provider.name}</h3>
              </div>
              <p className="text-xs text-muted-foreground font-mono">{provider.litellm_model}</p>
              {provider.api_base && (
                <p className="text-xs text-muted-foreground">API Base: {provider.api_base}</p>
              )}
              {provider.default_params && Object.keys(provider.default_params).length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Defaults:{' '}
                  {Object.entries(provider.default_params)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(', ')}
                </p>
              )}
              {provider.tags.length > 0 && (
                <div className="flex gap-1 pt-1">
                  {provider.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-1">
              {provider.has_api_key && (
                <Badge variant="outline" className="text-xs mr-2">
                  API Key Set
                </Badge>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleEdit(provider)}
                aria-label="Edit"
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDeleteTarget(provider)}
                aria-label="Delete"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}

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
