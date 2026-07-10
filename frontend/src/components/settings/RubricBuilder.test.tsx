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
  tags: [],
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

  it('loads criteria from existing rubric in edit mode', async () => {
    const user = userEvent.setup();
    const rubricWithCriteria = makeRubric({
      dimensions: [
        {
          name: 'accuracy',
          weight: 1,
          description: 'Factual accuracy',
          criteria: [
            { name: 'factual', criterion: 'Is factually correct', weight: 1 },
            { name: 'complete', criterion: 'Is complete', weight: 2 },
          ],
        },
      ],
    });

    render(<RubricBuilder open={true} onOpenChange={vi.fn()} rubric={rubricWithCriteria} />);

    // Criteria count shows in the toggle button
    expect(screen.getByText('Criteria (2)')).toBeInTheDocument();

    // Click toggle to expand criteria
    await user.click(screen.getByText('Criteria (2)'));

    // Verify criterion input fields contain expected values
    expect(screen.getByDisplayValue('factual')).toBeInTheDocument();
    expect(screen.getByDisplayValue('complete')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Is factually correct')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Is complete')).toBeInTheDocument();
  });

  it('can add a criterion to a dimension', async () => {
    const user = userEvent.setup();
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} />);

    // Add a dimension first
    await user.click(screen.getByRole('button', { name: /add dimension/i }));

    // Initially shows Criteria (0)
    expect(screen.getByText('Criteria (0)')).toBeInTheDocument();

    // Click "Add Criterion"
    await user.click(screen.getByRole('button', { name: /add criterion/i }));

    // Count updates to 1
    expect(screen.getByText('Criteria (1)')).toBeInTheDocument();

    // Section auto-expands and shows input fields
    expect(screen.getByPlaceholderText('Criterion name')).toBeInTheDocument();
  });

  it('can remove a criterion', async () => {
    const user = userEvent.setup();
    const rubricWithCriteria = makeRubric({
      dimensions: [
        {
          name: 'accuracy',
          weight: 1,
          description: 'Factual accuracy',
          criteria: [
            { name: 'factual', criterion: 'Is factually correct', weight: 1 },
            { name: 'complete', criterion: 'Is complete', weight: 2 },
          ],
        },
      ],
    });

    render(<RubricBuilder open={true} onOpenChange={vi.fn()} rubric={rubricWithCriteria} />);

    // Expand criteria section
    await user.click(screen.getByText('Criteria (2)'));

    // Remove the first criterion
    const removeButton = screen.getByRole('button', { name: /remove criterion 1/i });
    await user.click(removeButton);

    // Only 1 criterion remains
    expect(screen.getByText('Criteria (1)')).toBeInTheDocument();
    // The second criterion (now first) still exists
    expect(screen.getByDisplayValue('complete')).toBeInTheDocument();
    expect(screen.queryByDisplayValue('factual')).not.toBeInTheDocument();
  });

  it('validates criteria fields', async () => {
    const user = userEvent.setup();
    render(<RubricBuilder open={true} onOpenChange={vi.fn()} />);

    // Fill in rubric name
    await user.type(screen.getByLabelText(/name/i), 'Test Rubric');

    // Add a dimension with a name
    await user.click(screen.getByRole('button', { name: /add dimension/i }));
    const row = screen.getByTestId('dimension-row');
    const dimInputs = within(row).getAllByRole('textbox');
    await user.type(dimInputs[0]!, 'quality');

    // Add a criterion but leave fields empty
    await user.click(screen.getByRole('button', { name: /add criterion/i }));

    // Try to save
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    expect(mockCreateRubric).not.toHaveBeenCalled();
  });

  it('includes criteria in save payload', async () => {
    const user = userEvent.setup();
    mockCreateRubric.mockResolvedValue(makeRubric());

    render(<RubricBuilder open={true} onOpenChange={vi.fn()} />);

    // Fill rubric name
    await user.type(screen.getByLabelText(/name/i), 'Criteria Rubric');

    // Add dimension
    await user.click(screen.getByRole('button', { name: /add dimension/i }));
    const row = screen.getByTestId('dimension-row');
    const dimInputs = within(row).getAllByRole('textbox');
    await user.type(dimInputs[0]!, 'quality');

    // Add criterion and fill fields
    await user.click(screen.getByRole('button', { name: /add criterion/i }));

    const criterionName = screen.getByPlaceholderText('Criterion name');
    await user.type(criterionName, 'factual');

    const criterionText = screen.getByPlaceholderText('Criterion text (evaluation instruction)');
    await user.type(criterionText, 'Must be factually correct');

    // Save
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(mockCreateRubric).toHaveBeenCalledTimes(1);
    expect(mockCreateRubric).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Criteria Rubric',
        dimensions: expect.arrayContaining([
          expect.objectContaining({
            name: 'quality',
            criteria: expect.arrayContaining([
              expect.objectContaining({
                name: 'factual',
                criterion: 'Must be factually correct',
                weight: 1,
              }),
            ]),
          }),
        ]),
      }),
    );
  });

  it('criteria preserved through edit round-trip', async () => {
    const user = userEvent.setup();
    const rubricWithCriteria = makeRubric({
      dimensions: [
        {
          name: 'accuracy',
          weight: 1,
          description: 'Factual accuracy',
          criteria: [{ name: 'factual', criterion: 'Is factually correct', weight: 1 }],
        },
      ],
    });
    mockUpdateRubric.mockResolvedValue(rubricWithCriteria);

    render(<RubricBuilder open={true} onOpenChange={vi.fn()} rubric={rubricWithCriteria} />);

    // Save without changes
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(mockUpdateRubric).toHaveBeenCalledTimes(1);
    expect(mockUpdateRubric).toHaveBeenCalledWith(
      'r-1',
      expect.objectContaining({
        dimensions: expect.arrayContaining([
          expect.objectContaining({
            name: 'accuracy',
            criteria: expect.arrayContaining([
              expect.objectContaining({
                name: 'factual',
                criterion: 'Is factually correct',
                weight: 1,
              }),
            ]),
          }),
        ]),
      }),
    );
  });
});
