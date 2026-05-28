import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockImportRubric = vi.fn();

vi.mock('@/stores/rubricStore', () => ({
  useRubricStore: (selector?: unknown) => {
    const state = {
      importRubric: mockImportRubric,
    };
    if (typeof selector === 'function') {
      return (selector as (s: typeof state) => unknown)(state);
    }
    return state;
  },
}));

import { RubricImportDialog } from './RubricImportDialog';

describe('RubricImportDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when closed', () => {
    render(<RubricImportDialog open={false} onOpenChange={vi.fn()} />);
    expect(screen.queryByText(/import rubric/i)).not.toBeInTheDocument();
  });

  it('renders dialog content when open', () => {
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);
    expect(screen.getByText('Import Rubric')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/paste yaml/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^import$/i })).toBeInTheDocument();
  });

  it('shows reference link', () => {
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);
    const link = screen.getByRole('link', { name: /rubric-kit/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', 'https://github.com/instructlab/rubric-kit');
  });

  it('disables import button when textarea is empty', () => {
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);
    const importBtn = screen.getByRole('button', { name: /import$/i });
    expect(importBtn).toBeDisabled();
  });

  it('enables import button when yaml content is entered', async () => {
    const user = userEvent.setup();
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/paste yaml/i);
    await user.type(textarea, 'name: test');

    const importBtn = screen.getByRole('button', { name: /import$/i });
    expect(importBtn).not.toBeDisabled();
  });

  it('calls importRubric on submit', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const onImported = vi.fn();
    mockImportRubric.mockResolvedValue({ id: 'r-1', name: 'Imported' });

    render(
      <RubricImportDialog
        open={true}
        onOpenChange={onOpenChange}
        onImported={onImported}
      />
    );

    const textarea = screen.getByPlaceholderText(/paste yaml/i);
    await user.type(textarea, 'name: test');

    await user.click(screen.getByRole('button', { name: /import$/i }));

    expect(mockImportRubric).toHaveBeenCalledWith({ yaml_content: 'name: test' });
    expect(onImported).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('shows error message on import failure', async () => {
    const user = userEvent.setup();
    mockImportRubric.mockRejectedValue(new Error('Invalid YAML'));

    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/paste yaml/i);
    await user.type(textarea, 'bad yaml');

    await user.click(screen.getByRole('button', { name: /import$/i }));

    expect(await screen.findByText(/invalid yaml/i)).toBeInTheDocument();
  });
});
