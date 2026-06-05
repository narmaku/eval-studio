import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ArtifactsList } from './ArtifactsList';
import type { Artifact } from '@/types';

const mockArtifacts: Artifact[] = [
  {
    id: 'art-1',
    evaluation_id: 'eval-1',
    filename: 'report.json',
    content_type: 'application/json',
    size_bytes: 1536,
    description: 'Evaluation report',
    created_at: '2026-01-15T10:00:00Z',
  },
  {
    id: 'art-2',
    evaluation_id: 'eval-1',
    filename: 'output.txt',
    content_type: 'text/plain',
    size_bytes: 256,
    description: null,
    created_at: '2026-01-15T10:01:00Z',
  },
  {
    id: 'art-3',
    evaluation_id: 'eval-1',
    filename: 'screenshot.png',
    content_type: 'image/png',
    size_bytes: 2_097_152,
    description: 'Screenshot of the results',
    created_at: '2026-01-15T10:02:00Z',
  },
];

const mockListArtifacts = vi.fn();
const mockPreviewArtifact = vi.fn();
const mockGetArtifactDownloadUrl = vi.fn();

vi.mock('@/services/api', () => ({
  api: {
    listArtifacts: (...args: unknown[]) => mockListArtifacts(...args),
    previewArtifact: (...args: unknown[]) => mockPreviewArtifact(...args),
    getArtifactDownloadUrl: (...args: unknown[]) => mockGetArtifactDownloadUrl(...args),
  },
}));

