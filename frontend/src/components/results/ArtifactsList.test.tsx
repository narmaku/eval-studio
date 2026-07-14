import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ArtifactsList } from './ArtifactsList';
import type { Artifact } from '@/types';

function paginated(items: Artifact[]) {
  return { items, total: items.length, page: 1, page_size: 100, pages: 1 };
}

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
    mockListArtifacts.mockResolvedValue(paginated([]));
    const { container } = render(<ArtifactsList evaluationId="eval-1" />);
    await waitFor(() => {
      expect(mockListArtifacts).toHaveBeenCalledWith('eval-1');
    });
    expect(container.innerHTML).toBe('');
  });

  it('renders artifact list with correct data', async () => {
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
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
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('1.5 KB')).toBeInTheDocument();
    });
    expect(screen.getByText('256 B')).toBeInTheDocument();
    expect(screen.getByText('2.0 MB')).toBeInTheDocument();
  });

  it('shows preview button only for text/json artifacts', async () => {
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
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
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
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

    // JSON is now rendered with syntax highlighting — individual tokens appear in separate spans
    await waitFor(() => {
      expect(screen.getByText('"key"')).toBeInTheDocument();
    });
    expect(screen.getByText('"value"')).toBeInTheDocument();
  });

  it('calls download URL when download button is clicked', async () => {
    const user = userEvent.setup();
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
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
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
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
    mockListArtifacts.mockResolvedValue(paginated(csvArtifact));
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
    mockListArtifacts.mockResolvedValue(paginated(mdArtifact));
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
    mockListArtifacts.mockResolvedValue(paginated(htmlArtifact));
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
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
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
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
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
    mockListArtifacts.mockResolvedValue(paginated(zeroByteArtifact));
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
    mockListArtifacts.mockResolvedValue(paginated(gbArtifact));
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('1.0 GB')).toBeInTheDocument();
    });
  });

  // --- Content-aware preview renderer tests ---

  describe('content-aware preview renderers', () => {
    async function openPreviewFor(artifact: Artifact, content: string) {
      const user = userEvent.setup();
      mockListArtifacts.mockResolvedValue(paginated([artifact]));
      mockPreviewArtifact.mockResolvedValue(content);
      render(<ArtifactsList evaluationId="eval-1" />);

      await waitFor(() => {
        expect(screen.getByText(artifact.filename)).toBeInTheDocument();
      });

      const previewBtn = screen.getByTitle('Preview');
      await user.click(previewBtn);

      await waitFor(() => {
        expect(mockPreviewArtifact).toHaveBeenCalledWith(artifact.id);
      });

      return user;
    }

    const jsonArtifact: Artifact = {
      id: 'art-json',
      evaluation_id: 'eval-1',
      filename: 'data.json',
      content_type: 'application/json',
      size_bytes: 100,
      description: null,
      created_at: '2026-01-15T10:00:00Z',
    };

    const csvArtifact: Artifact = {
      id: 'art-csv',
      evaluation_id: 'eval-1',
      filename: 'results.csv',
      content_type: 'text/csv',
      size_bytes: 80,
      description: null,
      created_at: '2026-01-15T10:00:00Z',
    };

    const markdownArtifact: Artifact = {
      id: 'art-md',
      evaluation_id: 'eval-1',
      filename: 'report.md',
      content_type: 'text/markdown',
      size_bytes: 60,
      description: null,
      created_at: '2026-01-15T10:00:00Z',
    };

    const plainTextArtifact: Artifact = {
      id: 'art-txt',
      evaluation_id: 'eval-1',
      filename: 'log.txt',
      content_type: 'text/plain',
      size_bytes: 40,
      description: null,
      created_at: '2026-01-15T10:00:00Z',
    };

    it('renders JSON content with syntax-highlighted key-value tokens', async () => {
      await openPreviewFor(jsonArtifact, '{"name": "Alice", "score": 42}');

      await waitFor(() => {
        expect(screen.getByText('"name"')).toBeInTheDocument();
      });
      expect(screen.getByText('"Alice"')).toBeInTheDocument();
      expect(screen.getByText('"score"')).toBeInTheDocument();
      expect(screen.getByText('42')).toBeInTheDocument();
    });

    it('renders JSON with nested objects', async () => {
      await openPreviewFor(jsonArtifact, '{"meta": {"version": 7}}');

      await waitFor(() => {
        expect(screen.getByText('"meta"')).toBeInTheDocument();
      });
      expect(screen.getByText('"version"')).toBeInTheDocument();
      expect(screen.getByText('7')).toBeInTheDocument();
    });

    it('renders JSON null and boolean values', async () => {
      await openPreviewFor(jsonArtifact, '{"active": true, "deleted": false, "notes": null}');

      await waitFor(() => {
        expect(screen.getByText('"active"')).toBeInTheDocument();
      });
      expect(screen.getByText('true')).toBeInTheDocument();
      expect(screen.getByText('false')).toBeInTheDocument();
      expect(screen.getByText('null')).toBeInTheDocument();
    });

    it('renders empty JSON object as {}', async () => {
      await openPreviewFor(jsonArtifact, '{}');

      await waitFor(() => {
        expect(screen.getByText('{}')).toBeInTheDocument();
      });
    });

    it('renders empty JSON array as []', async () => {
      await openPreviewFor(jsonArtifact, '[]');

      await waitFor(() => {
        expect(screen.getByText('[]')).toBeInTheDocument();
      });
    });

    it('falls back to plain text when JSON is invalid', async () => {
      const invalidJson = '{not valid json!!!}';
      await openPreviewFor(jsonArtifact, invalidJson);

      // Invalid JSON should be displayed as plain text in a <pre> block
      await waitFor(() => {
        expect(screen.getByText(invalidJson)).toBeInTheDocument();
      });
      // Should render in a <pre> tag (plain text fallback)
      const preElement = screen.getByText(invalidJson).closest('pre');
      expect(preElement).toBeInTheDocument();
    });

    it('renders CSV content as a table with header and body rows', async () => {
      const csvContent = 'Name,Score,Grade\nAlice,95,A\nBob,82,B';
      await openPreviewFor(csvArtifact, csvContent);

      // Check header cells
      await waitFor(() => {
        expect(screen.getByText('Name')).toBeInTheDocument();
      });
      expect(screen.getByText('Score')).toBeInTheDocument();
      expect(screen.getByText('Grade')).toBeInTheDocument();

      // Check body cells
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('95')).toBeInTheDocument();
      expect(screen.getByText('A')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
      expect(screen.getByText('82')).toBeInTheDocument();
      expect(screen.getByText('B')).toBeInTheDocument();

      // Verify it renders as a table structure
      expect(document.querySelector('table')).toBeInTheDocument();
    });

    it('renders CSV with header only (no data rows)', async () => {
      await openPreviewFor(csvArtifact, 'Col1,Col2,Col3');

      await waitFor(() => {
        expect(screen.getByText('Col1')).toBeInTheDocument();
      });
      expect(screen.getByText('Col2')).toBeInTheDocument();
      expect(screen.getByText('Col3')).toBeInTheDocument();
    });

    it('renders markdown content with formatted output', async () => {
      const mdContent = '# Heading\n\nSome **bold** text and a [link](https://example.com).';
      await openPreviewFor(markdownArtifact, mdContent);

      await waitFor(() => {
        expect(screen.getByText('Heading')).toBeInTheDocument();
      });
      // ReactMarkdown renders "bold" within a <strong> tag, inside the paragraph
      expect(screen.getByText('link')).toBeInTheDocument();
    });

    it('renders plain text content in a preformatted block', async () => {
      const textContent = 'This is plain text output';
      await openPreviewFor(plainTextArtifact, textContent);

      await waitFor(() => {
        expect(screen.getByText(textContent)).toBeInTheDocument();
      });
      const preElement = screen.getByText(textContent).closest('pre');
      expect(preElement).toBeInTheDocument();
    });
  });

  // --- Content type badge tests ---

  describe('content type badge in preview dialog', () => {
    it('shows JSON badge when previewing a JSON artifact', async () => {
      const user = userEvent.setup();
      mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
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
        expect(screen.getByText('JSON')).toBeInTheDocument();
      });
    });

    it('shows Text badge when previewing a plain text artifact', async () => {
      const user = userEvent.setup();
      mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
      mockPreviewArtifact.mockResolvedValue('Hello world');
      render(<ArtifactsList evaluationId="eval-1" />);

      await waitFor(() => {
        expect(screen.getByText('output.txt')).toBeInTheDocument();
      });

      const previewButtons = screen.getAllByTitle('Preview');
      await user.click(previewButtons[1]!);

      await waitFor(() => {
        expect(mockPreviewArtifact).toHaveBeenCalledWith('art-2');
      });

      await waitFor(() => {
        expect(screen.getByText('Text')).toBeInTheDocument();
      });
    });

    it('shows CSV badge when previewing a CSV artifact', async () => {
      const user = userEvent.setup();
      const csvArtifact: Artifact = {
        id: 'art-csv2',
        evaluation_id: 'eval-1',
        filename: 'data.csv',
        content_type: 'text/csv',
        size_bytes: 50,
        description: null,
        created_at: '2026-01-15T10:00:00Z',
      };
      mockListArtifacts.mockResolvedValue(paginated([csvArtifact]));
      mockPreviewArtifact.mockResolvedValue('a,b\n1,2');
      render(<ArtifactsList evaluationId="eval-1" />);

      await waitFor(() => {
        expect(screen.getByText('data.csv')).toBeInTheDocument();
      });

      await user.click(screen.getByTitle('Preview'));

      await waitFor(() => {
        expect(screen.getByText('CSV')).toBeInTheDocument();
      });
    });

    it('shows Markdown badge when previewing a markdown artifact', async () => {
      const user = userEvent.setup();
      const mdArtifact: Artifact = {
        id: 'art-md2',
        evaluation_id: 'eval-1',
        filename: 'notes.md',
        content_type: 'text/markdown',
        size_bytes: 30,
        description: null,
        created_at: '2026-01-15T10:00:00Z',
      };
      mockListArtifacts.mockResolvedValue(paginated([mdArtifact]));
      mockPreviewArtifact.mockResolvedValue('# Hello');
      render(<ArtifactsList evaluationId="eval-1" />);

      await waitFor(() => {
        expect(screen.getByText('notes.md')).toBeInTheDocument();
      });

      await user.click(screen.getByTitle('Preview'));

      await waitFor(() => {
        expect(screen.getByText('Markdown')).toBeInTheDocument();
      });
    });
  });

  // --- Copy button tests ---

  describe('copy button', () => {
    it('shows copy button when preview content is loaded', async () => {
      const user = userEvent.setup();
      mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
      mockPreviewArtifact.mockResolvedValue('some content');
      render(<ArtifactsList evaluationId="eval-1" />);

      await waitFor(() => {
        expect(screen.getByText('output.txt')).toBeInTheDocument();
      });

      const previewButtons = screen.getAllByTitle('Preview');
      await user.click(previewButtons[1]!);

      await waitFor(() => {
        expect(screen.getByText('Copy')).toBeInTheDocument();
      });
    });

    it('copies content to clipboard and shows "Copied" feedback', async () => {
      const user = userEvent.setup();
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      });

      mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
      mockPreviewArtifact.mockResolvedValue('clipboard content');
      render(<ArtifactsList evaluationId="eval-1" />);

      await waitFor(() => {
        expect(screen.getByText('output.txt')).toBeInTheDocument();
      });

      const previewButtons = screen.getAllByTitle('Preview');
      await user.click(previewButtons[1]!);

      await waitFor(() => {
        expect(screen.getByText('Copy')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Copy'));

      await waitFor(() => {
        expect(writeTextMock).toHaveBeenCalledWith('clipboard content');
      });

      await waitFor(() => {
        expect(screen.getByText('Copied')).toBeInTheDocument();
      });
    });

    it('handles clipboard write failure gracefully', async () => {
      const user = userEvent.setup();
      const writeTextMock = vi.fn().mockRejectedValue(new Error('Clipboard denied'));
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      });
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
      mockPreviewArtifact.mockResolvedValue('some text');
      render(<ArtifactsList evaluationId="eval-1" />);

      await waitFor(() => {
        expect(screen.getByText('output.txt')).toBeInTheDocument();
      });

      const previewButtons = screen.getAllByTitle('Preview');
      await user.click(previewButtons[1]!);

      await waitFor(() => {
        expect(screen.getByText('Copy')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Copy'));

      await waitFor(() => {
        expect(writeTextMock).toHaveBeenCalled();
      });

      // Should not crash — button should remain as "Copy" (not "Copied")
      expect(screen.getByText('Copy')).toBeInTheDocument();

      warnSpy.mockRestore();
    });
  });

  // --- Empty content handling ---

  it('handles empty string content gracefully in preview', async () => {
    const user = userEvent.setup();
    mockListArtifacts.mockResolvedValue(paginated(mockArtifacts));
    mockPreviewArtifact.mockResolvedValue('');
    render(<ArtifactsList evaluationId="eval-1" />);

    await waitFor(() => {
      expect(screen.getByText('output.txt')).toBeInTheDocument();
    });

    const previewButtons = screen.getAllByTitle('Preview');
    await user.click(previewButtons[1]!);

    // Dialog should open and display the preview area without crashing
    await waitFor(() => {
      expect(mockPreviewArtifact).toHaveBeenCalledWith('art-2');
    });

    // The copy button should still appear for empty content (content is not null)
    await waitFor(() => {
      expect(screen.getByText('Copy')).toBeInTheDocument();
    });
  });
});
