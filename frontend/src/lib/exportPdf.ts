import html2canvas from 'html2canvas-pro';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

const A4_W = 210;
const A4_H = 297;
const M = 12; // margin
const USABLE_W = A4_W - M * 2;

interface PdfResultItem {
  question: string;
  expectedAnswer?: string | null;
  actualAnswer?: string | null;
  score: number | null;
  passed: boolean | null;
  judgeReasoning?: string | null;
  scoresBreakdown?: Record<string, number> | null;
  contestantModel?: string | null;
}

export interface PdfExportData {
  evaluationName: string;
  evaluationMode: string;
  metrics: {
    totalItems: number;
    passRate: number;
    meanScore: number;
    medianScore: number;
    passedItems: number;
    failedItems: number;
  };
  results: PdfResultItem[];
  chartElements?: HTMLElement[];
}

async function captureCharts(
  elements: HTMLElement[],
): Promise<string[]> {
  document.documentElement.classList.add('pdf-capture');
  try {
    const images: string[] = [];
    for (const el of elements) {
      const canvas = await html2canvas(el, {
        useCORS: true,
        scale: 2,
        backgroundColor: '#ffffff',
      });
      images.push(canvas.toDataURL('image/png'));
    }
    return images;
  } finally {
    document.documentElement.classList.remove('pdf-capture');
  }
}

function addWrappedText(
  pdf: jsPDF,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
): number {
  const lines = pdf.splitTextToSize(text, maxWidth) as string[];
  for (const line of lines) {
    if (y > A4_H - M) {
      pdf.addPage();
      y = M;
    }
    pdf.text(line, x, y);
    y += lineHeight;
  }
  return y;
}

function ensureSpace(pdf: jsPDF, y: number, needed: number): number {
  if (y + needed > A4_H - M) {
    pdf.addPage();
    return M;
  }
  return y;
}

