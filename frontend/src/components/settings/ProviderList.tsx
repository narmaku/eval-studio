import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { api } from '@/services/api';
import type { Provider } from '@/types';

export function ProviderList() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProviders = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.listProviders();
        setProviders(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch providers';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };
    fetchProviders();
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <p className="text-sm text-muted-foreground">Loading providers...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-destructive/10 p-4 text-sm text-destructive">{error}</div>
    );
  }

  if (providers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-12">
        <p className="text-sm text-muted-foreground">
          No providers configured. Add provider profiles to config/providers.yaml
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {providers.map((provider) => (
        <Card key={provider.id}>
          <CardContent className="py-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{provider.name}</h3>
                  <Badge variant="secondary">{provider.purpose}</Badge>
                </div>
                <p className="text-xs text-muted-foreground font-mono">{provider.litellm_model}</p>
                {provider.api_base && (
                  <p className="text-xs text-muted-foreground">
                    API Base: {provider.api_base}
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
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {provider.has_api_key && (
                  <Badge variant="outline" className="text-xs">
                    API Key Set
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
