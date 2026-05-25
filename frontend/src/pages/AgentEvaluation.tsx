import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function AgentEvaluation() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agent/Chat Evaluation</h1>
        <p className="text-muted-foreground">
          Multi-turn conversational evaluation with tool call tracing, live or simulated sessions.
        </p>
      </div>
      <Separator />
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Conversation Panel</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Chat conversation will appear here.
            </p>
          </CardContent>
        </Card>
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Tool Inspector Panel</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Tool call details will appear here.
            </p>
          </CardContent>
        </Card>
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Scoring Panel</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Turn-by-turn and session scores will appear here.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
