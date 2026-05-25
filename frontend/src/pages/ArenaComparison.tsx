import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function ArenaComparison() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Model Arena</h1>
        <p className="text-muted-foreground">
          Compare multiple models by running the same evaluation across all contestants
          side-by-side.
        </p>
      </div>
      <Separator />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Model Selector</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Model selection and configuration will appear here.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Evaluation Mode Selector</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Evaluation mode selection will appear here.
            </p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Side-by-Side Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Side-by-side model comparison results will appear here.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Leaderboard</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">Model leaderboard will appear here.</p>
        </CardContent>
      </Card>
    </div>
  );
}
