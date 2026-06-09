import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const { mockHtml2canvas, mockSave, mockAddImage, mockAddPage } = vi.hoisted(() => {
  const mockSave = vi.fn();
  const mockAddImage = vi.fn();
  const mockAddPage = vi.fn();
  const mockHtml2canvas = vi.fn();
  return { mockHtml2canvas, mockSave, mockAddImage, mockAddPage };
});

function createMockCanvas(width: number, height: number) {
  const mockCtx = {
    drawImage: vi.fn(),
  };
  // Mock document.createElement('canvas') to return canvases with getContext
  const origCreate = document.createElement.bind(document);
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
    const el = origCreate(tag);
    if (tag === 'canvas') {
      (el as unknown as Record<string, unknown>).getContext = vi.fn(() => mockCtx);
      (el as unknown as Record<string, unknown>).toDataURL = vi.fn(
        () => 'data:image/png;base64,page',
      );
    }
    return el;
  });

  return {
    width,
    height,
    toDataURL: vi.fn(() => 'data:image/png;base64,full'),
    getContext: vi.fn(() => mockCtx),
    mockCtx,
  };
}

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
    };
  }
  return { jsPDF: MockJsPDF };
});

import { exportResultsPdf } from './exportPdf';

describe('exportResultsPdf', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.clearAllMocks();
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.removeChild(container);
    document.documentElement.classList.remove('pdf-capture');
    vi.restoreAllMocks();
  });

  it('calls html2canvas with the provided element and fixed width', async () => {
    const canvas = createMockCanvas(800, 600);
    mockHtml2canvas.mockResolvedValueOnce(canvas);

    await exportResultsPdf(container, 'my-eval');
    expect(mockHtml2canvas).toHaveBeenCalledWith(
      container,
      expect.objectContaining({
        useCORS: true,
        scale: 2,
        backgroundColor: '#ffffff',
        width: 800,
        windowWidth: 800,
      }),
    );
  });

  it('creates a PDF and triggers download with formatted filename', async () => {
    const canvas = createMockCanvas(800, 600);
    mockHtml2canvas.mockResolvedValueOnce(canvas);

    await exportResultsPdf(container, 'my-eval');
    expect(mockAddImage).toHaveBeenCalled();
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation-my-eval-\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('adds pdf-capture class during export and removes it after', async () => {
    let classListDuringCapture: string[] = [];
    const canvas = createMockCanvas(800, 600);
    mockHtml2canvas.mockImplementation(() => {
      classListDuringCapture = [...document.documentElement.classList];
      return Promise.resolve(canvas);
    });

    await exportResultsPdf(container, 'test');
    expect(classListDuringCapture).toContain('pdf-capture');
    expect(document.documentElement.classList.contains('pdf-capture')).toBe(false);
  });

  it('removes pdf-capture class even when html2canvas throws', async () => {
    mockHtml2canvas.mockRejectedValueOnce(new Error('capture failed'));

    await expect(exportResultsPdf(container, 'test')).rejects.toThrow('capture failed');
    expect(document.documentElement.classList.contains('pdf-capture')).toBe(false);
  });

  it('restores element inline styles after export', async () => {
    const canvas = createMockCanvas(800, 600);
    mockHtml2canvas.mockResolvedValueOnce(canvas);

    container.style.width = '100%';
    await exportResultsPdf(container, 'test');
    expect(container.style.width).toBe('100%');
  });

  it('sanitizes special characters in filename', async () => {
    const canvas = createMockCanvas(800, 600);
    mockHtml2canvas.mockResolvedValueOnce(canvas);

    await exportResultsPdf(container, 'My Eval / Test #1');
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation-My-Eval---Test--1-\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('handles multi-page content by calling addPage', async () => {
    const canvas = createMockCanvas(800, 5000);
    mockHtml2canvas.mockResolvedValueOnce(canvas);

    await exportResultsPdf(container, 'tall-eval');
    expect(mockAddPage).toHaveBeenCalled();
    expect(mockAddImage.mock.calls.length).toBeGreaterThan(1);
  });

  it('does not call addPage when content fits on a single page', async () => {
    const canvas = createMockCanvas(800, 600);
    mockHtml2canvas.mockResolvedValueOnce(canvas);

    await exportResultsPdf(container, 'short-eval');
    expect(mockAddPage).not.toHaveBeenCalled();
    expect(mockAddImage).toHaveBeenCalledTimes(1);
  });

  it('preserves underscores and hyphens in the filename', async () => {
    const canvas = createMockCanvas(800, 600);
    mockHtml2canvas.mockResolvedValueOnce(canvas);

    await exportResultsPdf(container, 'my_eval-name');
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation-my_eval-name-\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('handles an empty evaluation name', async () => {
    const canvas = createMockCanvas(800, 600);
    mockHtml2canvas.mockResolvedValueOnce(canvas);

    await exportResultsPdf(container, '');
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation--\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });
});
