import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { QAResultsTable } from './QAResultsTable';
import type { Score, DatasetItem } from '@/types';

const mockScores: Score[] = [
  {
    item_id: 'item-1',
    dimensions: { accuracy: 0.9 },
    overall: 0.9,
    pass: true,
    judge_reasoning: 'The answer correctly describes the systemctl command.',
    raw_response: 'Use systemctl restart sshd',
  },
  {
    item_id: 'item-2',
    dimensions: { accuracy: 0.3 },
    overall: 0.3,
    pass: false,
    judge_reasoning: 'The answer is incomplete and misses key steps.',
    raw_response: 'Just restart it',
  },
  {
    item_id: 'item-3',
    dimensions: { accuracy: 0.75 },
    overall: 0.75,
    pass: true,
    judge_reasoning: 'Adequate coverage of firewall rules.',
    raw_response: 'Run firewall-cmd --add-port=443/tcp --permanent',
  },
  {
    item_id: 'item-4',
    dimensions: { accuracy: 0.5 },
    overall: 0.5,
    pass: false,
    judge_reasoning: 'Missing SELinux context adjustment.',
    raw_response: 'Change the port in sshd_config',
  },
  {
    item_id: 'item-5',
    dimensions: { accuracy: 0.95 },
    overall: 0.95,
    pass: true,
    judge_reasoning: 'Excellent explanation of LVM concepts.',
    raw_response: 'Use pvcreate, vgcreate, and lvcreate in sequence.',
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
    render(
      <QAResultsTable scores={mockScores} datasetItems={mockDatasetItems} />,
    );

    // We should see 5 rows of data (not counting header)
    const rows = screen.getAllByRole('row');
    // 1 header row + 5 data rows = 6
    expect(rows).toHaveLength(6);
  });

  it('displays pass/fail badges correctly', () => {
    render(
      <QAResultsTable scores={mockScores} datasetItems={mockDatasetItems} />,
    );

    const passBadges = screen.getAllByText('Pass');
    const failBadges = screen.getAllByText('Fail');
    expect(passBadges).toHaveLength(3);
    expect(failBadges).toHaveLength(2);
  });

  it('displays question text from dataset items', () => {
    render(
      <QAResultsTable scores={mockScores} datasetItems={mockDatasetItems} />,
    );

    expect(
      screen.getByText(/How do you restart the SSH service/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Explain LVM volume creation/),
    ).toBeInTheDocument();
  });

  it('expands row on chevron click to show judge reasoning', async () => {
    const user = userEvent.setup();
    render(
      <QAResultsTable scores={mockScores} datasetItems={mockDatasetItems} />,
    );

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
        scores={mockScores}
        datasetItems={mockDatasetItems}
        onRowClick={onRowClick}
      />,
    );

    // Click the first data row (not the header)
    const rows = screen.getAllByRole('row');
    // rows[0] is header, rows[1] is first data row
    await user.click(rows[1]!);

    expect(onRowClick).toHaveBeenCalledWith(mockScores[0]);
  });

  it('shows empty state when no scores are provided', () => {
    render(<QAResultsTable scores={[]} />);

    expect(screen.getByText('No results to display.')).toBeInTheDocument();
  });
});
