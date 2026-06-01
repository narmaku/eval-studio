import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Rubric } from '@/types';

const mockFetchRubrics = vi.fn();
const mockDeleteRubric = vi.fn();

const makeRubric = (overrides: Partial<Rubric> = {}): Rubric => ({
  id: 'r-1',
  name: 'Test Rubric',
  description: 'A test rubric',
  dimensions: [{ name: 'accuracy', weight: 1.0, description: 'Is it accurate?' }],
  pass_threshold: 0.7,
  aggregation: 'weighted_average',
  prompt_template: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

let storeState: {
  rubrics: Rubric[];
  isLoading: boolean;
  error: string | null;
  fetchRubrics: typeof mockFetchRubrics;
  deleteRubric: typeof mockDeleteRubric;
  createRubric: ReturnType<typeof vi.fn>;
  updateRubric: ReturnType<typeof vi.fn>;
  importRubric: ReturnType<typeof vi.fn>;
  generateRubric: ReturnType<typeof vi.fn>;
  refineRubric: ReturnType<typeof vi.fn>;
};

const defaultStore = {
  rubrics: [] as Rubric[],
  isLoading: false,
  error: null,
  fetchRubrics: mockFetchRubrics,
  deleteRubric: mockDeleteRubric,
  createRubric: vi.fn(),
  updateRubric: vi.fn(),
  importRubric: vi.fn(),
  generateRubric: vi.fn(),
  refineRubric: vi.fn(),
};

vi.mock('@/stores/rubricStore', () => ({
  useRubricStore: (selector?: unknown) => {
    if (typeof selector === 'function') {
      return (selector as (s: typeof storeState) => unknown)(storeState);
    }
    return storeState;
  },
}));

// Stub RubricBuilder to avoid Sheet rendering complexity in this test
vi.mock('./RubricBuilder', () => ({
  RubricBuilder: ({
    open,
    rubric,
  }: {
    open: boolean;
    rubric?: Rubric;
    onOpenChange: (v: boolean) => void;
    onSaved?: () => void;
  }) =>
    open ? (
      <div data-testid="rubric-builder">{rubric ? `editing ${rubric.name}` : 'creating new'}</div>
    ) : null,
}));

// Stub dialog components
vi.mock('./RubricImportDialog', () => ({
  RubricImportDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="import-dialog">import dialog</div> : null,
}));

vi.mock('./RubricGenerateDialog', () => ({
  RubricGenerateDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="generate-dialog">generate dialog</div> : null,
}));

vi.mock('./RubricRefineDialog', () => ({
  RubricRefineDialog: ({ open, rubric }: { open: boolean; rubric: Rubric }) =>
    open ? <div data-testid="refine-dialog">refining {rubric.name}</div> : null,
}));

import { RubricList } from './RubricList';

describe('RubricList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storeState = { ...defaultStore };
  });

  it('calls fetchRubrics on mount', () => {
    render(<RubricList />);
    expect(mockFetchRubrics).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when no rubrics', () => {
    render(<RubricList />);
    expect(screen.getByText(/no rubrics created yet/i)).toBeInTheDocument();
  });

  it('renders rubric rows', () => {
    storeState = {
      ...defaultStore,
      rubrics: [
        makeRubric({ id: 'r-1', name: 'Quality Rubric' }),
        makeRubric({ id: 'r-2', name: 'Speed Rubric' }),
      ],
    };
    render(<RubricList />);
    expect(screen.getByText('Quality Rubric')).toBeInTheDocument();
    expect(screen.getByText('Speed Rubric')).toBeInTheDocument();
  });

  it('shows dimension count for each rubric', () => {
    storeState = {
      ...defaultStore,
      rubrics: [
        makeRubric({
          id: 'r-1',
          name: 'Multi Dim',
          dimensions: [
            { name: 'a', weight: 0.5, description: '' },
            { name: 'b', weight: 0.5, description: '' },
          ],
        }),
      ],
    };
    render(<RubricList />);
    expect(screen.getByText('2 dimensions')).toBeInTheDocument();
  });

  it('renders New Rubric button', () => {
    render(<RubricList />);
    expect(screen.getByRole('button', { name: /new rubric/i })).toBeInTheDocument();
  });

  it('renders Import and Generate buttons', () => {
    render(<RubricList />);
    expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate/i })).toBeInTheDocument();
  });

  it('renders Refine button per rubric', () => {
    storeState = {
      ...defaultStore,
      rubrics: [makeRubric({ id: 'r-1', name: 'My Rubric' })],
    };
    render(<RubricList />);
    expect(screen.getByRole('button', { name: /refine/i })).toBeInTheDocument();
  });

  it('filters rubrics by name', async () => {
    const user = userEvent.setup();
    storeState = {
      ...defaultStore,
      rubrics: [
        makeRubric({ id: 'r-1', name: 'Quality Rubric' }),
        makeRubric({ id: 'r-2', name: 'Speed Rubric' }),
      ],
    };
    render(<RubricList />);

    const filterInput = screen.getByPlaceholderText(/filter/i);
    await user.type(filterInput, 'Quality');

    expect(screen.getByText('Quality Rubric')).toBeInTheDocument();
    expect(screen.queryByText('Speed Rubric')).not.toBeInTheDocument();
  });

  it('opens builder on New Rubric click', async () => {
    const user = userEvent.setup();
    render(<RubricList />);

    await user.click(screen.getByRole('button', { name: /new rubric/i }));

    expect(screen.getByTestId('rubric-builder')).toBeInTheDocument();
    expect(screen.getByText('creating new')).toBeInTheDocument();
  });

  it('opens builder in edit mode on Edit click', async () => {
    const user = userEvent.setup();
    storeState = {
      ...defaultStore,
      rubrics: [makeRubric({ id: 'r-1', name: 'My Rubric' })],
    };
    render(<RubricList />);

    await user.click(screen.getByRole('button', { name: /edit/i }));

    expect(screen.getByTestId('rubric-builder')).toBeInTheDocument();
    expect(screen.getByText('editing My Rubric')).toBeInTheDocument();
  });

  it('opens import dialog on Import click', async () => {
    const user = userEvent.setup();
    render(<RubricList />);

    await user.click(screen.getByRole('button', { name: /import/i }));

    expect(screen.getByTestId('import-dialog')).toBeInTheDocument();
  });

  it('opens generate dialog on Generate click', async () => {
    const user = userEvent.setup();
    render(<RubricList />);

    await user.click(screen.getByRole('button', { name: /generate/i }));

    expect(screen.getByTestId('generate-dialog')).toBeInTheDocument();
  });

  it('opens refine dialog on Refine click', async () => {
    const user = userEvent.setup();
    storeState = {
      ...defaultStore,
      rubrics: [makeRubric({ id: 'r-1', name: 'My Rubric' })],
    };
    render(<RubricList />);

    await user.click(screen.getByRole('button', { name: /refine/i }));

    expect(screen.getByTestId('refine-dialog')).toBeInTheDocument();
    expect(screen.getByText('refining My Rubric')).toBeInTheDocument();
  });
});
