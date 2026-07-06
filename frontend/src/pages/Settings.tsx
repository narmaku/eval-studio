import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { EvaluatorList } from '@/components/settings/EvaluatorList';
import { RubricList } from '@/components/settings/RubricList';
import { ProviderList } from '@/components/settings/ProviderList';
import { ToolServerList } from '@/components/settings/ToolServerList';

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[25px] font-semibold tracking-[-0.02em]">Settings</h1>
        <p className="text-[13px] text-text-2">
          Manage evaluators, scoring rubrics, and LLM provider configuration.
        </p>
      </div>
      <Tabs defaultValue="evaluators">
        <TabsList className="h-9 rounded-[10px] bg-surface-2 p-1">
          <TabsTrigger
            value="evaluators"
            className="rounded-[7px] px-3 py-1 text-[12.5px] font-medium data-[state=active]:bg-surface-1 data-[state=active]:shadow-sm"
          >
            Evaluators
          </TabsTrigger>
          <TabsTrigger
            value="rubrics"
            className="rounded-[7px] px-3 py-1 text-[12.5px] font-medium data-[state=active]:bg-surface-1 data-[state=active]:shadow-sm"
          >
            Rubrics
          </TabsTrigger>
          <TabsTrigger
            value="providers"
            className="rounded-[7px] px-3 py-1 text-[12.5px] font-medium data-[state=active]:bg-surface-1 data-[state=active]:shadow-sm"
          >
            Providers
          </TabsTrigger>
          <TabsTrigger
            value="tool-servers"
            className="rounded-[7px] px-3 py-1 text-[12.5px] font-medium data-[state=active]:bg-surface-1 data-[state=active]:shadow-sm"
          >
            Tool Servers
          </TabsTrigger>
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
        <TabsContent value="tool-servers" className="mt-4">
          <ToolServerList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
