import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { PdfExportData } from './exportPdf';

const { mockHtml2canvas, mockSave, mockAddImage, mockAddPage, mockAutoTable } = vi.hoisted(() => ({
  mockSave: vi.fn(),
  mockAddImage: vi.fn(),
  mockAddPage: vi.fn(),
  mockAutoTable: vi.fn(),
  mockHtml2canvas: vi.fn(),
}));

vi.mock('html2canvas-pro', () => ({
  default: mockHtml2canvas,
}));

vi.mock('jspdf', () => {
  function MockJsPDF() {
    return {
      internal: { pageSize: { getWidth: () => 210, getHeight: () => 297 } },
      addImage: mockAddImage,
      addPage: mockAddPage,
      save: mockSave,
      text: vi.fn(),
      setFontSize: vi.fn(),
      setFont: vi.fn(),
      setTextColor: vi.fn(),
      setDrawColor: vi.fn(),
      line: vi.fn(),
      getTextWidth: vi.fn(() => 50),
      splitTextToSize: vi.fn((text: string) => [text]),
      lastAutoTable: { finalY: 100 },
    };
  }
  return { jsPDF: MockJsPDF };
});

vi.mock('jspdf-autotable', () => ({
  default: mockAutoTable,
}));

import { exportResultsPdf } from './exportPdf';

function makeData(overrides?: Partial<PdfExportData>): PdfExportData {
  return {
    evaluationName: 'Test Eval',
    evaluationMode: 'qa',
    metrics: {
      totalItems: 2,
      passRate: 1.0,
      meanScore: 0.85,
      medianScore: 0.85,
      passedItems: 2,
      failedItems: 0,
    },
    results: [
      {
        question: 'What is 2+2?',
        expectedAnswer: '4',
        actualAnswer: '4',
        score: 1.0,
        passed: true,
        judgeReasoning: 'Correct answer.',
        scoresBreakdown: null,
        contestantModel: null,
      },
    ],
    ...overrides,
  };
}

describe('exportResultsPdf', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
    document.documentElement.classList.remove('pdf-capture');
  });

  it('creates a PDF and triggers download with formatted filename', async () => {
    await exportResultsPdf(makeData());
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation-Test-Eval-\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('renders the summary table via autoTable', async () => {
    await exportResultsPdf(makeData());
    expect(mockAutoTable).toHaveBeenCalledTimes(1);
    const call = mockAutoTable.mock.calls[0]!;
    expect(call[1].head[0]).toContain('Question');
    expect(call[1].body.length).toBe(1);
  });

  it('sanitizes special characters in filename', async () => {
    await exportResultsPdf(makeData({ evaluationName: 'My Eval / Test #1' }));
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation-My-Eval---Test--1-\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('preserves underscores and hyphens in filename', async () => {
    await exportResultsPdf(makeData({ evaluationName: 'my_eval-name' }));
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation-my_eval-name-\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('handles empty evaluation name', async () => {
    await exportResultsPdf(makeData({ evaluationName: '' }));
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation--\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('uses arena table columns when mode is arena', async () => {
    await exportResultsPdf(
      makeData({
        evaluationMode: 'arena',
        results: [
          {
            question: 'Test?',
            actualAnswer: 'yes',
            score: 0.9,
            passed: true,
            contestantModel: 'gpt-4',
            judgeReasoning: null,
            scoresBreakdown: null,
          },
        ],
      }),
    );
    const call = mockAutoTable.mock.calls[0]!;
    expect(call[1].head[0]).toContain('Contestant');
  });

  it('captures chart elements with html2canvas when provided', async () => {
    const chartEl = document.createElement('div');
    const mockCanvas = {
      width: 400,
      height: 300,
      toDataURL: vi.fn(() => 'data:image/png;base64,chart'),
    };
    mockHtml2canvas.mockResolvedValueOnce(mockCanvas);

    // Mock Image for aspect ratio calculation
    const origImage = globalThis.Image;
    globalThis.Image = class extends origImage {
      constructor() {
        super();
        setTimeout(() => {
          Object.defineProperty(this, 'width', { value: 400 });
          Object.defineProperty(this, 'height', { value: 300 });
          this.onload?.(new Event('load'));
        }, 0);
      }
    } as unknown as typeof Image;

    await exportResultsPdf(makeData({ chartElements: [chartEl] }));

    expect(mockHtml2canvas).toHaveBeenCalledWith(chartEl, expect.objectContaining({ scale: 2 }));
    expect(mockAddImage).toHaveBeenCalled();

    globalThis.Image = origImage;
  });

  it('does not call html2canvas when no chart elements provided', async () => {
    await exportResultsPdf(makeData());
    expect(mockHtml2canvas).not.toHaveBeenCalled();
  });

  it('removes pdf-capture class after chart capture', async () => {
    const chartEl = document.createElement('div');
    const mockCanvas = {
      width: 400,
      height: 300,
      toDataURL: vi.fn(() => 'data:image/png;base64,chart'),
    };
    mockHtml2canvas.mockResolvedValueOnce(mockCanvas);

    const origImage = globalThis.Image;
    globalThis.Image = class extends origImage {
      constructor() {
        super();
        setTimeout(() => {
          Object.defineProperty(this, 'width', { value: 400 });
          Object.defineProperty(this, 'height', { value: 300 });
          this.onload?.(new Event('load'));
        }, 0);
      }
    } as unknown as typeof Image;

    await exportResultsPdf(makeData({ chartElements: [chartEl] }));
    expect(document.documentElement.classList.contains('pdf-capture')).toBe(false);

    globalThis.Image = origImage;
  });
});