describe('ArtifactsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetArtifactDownloadUrl.mockReturnValue('/api/v1/artifacts/art-1/download');
  });

  it('renders nothing when no artifacts exist', async () => {
    mockListArtifacts.mockResolvedValue([]);
    const { container } = render(<ArtifactsList evaluationId="eval-1" />);
    await waitFor(() => {
      expect(mockListArtifacts).toHaveBeenCalledWith('eval-1');
    });
    expect(container.innerHTML).toBe('');
  });

  it('renders artifact list with correct data', async () => {
    mockListArtifacts.mockResolvedValue(mockArtifacts);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('Artifacts')).toBeInTheDocument();
    });

    // Check filenames
    expect(screen.getByText('report.json')).toBeInTheDocument();
    expect(screen.getByText('output.txt')).toBeInTheDocument();
    expect(screen.getByText('screenshot.png')).toBeInTheDocument();

    // Check content types
    expect(screen.getByText('application/json')).toBeInTheDocument();
    expect(screen.getByText('text/plain')).toBeInTheDocument();
    expect(screen.getByText('image/png')).toBeInTheDocument();

    // Check descriptions
    expect(screen.getByText('Evaluation report')).toBeInTheDocument();
    expect(screen.getByText('Screenshot of the results')).toBeInTheDocument();

    // Check count badge
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('formats file sizes correctly', async () => {
    mockListArtifacts.mockResolvedValue(mockArtifacts);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('1.5 KB')).toBeInTheDocument();
    });
    expect(screen.getByText('256 B')).toBeInTheDocument();
    expect(screen.getByText('2.0 MB')).toBeInTheDocument();
  });

  it('shows preview button only for text/json artifacts', async () => {
    mockListArtifacts.mockResolvedValue(mockArtifacts);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('report.json')).toBeInTheDocument();
    });

    // Preview buttons should exist for text and json, not for image
    const previewButtons = screen.getAllByTitle('Preview');
    expect(previewButtons).toHaveLength(2);

    // Download buttons should exist for all artifacts
    const downloadButtons = screen.getAllByTitle('Download');
    expect(downloadButtons).toHaveLength(3);
  });

  it('opens preview dialog when preview button is clicked', async () => {
    const user = userEvent.setup();
    mockListArtifacts.mockResolvedValue(mockArtifacts);
    mockPreviewArtifact.mockResolvedValue('{"key": "value"}');
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('report.json')).toBeInTheDocument();
    });

    const previewButtons = screen.getAllByTitle('Preview');
    await user.click(previewButtons[0]!);

    await waitFor(() => {
      expect(mockPreviewArtifact).toHaveBeenCalledWith('art-1');
    });

    await waitFor(() => {
      expect(screen.getByText('{"key": "value"}')).toBeInTheDocument();
    });
  });

  it('calls download URL when download button is clicked', async () => {
    const user = userEvent.setup();
    mockListArtifacts.mockResolvedValue(mockArtifacts);
    mockGetArtifactDownloadUrl.mockReturnValue('/api/v1/artifacts/art-1/download');

    const mockOpen = vi.fn();
    vi.spyOn(window, 'open').mockImplementation(mockOpen);

    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('report.json')).toBeInTheDocument();
    });

    const downloadButtons = screen.getAllByTitle('Download');
    await user.click(downloadButtons[0]!);

    expect(mockGetArtifactDownloadUrl).toHaveBeenCalledWith('art-1');
    expect(mockOpen).toHaveBeenCalledWith('/api/v1/artifacts/art-1/download', '_blank');
  });

  it('shows error state when fetch fails', async () => {
    mockListArtifacts.mockRejectedValue(new Error('Network error'));
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('displays dashes for null descriptions', async () => {
    mockListArtifacts.mockResolvedValue(mockArtifacts);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('output.txt')).toBeInTheDocument();
    });

    // The null description should show "--"
    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it('renders nothing while loading', () => {
    // mockListArtifacts returns a promise that never resolves
    mockListArtifacts.mockReturnValue(new Promise(() => {}));
    const { container } = render(<ArtifactsList evaluationId="eval-loading" />);
    // Component returns null during loading state
    expect(container.innerHTML).toBe('');
  });

  it('shows preview button for text/csv artifacts', async () => {
    const csvArtifact: Artifact[] = [
      {
        id: 'art-csv',
        evaluation_id: 'eval-1',
        filename: 'data.csv',
        content_type: 'text/csv',
        size_bytes: 100,
        description: null,
        created_at: '2026-01-15T10:00:00Z',
      },
    ];
    mockListArtifacts.mockResolvedValue(csvArtifact);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('data.csv')).toBeInTheDocument();
    });

    expect(screen.getByTitle('Preview')).toBeInTheDocument();
  });

  it('shows preview button for text/markdown artifacts', async () => {
    const mdArtifact: Artifact[] = [
      {
        id: 'art-md',
        evaluation_id: 'eval-1',
        filename: 'notes.md',
        content_type: 'text/markdown',
        size_bytes: 50,
        description: null,
        created_at: '2026-01-15T10:00:00Z',
      },
    ];
    mockListArtifacts.mockResolvedValue(mdArtifact);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('notes.md')).toBeInTheDocument();
    });

    expect(screen.getByTitle('Preview')).toBeInTheDocument();
  });

  it('does not show preview button for text/html artifacts (XSS prevention)', async () => {
    const htmlArtifact: Artifact[] = [
      {
        id: 'art-html',
        evaluation_id: 'eval-1',
        filename: 'page.html',
        content_type: 'text/html',
        size_bytes: 200,
        description: null,
        created_at: '2026-01-15T10:00:00Z',
      },
    ];
    mockListArtifacts.mockResolvedValue(htmlArtifact);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('page.html')).toBeInTheDocument();
    });

    // No preview button should be rendered for HTML
    expect(screen.queryByTitle('Preview')).not.toBeInTheDocument();
    // Download should still be available
    expect(screen.getByTitle('Download')).toBeInTheDocument();
  });

  it('shows error in preview dialog when preview API fails', async () => {
    const user = userEvent.setup();
    mockListArtifacts.mockResolvedValue(mockArtifacts);
    mockPreviewArtifact.mockRejectedValue(new Error('Server error'));
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('report.json')).toBeInTheDocument();
    });

    const previewButtons = screen.getAllByTitle('Preview');
    await user.click(previewButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText(/Error loading preview: Server error/)).toBeInTheDocument();
    });
  });

  it('shows non-Error preview failure message', async () => {
    const user = userEvent.setup();
    mockListArtifacts.mockResolvedValue(mockArtifacts);
    mockPreviewArtifact.mockRejectedValue('string error');
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('report.json')).toBeInTheDocument();
    });

    const previewButtons = screen.getAllByTitle('Preview');
    await user.click(previewButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText(/Error loading preview: Failed to load preview/)).toBeInTheDocument();
    });
  });

  it('shows generic error message when fetch fails with non-Error', async () => {
    mockListArtifacts.mockRejectedValue('not an error object');
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load artifacts')).toBeInTheDocument();
    });
  });

  it('formats zero-byte file size correctly', async () => {
    const zeroByteArtifact: Artifact[] = [
      {
        id: 'art-zero',
        evaluation_id: 'eval-1',
        filename: 'empty.txt',
        content_type: 'text/plain',
        size_bytes: 0,
        description: null,
        created_at: '2026-01-15T10:00:00Z',
      },
    ];
    mockListArtifacts.mockResolvedValue(zeroByteArtifact);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('0 B')).toBeInTheDocument();
    });
  });

  it('formats gigabyte file size correctly', async () => {
    const gbArtifact: Artifact[] = [
      {
        id: 'art-gb',
        evaluation_id: 'eval-1',
        filename: 'huge.bin',
        content_type: 'application/octet-stream',
        size_bytes: 1_073_741_824, // 1 GB
        description: null,
        created_at: '2026-01-15T10:00:00Z',
      },
    ];
    mockListArtifacts.mockResolvedValue(gbArtifact);
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('1.0 GB')).toBeInTheDocument();
    });
  });
});