export async function exportResultsPdf(data: PdfExportData): Promise<void> {
  const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  let y = M;

  // --- Header ---
  pdf.setFontSize(16);
  pdf.setFont('helvetica', 'bold');
  pdf.text(data.evaluationName, M, y + 5);
  pdf.setFontSize(9);
  pdf.setFont('helvetica', 'normal');
  pdf.setTextColor(100);
  pdf.text(data.evaluationMode.toUpperCase(), M + pdf.getTextWidth(data.evaluationName) + 4, y + 5);
  pdf.setTextColor(0);
  y += 14;

  // --- Metrics row ---
  const metricLabels = ['Total Items', 'Pass Rate', 'Mean Score', 'Median Score'];
  const metricValues = [
    String(data.metrics.totalItems),
    `${(data.metrics.passRate * 100).toFixed(1)}%`,
    data.metrics.meanScore.toFixed(3),
    data.metrics.medianScore.toFixed(3),
  ];
  const colW = USABLE_W / 4;

  pdf.setFontSize(8);
  pdf.setTextColor(120);
  metricLabels.forEach((label, i) => {
    pdf.text(label, M + i * colW, y);
  });
  y += 5;
  pdf.setFontSize(18);
  pdf.setTextColor(0);
  pdf.setFont('helvetica', 'bold');
  metricValues.forEach((val, i) => {
    pdf.text(val, M + i * colW, y);
  });
  pdf.setFont('helvetica', 'normal');
  y += 10;

  // --- Charts (as images) ---
  if (data.chartElements && data.chartElements.length > 0) {
    // Wait for Recharts animations to complete
    await new Promise((resolve) => setTimeout(resolve, 500));

    const chartImages = await captureCharts(data.chartElements);
    const chartW = USABLE_W / chartImages.length;

    for (let i = 0; i < chartImages.length; i++) {
      const img = new Image();
      img.src = chartImages[i]!;
      await new Promise<void>((resolve) => {
        img.onload = () => resolve();
        img.onerror = () => resolve();
      });

      const aspectRatio = img.height / img.width;
      const imgW = chartW - 4;
      const imgH = imgW * aspectRatio;
      const chartY = ensureSpace(pdf, y, imgH + 4);
      pdf.addImage(chartImages[i]!, 'PNG', M + i * chartW + 2, chartY, imgW, imgH);
    }

    // Estimate chart height from first image
    if (chartImages.length > 0) {
      const img = new Image();
      img.src = chartImages[0]!;
      await new Promise<void>((resolve) => {
        img.onload = () => resolve();
        img.onerror = () => resolve();
      });
      y += (USABLE_W / chartImages.length - 4) * (img.height / img.width) + 8;
    }
  }

  // --- Separator ---
  y = ensureSpace(pdf, y, 15);
  pdf.setDrawColor(220);
  pdf.line(M, y, A4_W - M, y);
  y += 8;

  // --- Per-Item Results ---
  pdf.setFontSize(14);
  pdf.setFont('helvetica', 'bold');
  pdf.text('Per-Item Results', M, y);
  pdf.setFont('helvetica', 'normal');
  y += 8;

  // Summary table
  const isArena = data.evaluationMode === 'arena';
  const tableHead = isArena
    ? [['#', 'Contestant', 'Question', 'Score', 'Result']]
    : [['#', 'Question', 'Score', 'Result']];

  const tableBody = data.results.map((r, i) => {
    const question = r.question.length > 80 ? r.question.slice(0, 80) + '...' : r.question;
    const score = r.score != null ? `${(r.score * 100).toFixed(0)}%` : '--';
    const result = r.passed === true ? 'Pass' : r.passed === false ? 'Fail' : '--';
    if (isArena) {
      return [String(i + 1), r.contestantModel ?? '--', question, score, result];
    }
    return [String(i + 1), question, score, result];
  });

  autoTable(pdf, {
    startY: y,
    head: tableHead,
    body: tableBody,
    theme: 'grid',
    headStyles: { fillColor: [240, 240, 240], textColor: [30, 30, 30], fontStyle: 'bold', fontSize: 8 },
    bodyStyles: { fontSize: 8, textColor: [30, 30, 30] },
    columnStyles: isArena
      ? { 0: { cellWidth: 8 }, 1: { cellWidth: 30 }, 3: { cellWidth: 16 }, 4: { cellWidth: 16 } }
      : { 0: { cellWidth: 8 }, 2: { cellWidth: 16 }, 3: { cellWidth: 16 } },
    margin: { left: M, right: M },
    styles: { cellPadding: 2, overflow: 'linebreak' },
    didParseCell: (hookData) => {
      const resultColIdx = isArena ? 4 : 3;
      if (hookData.section === 'body' && hookData.column.index === resultColIdx) {
        if (hookData.cell.raw === 'Pass') {
          hookData.cell.styles.textColor = [22, 163, 74];
          hookData.cell.styles.fontStyle = 'bold';
        } else if (hookData.cell.raw === 'Fail') {
          hookData.cell.styles.textColor = [220, 38, 38];
          hookData.cell.styles.fontStyle = 'bold';
        }
      }
    },
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  y = (pdf as any).lastAutoTable.finalY + 10;

  // --- Detailed results per item ---
  pdf.setFontSize(14);
  pdf.setFont('helvetica', 'bold');
  y = ensureSpace(pdf, y, 20);
  pdf.text('Detailed Results', M, y);
  pdf.setFont('helvetica', 'normal');
  y += 8;

  const isQA = data.evaluationMode === 'qa';
  const isRAG = data.evaluationMode === 'rag';
  const showExpected = isQA || isRAG;

  for (let i = 0; i < data.results.length; i++) {
    const r = data.results[i]!;
    const score = r.score != null ? `${(r.score * 100).toFixed(0)}%` : '--';
    const passLabel = r.passed === true ? 'PASS' : r.passed === false ? 'FAIL' : '--';

    // Item header
    y = ensureSpace(pdf, y, 25);
    pdf.setDrawColor(200);
    pdf.line(M, y, A4_W - M, y);
    y += 5;

    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'bold');
    const itemHeader = `Item ${i + 1}  —  Score: ${score}  |  ${passLabel}`;
    if (isArena && r.contestantModel) {
      pdf.text(`${itemHeader}  |  Model: ${r.contestantModel}`, M, y);
    } else {
      pdf.text(itemHeader, M, y);
    }
    y += 6;

    // Question
    pdf.setFontSize(9);
    pdf.setFont('helvetica', 'bold');
    pdf.text('Question', M, y);
    y += 4;
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(8.5);
    y = addWrappedText(pdf, r.question, M, y, USABLE_W, 3.8);
    y += 2;

    // Expected answer
    if (showExpected && r.expectedAnswer) {
      y = ensureSpace(pdf, y, 10);
      pdf.setFontSize(9);
      pdf.setFont('helvetica', 'bold');
      pdf.text('Expected Answer', M, y);
      y += 4;
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(8.5);
      y = addWrappedText(pdf, r.expectedAnswer, M, y, USABLE_W, 3.8);
      y += 2;
    }

    // Actual answer
    if (r.actualAnswer) {
      y = ensureSpace(pdf, y, 10);
      pdf.setFontSize(9);
      pdf.setFont('helvetica', 'bold');
      pdf.text('Actual Answer', M, y);
      y += 4;
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(8.5);
      y = addWrappedText(pdf, r.actualAnswer, M, y, USABLE_W, 3.8);
      y += 2;
    }

    // Scores breakdown
    if (r.scoresBreakdown && Object.keys(r.scoresBreakdown).length > 0) {
      y = ensureSpace(pdf, y, 10);
      pdf.setFontSize(9);
      pdf.setFont('helvetica', 'bold');
      pdf.text('Score Breakdown', M, y);
      y += 4;
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(8.5);
      for (const [key, value] of Object.entries(r.scoresBreakdown)) {
        y = ensureSpace(pdf, y, 5);
        pdf.text(`  ${key}: ${value.toFixed(3)}`, M, y);
        y += 3.8;
      }
      y += 2;
    }

    // Judge reasoning
    if (r.judgeReasoning) {
      y = ensureSpace(pdf, y, 10);
      pdf.setFontSize(9);
      pdf.setFont('helvetica', 'bold');
      pdf.text('Judge Reasoning', M, y);
      y += 4;
      pdf.setFont('helvetica', 'italic');
      pdf.setFontSize(8.5);
      pdf.setTextColor(80);
      y = addWrappedText(pdf, r.judgeReasoning, M + 3, y, USABLE_W - 3, 3.8);
      pdf.setTextColor(0);
      pdf.setFont('helvetica', 'normal');
      y += 4;
    }
  }

  // --- Footer with timestamp ---
  y = ensureSpace(pdf, y, 10);
  pdf.setFontSize(7);
  pdf.setTextColor(150);
  pdf.text(`Generated by eval-studio on ${new Date().toISOString().slice(0, 19).replace('T', ' ')}`, M, y);
  pdf.setTextColor(0);

  // Save
  const sanitizedName = data.evaluationName.replace(/[^a-zA-Z0-9_-]/g, '-');
  const date = new Date().toISOString().slice(0, 10);
  pdf.save(`evaluation-${sanitizedName}-${date}.pdf`);
}
