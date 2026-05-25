import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function Datasets() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Datasets</h1>
        <p className="text-muted-foreground">
          Manage your dataset library. Upload, import, version, and browse evaluation datasets.
        </p>
      </div>
      <Separator />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Dataset List / Table</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Searchable dataset table will appear here.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Upload Panel</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Dataset upload and import controls will appear here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
