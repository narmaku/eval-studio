// Placeholder -- will be implemented in Step 3
interface DatasetUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DatasetUploadDialog({ open, onOpenChange }: DatasetUploadDialogProps) {
  if (!open) return null;
  void onOpenChange;
  return null;
}
