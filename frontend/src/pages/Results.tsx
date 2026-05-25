import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function Results() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Results</h1>
        <p className="text-muted-foreground">
          Browse historical evaluation results, compare runs, and export data for further analysis.
        </p>
      </div>
      <Separator />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Results List / Table</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Filterable results table will appear here.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Comparison Tools</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Result comparison controls will appear here.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Export Options</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">Export format options will appear here.</p>
        </CardContent>
      </Card>
    </div>
  );
}
