import html2canvas from 'html2canvas-pro';
import { jsPDF } from 'jspdf';

/**
 * Capture an HTML container as a multi-page PDF and trigger a browser download.
 *
 * During capture the `pdf-capture` CSS class is added to `<html>` so that
 * styles can force a light theme and hide elements marked with `data-no-print`.
 */
export async function exportResultsPdf(
  element: HTMLElement,
  evaluationName: string,
): Promise<void> {
  document.documentElement.classList.add('pdf-capture');

  try {
    const canvas = await html2canvas(element, {
      useCORS: true,
      scale: 2,
      backgroundColor: '#ffffff',
    });

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();

    // Scale the canvas width to fit A4 width with 10mm margins on each side
    const margin = 10;
    const usableWidth = pageWidth - margin * 2;
    const imgWidth = usableWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    let heightLeft = imgHeight;
    let position = margin;

    // First page
    pdf.addImage(imgData, 'PNG', margin, position, imgWidth, imgHeight);
    heightLeft -= pageHeight - margin * 2;

    // Additional pages if content overflows
    while (heightLeft > 0) {
      position = margin - (imgHeight - heightLeft);
      pdf.addPage();
      pdf.addImage(imgData, 'PNG', margin, position, imgWidth, imgHeight);
      heightLeft -= pageHeight - margin * 2;
    }

    const sanitizedName = evaluationName.replace(/[^a-zA-Z0-9_-]/g, '-');
    const date = new Date().toISOString().slice(0, 10);
    pdf.save(`evaluation-${sanitizedName}-${date}.pdf`);
  } finally {
    document.documentElement.classList.remove('pdf-capture');
  }
}
