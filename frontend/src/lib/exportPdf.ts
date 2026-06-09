import html2canvas from 'html2canvas-pro';
import { jsPDF } from 'jspdf';

const A4_WIDTH_MM = 210;
const A4_HEIGHT_MM = 297;
const MARGIN_MM = 10;
const USABLE_WIDTH_MM = A4_WIDTH_MM - MARGIN_MM * 2;
const USABLE_HEIGHT_MM = A4_HEIGHT_MM - MARGIN_MM * 2;

// Fixed pixel width for capture — produces readable text at A4 scale
const CAPTURE_WIDTH_PX = 800;

export async function exportResultsPdf(
  element: HTMLElement,
  evaluationName: string,
): Promise<void> {
  document.documentElement.classList.add('pdf-capture');

  // Force a fixed width so content renders at a consistent, readable size
  const prevWidth = element.style.width;
  const prevMaxWidth = element.style.maxWidth;
  const prevMinWidth = element.style.minWidth;
  element.style.width = `${CAPTURE_WIDTH_PX}px`;
  element.style.maxWidth = `${CAPTURE_WIDTH_PX}px`;
  element.style.minWidth = `${CAPTURE_WIDTH_PX}px`;

  // Let the browser reflow at the new width
  await new Promise((resolve) => setTimeout(resolve, 50));

  try {
    const canvas = await html2canvas(element, {
      useCORS: true,
      scale: 2,
      backgroundColor: '#ffffff',
      width: CAPTURE_WIDTH_PX,
      windowWidth: CAPTURE_WIDTH_PX,
    });

    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

    const imgWidth = USABLE_WIDTH_MM;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    // Split canvas into pages by slicing the source image
    const pageImgHeight = (USABLE_HEIGHT_MM / imgWidth) * canvas.width;
    let srcY = 0;
    let pageIndex = 0;

    while (srcY < canvas.height) {
      const sliceHeight = Math.min(pageImgHeight, canvas.height - srcY);
      const destHeight = (sliceHeight * imgWidth) / canvas.width;

      // Create a canvas slice for this page
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = sliceHeight;
      const ctx = pageCanvas.getContext('2d');
      if (!ctx) throw new Error('Failed to get canvas context');

      ctx.drawImage(canvas, 0, srcY, canvas.width, sliceHeight, 0, 0, canvas.width, sliceHeight);

      const pageData = pageCanvas.toDataURL('image/png');

      if (pageIndex > 0) pdf.addPage();
      pdf.addImage(pageData, 'PNG', MARGIN_MM, MARGIN_MM, imgWidth, destHeight);

      srcY += sliceHeight;
      pageIndex++;
    }

    const sanitizedName = evaluationName.replace(/[^a-zA-Z0-9_-]/g, '-');
    const date = new Date().toISOString().slice(0, 10);
    pdf.save(`evaluation-${sanitizedName}-${date}.pdf`);
  } finally {
    element.style.width = prevWidth;
    element.style.maxWidth = prevMaxWidth;
    element.style.minWidth = prevMinWidth;
    document.documentElement.classList.remove('pdf-capture');
  }
}
