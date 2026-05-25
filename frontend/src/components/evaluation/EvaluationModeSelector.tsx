import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

const modes = [
  {
    to: '/evaluate/qa',
    title: 'Q & A',
    subtitle: 'Single-turn',
    description: 'Evaluate Q&A pairs with configurable judges and metrics.',
  },
  {
    to: '/evaluate/agent',
    title: 'Agent Chat',
    subtitle: 'Multi-turn',
    description: 'Interactive or simulated multi-turn conversations with tool call tracing.',
  },
  {
    to: '/evaluate/rag',
    title: 'RAG',
    subtitle: 'Pipeline eval',
    description: 'Evaluate retrieval-augmented generation with chunk-level analysis.',
  },
  {
    to: '/evaluate/arena',
    title: 'Arena',
    subtitle: 'Compare models',
    description: 'Run the same evaluation across multiple models side-by-side.',
  },
];

export function EvaluationModeSelector() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Start New Evaluation</h1>
        <p className="text-muted-foreground">Choose an evaluation mode to get started.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {modes.map((mode) => (
          <Link key={mode.to} to={mode.to}>
            <Card className="hover:border-primary transition-colors cursor-pointer h-full">
              <CardHeader>
                <CardTitle>{mode.title}</CardTitle>
                <CardDescription>{mode.subtitle}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{mode.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
