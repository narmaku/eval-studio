import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useResultStore } from '@/stores/resultStore';
import { ResultDetailView } from '@/components/results';

export default function ResultDetail() {
  const { resultId } = useParams<{ resultId: string }>();
  const { currentResult, isLoading, error, fetchResult } = useResultStore();

  useEffect(() => {
    if (resultId) {
      void fetchResult(resultId);
    }
  }, [resultId, fetchResult]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading result details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <p className="text-destructive font-medium">Error loading result</p>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!currentResult) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Result not found.</p>
      </div>
    );
  }

  return <ResultDetailView result={currentResult} />;
}
