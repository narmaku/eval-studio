import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { EvaluatorList } from '@/components/settings/EvaluatorList';
import { RubricList } from '@/components/settings/RubricList';
import { ProviderList } from '@/components/settings/ProviderList';

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage evaluators, scoring rubrics, and LLM provider configuration.
        </p>
      </div>
      <Separator />
      <Tabs defaultValue="evaluators">
        <TabsList>
          <TabsTrigger value="evaluators">Evaluators</TabsTrigger>
          <TabsTrigger value="rubrics">Rubrics</TabsTrigger>
          <TabsTrigger value="providers">Providers</TabsTrigger>
        </TabsList>
        <TabsContent value="evaluators" className="mt-4">
          <EvaluatorList />
        </TabsContent>
        <TabsContent value="rubrics" className="mt-4">
          <RubricList />
        </TabsContent>
        <TabsContent value="providers" className="mt-4">
          <ProviderList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
