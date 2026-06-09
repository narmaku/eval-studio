import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Use vi.hoisted so that mock references are available in hoisted vi.mock factories
const { mockHtml2canvas, mockSave, mockAddImage, mockAddPage, mockCanvas } = vi.hoisted(() => {
  const mockCanvas = {
    width: 800,
    height: 1200,
    toDataURL: vi.fn(() => 'data:image/png;base64,fake'),
  };
  const mockHtml2canvas = vi.fn(() => Promise.resolve(mockCanvas));
  const mockSave = vi.fn();
  const mockAddImage = vi.fn();
  const mockAddPage = vi.fn();
  return { mockHtml2canvas, mockSave, mockAddImage, mockAddPage, mockCanvas };
});

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
    vi.clearAllMocks();
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
    document.documentElement.classList.remove('pdf-capture');
  });

  it('calls html2canvas with the provided element', async () => {
    await exportResultsPdf(container, 'my-eval');
    expect(mockHtml2canvas).toHaveBeenCalledWith(
      container,
      expect.objectContaining({ useCORS: true }),
    );
  });

  it('creates a PDF and triggers download with formatted filename', async () => {
    await exportResultsPdf(container, 'my-eval');
    expect(mockAddImage).toHaveBeenCalled();
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation-my-eval-\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('adds pdf-capture class during export and removes it after', async () => {
    let classListDuringCapture: string[] = [];
    mockHtml2canvas.mockImplementation(() => {
      classListDuringCapture = [...document.documentElement.classList];
      return Promise.resolve(mockCanvas);
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

  it('sanitizes special characters in filename', async () => {
    await exportResultsPdf(container, 'My Eval / Test #1');
    expect(mockSave).toHaveBeenCalledWith(
      expect.stringMatching(/^evaluation-My-Eval---Test--1-\d{4}-\d{2}-\d{2}\.pdf$/),
    );
  });

  it('handles multi-page content by calling addPage with correct offsets', async () => {
    // Make canvas very tall relative to page height to trigger pagination
    const tallCanvas = {
      ...mockCanvas,
      height: 5000,
      width: 800,
      toDataURL: vi.fn(() => 'data:image/png;base64,fake'),
    };
    mockHtml2canvas.mockResolvedValueOnce(tallCanvas);

    await exportResultsPdf(container, 'tall-eval');
    expect(mockAddPage).toHaveBeenCalled();

    // Verify each page shifts the image further up (negative y position)
    // Page 1 is at y=10 (margin), subsequent pages must have decreasing y
    const addImageCalls = mockAddImage.mock.calls;
    expect(addImageCalls.length).toBeGreaterThan(1);

    const firstPageY = addImageCalls[0][3] as number;
    expect(firstPageY).toBe(10); // margin

    for (let i = 1; i < addImageCalls.length; i++) {
      const pageY = addImageCalls[i][3] as number;
      const prevPageY = addImageCalls[i - 1][3] as number;
      expect(pageY).toBeLessThan(prevPageY);
    }
  });
});
