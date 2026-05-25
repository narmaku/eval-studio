import { useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { ModelEndpoint } from '@/types';

const modelEndpointSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  litellm_model: z.string().min(1, 'Model is required'),
  api_base: z.string().url('Must be a valid URL').or(z.literal('')).optional(),
});

type ModelEndpointFormData = z.infer<typeof modelEndpointSchema>;

interface ModelEndpointConfigProps {
  value: ModelEndpoint | undefined;
  onChange: (endpoint: ModelEndpoint) => void;
  disabled?: boolean;
}

export function ModelEndpointConfig({ value, onChange, disabled }: ModelEndpointConfigProps) {
  const {
    register,
    watch,
    reset,
    formState: { errors, isValid },
  } = useForm<ModelEndpointFormData>({
    resolver: zodResolver(modelEndpointSchema),
    mode: 'onChange',
    defaultValues: {
      name: value?.name ?? '',
      litellm_model: value?.litellm_model ?? '',
      api_base: value?.api_base ?? '',
    },
  });

  const isInternalChange = useRef(false);

  useEffect(() => {
    if (value && !isInternalChange.current) {
      reset({
        name: value.name,
        litellm_model: value.litellm_model,
        api_base: value.api_base ?? '',
      });
    }
    isInternalChange.current = false;
  }, [value, reset]);

  useEffect(() => {
    const subscription = watch((formValues) => {
      if (isValid && formValues.name && formValues.litellm_model) {
        isInternalChange.current = true;
        onChange({
          name: formValues.name,
          litellm_model: formValues.litellm_model,
          api_base: formValues.api_base || undefined,
        });
      }
    });
    return () => subscription.unsubscribe();
  }, [watch, isValid, onChange]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Model Endpoint</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="endpoint-name">Name</Label>
          <Input
            id="endpoint-name"
            placeholder="e.g. GPT-4o"
            disabled={disabled}
            {...register('name')}
          />
          {errors.name && (
            <p className="text-destructive text-xs">{errors.name.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="endpoint-model">LiteLLM Model</Label>
          <Input
            id="endpoint-model"
            placeholder="e.g. openai/gpt-4o"
            disabled={disabled}
            {...register('litellm_model')}
          />
          {errors.litellm_model && (
            <p className="text-destructive text-xs">{errors.litellm_model.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="endpoint-api-base">API Base URL (optional)</Label>
          <Input
            id="endpoint-api-base"
            placeholder="e.g. https://api.openai.com/v1"
            disabled={disabled}
            {...register('api_base')}
          />
          {errors.api_base && (
            <p className="text-destructive text-xs">{errors.api_base.message}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
