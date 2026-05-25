import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function Environments() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Environments</h1>
        <p className="text-muted-foreground">
          Manage test environments for agent evaluations. Configure BYOE, Docker Compose, or TMT
          environments.
        </p>
      </div>
      <Separator />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Environment List</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Environment list with status indicators will appear here.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Environment Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Environment creation and configuration form will appear here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
