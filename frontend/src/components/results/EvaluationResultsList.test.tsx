import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { EvaluationResultsList } from './EvaluationResultsList';
import type { EvaluationResultRow } from './EvaluationResultsList';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock the result store
const mockToggleSelection = vi.fn();
const mockSetReference = vi.fn();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SelectorFn = (state: any) => unknown;

const defaultState = {
  selectedEvaluationIds: [] as string[],
  referenceEvaluationId: null as string | null,
  toggleSelection: mockToggleSelection,
  setReference: mockSetReference,
};

vi.mock('@/stores/resultStore', () => ({
  useResultStore: vi.fn((selector: SelectorFn) => selector(defaultState)),
}));

import { useResultStore } from '@/stores/resultStore';

const mockedUseResultStore = vi.mocked(useResultStore);

function mockStoreWith(overrides: Record<string, unknown>) {
  const state = { ...defaultState, ...overrides };
  mockedUseResultStore.mockImplementation((selector: SelectorFn) => selector(state));
}

const mockRows: EvaluationResultRow[] = [
  {
    evaluationId: 'e1',
    resultId: 'r1',
    name: 'QA Benchmark v1',
    mode: 'qa',
    status: 'completed',
    totalItems: 10,
    passRate: 0.8,
    meanScore: 0.85,
    createdAt: '2026-01-15T10:00:00Z',
    datasetId: 'ds1',
  },
  {
    evaluationId: 'e2',
    resultId: 'r2',
    name: 'RAG Evaluation',
    mode: 'rag',
    status: 'completed',
    totalItems: 20,
    passRate: 0.95,
    meanScore: 0.92,
    createdAt: '2026-01-10T10:00:00Z',
    datasetId: 'ds2',
  },
  {
    evaluationId: 'e3',
    resultId: 'r3',
    name: 'Agent Test',
    mode: 'agent',
    status: 'completed',
    totalItems: 5,
    passRate: 0.6,
    meanScore: 0.65,
    createdAt: '2026-01-20T10:00:00Z',
    datasetId: 'ds1',
  },
];

describe('EvaluationResultsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseResultStore.mockImplementation((selector: SelectorFn) => selector(defaultState));
  });

  it('renders table with data', () => {
    render(<EvaluationResultsList rows={mockRows} />);

    // Check column headers
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Mode')).toBeInTheDocument();
    expect(screen.getByText('Items Scored')).toBeInTheDocument();
    expect(screen.getByText('Pass Rate')).toBeInTheDocument();
    expect(screen.getByText('Mean Score')).toBeInTheDocument();
    expect(screen.getByText('Date')).toBeInTheDocument();

    // Check row content
    expect(screen.getByText('QA Benchmark v1')).toBeInTheDocument();
    expect(screen.getByText('RAG Evaluation')).toBeInTheDocument();
    expect(screen.getByText('Agent Test')).toBeInTheDocument();
  });

  it('renders empty state when no rows provided', () => {
    render(<EvaluationResultsList rows={[]} />);
    expect(screen.getByText('No evaluation results yet.')).toBeInTheDocument();
  });

  it('formats pass rate as percentage', () => {
    render(<EvaluationResultsList rows={mockRows} />);
    expect(screen.getByText('80.0%')).toBeInTheDocument();
    expect(screen.getByText('95.0%')).toBeInTheDocument();
  });

  it('formats mean score to 3 decimals', () => {
    render(<EvaluationResultsList rows={mockRows} />);
    expect(screen.getByText('0.850')).toBeInTheDocument();
    expect(screen.getByText('0.920')).toBeInTheDocument();
  });

  it('navigates on row click', async () => {
    const user = userEvent.setup();
    render(<EvaluationResultsList rows={mockRows} />);

    const rows = screen.getAllByRole('row');
    // First row is the header; default sort is date desc, so first data row is Agent Test (r3, Jan 20)
    await user.click(rows[1]!);

    expect(mockNavigate).toHaveBeenCalledWith('/results/r3');
  });

  it('renders mode badges', () => {
    render(<EvaluationResultsList rows={mockRows} />);

    const badges = screen.getAllByText(/^(Q&A|RAG|Agent)$/i);
    expect(badges.length).toBeGreaterThanOrEqual(3);
  });

  it('displays correct item counts', () => {
    render(<EvaluationResultsList rows={mockRows} />);
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders checkboxes for each row', () => {
    render(<EvaluationResultsList rows={mockRows} />);
    const checkboxes = screen.getAllByRole('checkbox');
    // One per data row (3 rows)
    expect(checkboxes.length).toBe(3);
  });

  it('calls toggleSelection when checkbox is clicked', async () => {
    const user = userEvent.setup();
    render(<EvaluationResultsList rows={mockRows} />);

    const checkboxes = screen.getAllByRole('checkbox');
    // Click the first checkbox - default sort is date desc, so first row is e3 (Agent Test, Jan 20)
    await user.click(checkboxes[0]!);
    expect(mockToggleSelection).toHaveBeenCalledWith('e3');
  });

  it('greys out incompatible rows when selection is active', () => {
    // Simulate e1 (qa, ds1) selected
    mockStoreWith({
      selectedEvaluationIds: ['e1'],
      referenceEvaluationId: 'e1',
    });

    render(<EvaluationResultsList rows={mockRows} />);

    // e2 is RAG/ds2, e3 is agent/ds1 - both incompatible with qa/ds1
    // Find data rows (skip header)
    const rows = screen.getAllByRole('row');
    // rows[0] is header, rows[1-3] are data

    // Check that incompatible rows have reduced opacity
    // e3 (Agent Test, agent mode, ds1) - incompatible by mode (sorted first since newest date)
    const agentRow = rows[1]!;
    expect(agentRow).toHaveClass('opacity-40');

    // e1 (QA Benchmark v1, qa mode, ds1) - compatible (selected)
    const qaRow = rows[2]!;
    expect(qaRow).not.toHaveClass('opacity-40');

    // e2 (RAG Evaluation, rag mode, ds2) - incompatible by both mode and dataset
    const ragRow = rows[3]!;
    expect(ragRow).toHaveClass('opacity-40');
  });

  it('shows reference star icon on reference evaluation', () => {
    const compatibleRows: EvaluationResultRow[] = [
      { ...mockRows[0]!, evaluationId: 'e1' },
      {
        evaluationId: 'e4',
        resultId: 'r4',
        name: 'QA Benchmark v2',
        mode: 'qa',
        status: 'completed',
        totalItems: 15,
        passRate: 0.9,
        meanScore: 0.88,
        createdAt: '2026-01-25T10:00:00Z',
        datasetId: 'ds1',
      },
    ];

    mockStoreWith({
      selectedEvaluationIds: ['e1', 'e4'],
      referenceEvaluationId: 'e1',
    });

    render(<EvaluationResultsList rows={compatibleRows} />);

    // The reference row should have a star button
    const starButtons = screen.getAllByTitle(/reference/i);
    expect(starButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('disables checkbox for incompatible rows', () => {
    mockStoreWith({
      selectedEvaluationIds: ['e1'],
      referenceEvaluationId: 'e1',
    });

    render(<EvaluationResultsList rows={mockRows} />);

    const checkboxes = screen.getAllByRole('checkbox');
    // e3 (agent/ds1, incompatible) - sorted first (newest date)
    expect(checkboxes[0]).toBeDisabled();
    // e1 (qa/ds1, selected) - sorted second
    expect(checkboxes[1]).not.toBeDisabled();
    // e2 (rag/ds2, incompatible) - sorted last (oldest date)
    expect(checkboxes[2]).toBeDisabled();
  });
});
