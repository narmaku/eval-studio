import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RubricList } from '@/components/settings/RubricList';
import { ProviderList } from '@/components/settings/ProviderList';
import { ToolServerList } from '@/components/settings/ToolServerList';

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage scoring rubrics, LLM providers, and tool server configuration.
        </p>
      </div>
      <Separator />
      <Tabs defaultValue="rubrics">
        <TabsList>
          <TabsTrigger value="rubrics">Rubrics</TabsTrigger>
          <TabsTrigger value="providers">Providers</TabsTrigger>
          <TabsTrigger value="tool-servers">Tool Servers</TabsTrigger>
        </TabsList>
        <TabsContent value="rubrics" className="mt-4">
          <RubricList />
        </TabsContent>
        <TabsContent value="providers" className="mt-4">
          <ProviderList />
        </TabsContent>
        <TabsContent value="tool-servers" className="mt-4">
          <ToolServerList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
