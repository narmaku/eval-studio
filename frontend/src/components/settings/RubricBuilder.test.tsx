import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Rubric } from '@/types';

const mockCreateRubric = vi.fn();
const mockUpdateRubric = vi.fn();

vi.mock('@/stores/rubricStore', () => ({
  useRubricStore: (selector?: unknown) => {
    const state = {
      createRubric: mockCreateRubric,
      updateRubric: mockUpdateRubric,
    };
    if (typeof selector === 'function') {
      return (selector as (s: typeof state) => unknown)(state);
    }
    return state;
  },
}));

import { RubricBuilder } from './RubricBuilder';

const makeRubric = (overrides: Partial<Rubric> = {}): Rubric => ({
  id: 'r-1',
  name: 'Existing Rubric',
  description: 'An existing rubric',
  dimensions: [{ name: 'accuracy', weight: 0.5, description: 'Is it accurate?' }],
  pass_threshold: 0.7,
  aggregation: 'weighted_average',
  prompt_template: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('RubricBuilder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form fields when open', () => {
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByText(/pass threshold/i)).toBeInTheDocument();
    expect(screen.getByText(/aggregation/i)).toBeInTheDocument();
  });

  it('renders "New Rubric" title in create mode', () => {
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} />);
    expect(screen.getByText('New Rubric')).toBeInTheDocument();
  });

  it('renders "Edit Rubric" title in edit mode', () => {
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} rubric={makeRubric()} />);
    expect(screen.getByText('Edit Rubric')).toBeInTheDocument();
  });

  it('populates form with rubric data in edit mode', () => {
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} rubric={makeRubric()} />);

    expect(screen.getByLabelText(/name/i)).toHaveValue('Existing Rubric');
    expect(screen.getByLabelText(/description/i)).toHaveValue('An existing rubric');
    // Check dimension row exists
    expect(screen.getByDisplayValue('accuracy')).toBeInTheDocument();
  });

  it('can add dimension rows', async () => {
    const user = userEvent.setup();
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} />);

    const addButton = screen.getByRole('button', { name: /add dimension/i });
    await user.click(addButton);

    // There should now be dimension input rows
    const dimensionGroups = screen.getAllByTestId('dimension-row');
    expect(dimensionGroups.length).toBeGreaterThanOrEqual(1);
  });

  it('can remove dimension rows', async () => {
    const user = userEvent.setup();
    render(
      <RubricBuilder
        open={true}
        onOpenChange={vi.fn()}
        rubric={makeRubric({
          dimensions: [
            { name: 'dim1', weight: 0.5, description: 'First' },
            { name: 'dim2', weight: 0.5, description: 'Second' },
          ],
        })}
      />,
    );

    const removeButtons = screen.getAllByTestId('remove-dimension');
    expect(removeButtons).toHaveLength(2);
    const firstRemove = removeButtons[0]!;
    await user.click(firstRemove);

    expect(screen.getAllByTestId('dimension-row')).toHaveLength(1);
  });

  it('validates: rejects empty name', async () => {
    const user = userEvent.setup();
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} />);

    // Add a dimension so that is not the validation issue
    await user.click(screen.getByRole('button', { name: /add dimension/i }));
    const row = screen.getByTestId('dimension-row');
    const inputs = within(row).getAllByRole('textbox');
    await user.type(inputs[0]!, 'quality');

    // Try to save without a name
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    expect(mockCreateRubric).not.toHaveBeenCalled();
  });

  it('validates: rejects empty dimensions', async () => {
    const user = userEvent.setup();
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByLabelText(/name/i), 'Test Rubric');

    // Try to save without dimensions
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(screen.getByText(/at least one dimension/i)).toBeInTheDocument();
    expect(mockCreateRubric).not.toHaveBeenCalled();
  });

  it('calls createRubric on save in create mode', async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    const onOpenChange = vi.fn();
    mockCreateRubric.mockResolvedValue(makeRubric());

    render(<RubricBuilder open={true} onOpenChange={onOpenChange} onSaved={onSaved} />);

    await user.type(screen.getByLabelText(/name/i), 'New Rubric');
    await user.click(screen.getByRole('button', { name: /add dimension/i }));

    const row = screen.getByTestId('dimension-row');
    const inputs = within(row).getAllByRole('textbox');
    await user.type(inputs[0]!, 'quality');

    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(mockCreateRubric).toHaveBeenCalledTimes(1);
    expect(mockCreateRubric).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'New Rubric',
        dimensions: expect.arrayContaining([expect.objectContaining({ name: 'quality' })]),
      }),
    );
  });

  it('calls updateRubric on save in edit mode', async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    mockUpdateRubric.mockResolvedValue(makeRubric({ name: 'Updated' }));

    render(
      <RubricBuilder open={true} onOpenChange={vi.fn()} rubric={makeRubric()} onSaved={onSaved} />,
    );

    const nameInput = screen.getByLabelText(/name/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated');

    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(mockUpdateRubric).toHaveBeenCalledTimes(1);
    expect(mockUpdateRubric).toHaveBeenCalledWith(
      'r-1',
      expect.objectContaining({ name: 'Updated' }),
    );
  });
});
