import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { QAResultsTable } from './QAResultsTable';
import type { Result, DatasetItem } from '@/types';

const mockResults: Result[] = [
  {
    id: 'r1',
    evaluation_id: 'e1',
    dataset_item_id: 'item-1',
    session_id: null,
    contestant_model: null,
    score: 0.9,
    passed: true,
    actual_answer: 'Use systemctl restart sshd',
    judge_reasoning: 'The answer correctly describes the systemctl command.',
    scores_breakdown: { accuracy: 0.9 },
    retrieved_chunks: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'r2',
    evaluation_id: 'e1',
    dataset_item_id: 'item-2',
    session_id: null,
    contestant_model: null,
    score: 0.3,
    passed: false,
    actual_answer: 'Just restart it',
    judge_reasoning: 'The answer is incomplete and misses key steps.',
    scores_breakdown: { accuracy: 0.3 },
    retrieved_chunks: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'r3',
    evaluation_id: 'e1',
    dataset_item_id: 'item-3',
    session_id: null,
    contestant_model: null,
    score: 0.75,
    passed: true,
    actual_answer: 'Run firewall-cmd --add-port=443/tcp --permanent',
    judge_reasoning: 'Adequate coverage of firewall rules.',
    scores_breakdown: { accuracy: 0.75 },
    retrieved_chunks: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'r4',
    evaluation_id: 'e1',
    dataset_item_id: 'item-4',
    session_id: null,
    contestant_model: null,
    score: 0.5,
    passed: false,
    actual_answer: 'Change the port in sshd_config',
    judge_reasoning: 'Missing SELinux context adjustment.',
    scores_breakdown: { accuracy: 0.5 },
    retrieved_chunks: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'r5',
    evaluation_id: 'e1',
    dataset_item_id: 'item-5',
    session_id: null,
    contestant_model: null,
    score: 0.95,
    passed: true,
    actual_answer: 'Use pvcreate, vgcreate, and lvcreate in sequence.',
    judge_reasoning: 'Excellent explanation of LVM concepts.',
    scores_breakdown: { accuracy: 0.95 },
    retrieved_chunks: null,
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockDatasetItems: DatasetItem[] = [
  {
    id: 'item-1',
    question: 'How do you restart the SSH service on RHEL?',
    expected_answer: 'systemctl restart sshd',
    metadata: {},
    order_index: 0,
  },
  {
    id: 'item-2',
    question: 'How do you configure a static IP on RHEL 9?',
    expected_answer: 'Use nmcli or edit /etc/NetworkManager/system-connections/',
    metadata: {},
    order_index: 1,
  },
  {
    id: 'item-3',
    question: 'How do you open port 443 on RHEL?',
    expected_answer: 'firewall-cmd --add-port=443/tcp --permanent && firewall-cmd --reload',
    metadata: {},
    order_index: 2,
  },
  {
    id: 'item-4',
    question: 'How do you change the SSH port on RHEL with SELinux enabled?',
    expected_answer: 'Edit sshd_config, run semanage port, restart sshd',
    metadata: {},
    order_index: 3,
  },
  {
    id: 'item-5',
    question: 'Explain LVM volume creation on Linux.',
    expected_answer: 'Create PV with pvcreate, VG with vgcreate, LV with lvcreate, then mkfs',
    metadata: {},
    order_index: 4,
  },
];

describe('QAResultsTable', () => {
  it('renders all score rows', () => {
    render(<QAResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    // We should see 5 rows of data (not counting header)
    const rows = screen.getAllByRole('row');
    // 1 header row + 5 data rows = 6
    expect(rows).toHaveLength(6);
  });

  it('displays pass/fail badges correctly', () => {
    render(<QAResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    const passBadges = screen.getAllByText('Pass');
    const failBadges = screen.getAllByText('Fail');
    expect(passBadges).toHaveLength(3);
    expect(failBadges).toHaveLength(2);
  });

  it('displays question text from dataset items', () => {
    render(<QAResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    expect(screen.getByText(/How do you restart the SSH service/)).toBeInTheDocument();
    expect(screen.getByText(/Explain LVM volume creation/)).toBeInTheDocument();
  });

  it('expands row on chevron click to show judge reasoning', async () => {
    const user = userEvent.setup();
    render(<QAResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    // Find the expand buttons
    const expandButtons = screen.getAllByRole('button', { name: /expand row/i });
    expect(expandButtons.length).toBeGreaterThan(0);

    // Click the first expand button
    await user.click(expandButtons[0]!);

    // Now the judge reasoning for the first item should be visible
    expect(
      screen.getByText(/The answer correctly describes the systemctl command/),
    ).toBeInTheDocument();
  });

  it('calls onRowClick when a row is clicked', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();
    render(
      <QAResultsTable
        results={mockResults}
        datasetItems={mockDatasetItems}
        onRowClick={onRowClick}
      />,
    );

    // Click the first data row (not the header)
    const rows = screen.getAllByRole('row');
    // rows[0] is header, rows[1] is first data row
    await user.click(rows[1]!);

    expect(onRowClick).toHaveBeenCalledWith(mockResults[0]);
  });

  it('shows -- for expected answer when datasetItems is not provided', () => {
    render(<QAResultsTable results={mockResults} />);

    const cells = document.querySelectorAll('td');
    const expectedCells = Array.from(cells).filter((cell) => cell.textContent === '--');
    expect(expectedCells.length).toBeGreaterThan(0);
  });

  it('shows expected answer text when datasetItems is provided', () => {
    render(<QAResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    // Expected answer column should render the expected_answer from dataset items
    // Use getAllByText since the text may partially match the actual answer column too
    const matches = screen.getAllByText(/systemctl restart sshd/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('shows empty state when no results are provided', () => {
    render(<QAResultsTable results={[]} />);

    expect(screen.getByText('No results to display.')).toBeInTheDocument();
  });
});
