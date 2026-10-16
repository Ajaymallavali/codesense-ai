import { jsPDF } from "jspdf";
import { request, API_BASE_URL, getStoredToken } from "./apiClient";
import { ReportSummary } from "../types";

export const reportApi = {
  async getSummary(repositoryId: string): Promise<ReportSummary> {
    return request<ReportSummary>(`/reports/summary?repositoryId=${repositoryId}`);
  },

  async downloadReport(repositoryId: string, reportType: "assessment" | "debt" = "assessment"): Promise<void> {
    const token = getStoredToken();
    const url = `${API_BASE_URL}/reports/download?repositoryId=${repositoryId}&reportType=${reportType}`;

    const headers = new Headers();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error(`Failed to download report: ${response.statusText}`);
    }

    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition");
    let filename = `codesense-${reportType}-report.md`;
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },

  async generatePdfReport(summary: ReportSummary, type: "assessment" | "debt" = "assessment"): Promise<void> {
    const doc = new jsPDF({
      orientation: "portrait",
      unit: "mm",
      format: "a4",
    });

    const pageWidth = 210;
    const pageHeight = 297;
    const margin = 14;
    const contentWidth = pageWidth - margin * 2;

    // Header Banner
    doc.setFillColor(15, 23, 42); // slate-900
    doc.rect(0, 0, pageWidth, 28, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(15);
    const title =
      type === "debt"
        ? "CodeSense AI - Technical Debt Remediation Plan"
        : "CodeSense AI - Quality & Security Assessment Report";
    doc.text(title, margin, 12);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(148, 163, 184); // slate-400
    doc.text("Authoritative Automated AST Intelligence & Code Health Audit", margin, 19);

    // Repository Meta Card
    let y = 35;
    doc.setFillColor(248, 250, 252);
    doc.setDrawColor(226, 232, 240);
    doc.roundedRect(margin, y, contentWidth, 18, 2, 2, "FD");

    doc.setTextColor(15, 23, 42);
    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.text(`Repository: ${summary.repository}`, margin + 4, y + 6);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.5);
    doc.setTextColor(100, 116, 139);
    doc.text(
      `Branch: ${summary.branch}  |  Language: ${summary.language}  |  Generated: ${new Date(summary.completedAt).toLocaleString()}`,
      margin + 4,
      y + 13
    );

    // 3 Metric KPI Cards
    y += 24;
    const cardWidth = (contentWidth - 8) / 3;

    // Maintainability Score
    doc.setFillColor(240, 253, 250); // teal-50
    doc.setDrawColor(204, 251, 241); // teal-100
    doc.roundedRect(margin, y, cardWidth, 20, 2, 2, "FD");
    doc.setFontSize(8);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(15, 118, 110); // teal-700
    doc.text("MAINTAINABILITY SCORE", margin + 4, y + 5.5);
    doc.setFontSize(15);
    doc.text(`${summary.maintainabilityScore}/100`, margin + 4, y + 15);

    // Technical Debt
    doc.setFillColor(254, 243, 199); // amber-50
    doc.setDrawColor(253, 230, 138); // amber-100
    doc.roundedRect(margin + cardWidth + 4, y, cardWidth, 20, 2, 2, "FD");
    doc.setFontSize(8);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(180, 83, 9); // amber-700
    doc.text("ESTIMATED TECH DEBT", margin + cardWidth + 8, y + 5.5);
    doc.setFontSize(15);
    doc.text(`${summary.technicalDebtHours} hours`, margin + cardWidth + 8, y + 15);

    // Total Findings
    doc.setFillColor(255, 241, 242); // rose-50
    doc.setDrawColor(254, 205, 211); // rose-100
    doc.roundedRect(margin + (cardWidth + 4) * 2, y, cardWidth, 20, 2, 2, "FD");
    doc.setFontSize(8);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(190, 18, 60); // rose-700
    doc.text("TOTAL AST FINDINGS", margin + (cardWidth + 4) * 2 + 4, y + 5.5);
    doc.setFontSize(15);
    doc.text(`${summary.findingsCount}`, margin + (cardWidth + 4) * 2 + 4, y + 15);

    // Issue Breakdown Section
    y += 26;
    doc.setTextColor(15, 23, 42);
    doc.setFontSize(10.5);
    doc.setFont("helvetica", "bold");
    doc.text("Findings Breakdown by Category", margin, y);

    y += 4;
    const categories = Object.entries(summary.findingsByCategory);
    const catWidth = contentWidth / categories.length;
    doc.setFillColor(241, 245, 249);
    doc.rect(margin, y, contentWidth, 10, "F");
    categories.forEach(([cat, count], idx) => {
      doc.setFontSize(8);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(71, 85, 105);
      doc.text(`${cat}: `, margin + idx * catWidth + 3, y + 6.5);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(15, 23, 42);
      doc.text(`${count}`, margin + idx * catWidth + 3 + doc.getTextWidth(`${cat}: `), y + 6.5);
    });

    // Detailed Findings Table
    y += 16;
    doc.setTextColor(15, 23, 42);
    doc.setFontSize(10.5);
    doc.setFont("helvetica", "bold");
    doc.text("Identified Issues & Recommendations", margin, y);

    y += 4;

    const renderTableHeader = (currentY: number) => {
      doc.setFillColor(30, 41, 59);
      doc.rect(margin, currentY, contentWidth, 7, "F");
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(7.5);
      doc.setFont("helvetica", "bold");
      doc.text("Severity", margin + 2, currentY + 4.8);
      doc.text("Category", margin + 20, currentY + 4.8);
      doc.text("Location", margin + 48, currentY + 4.8);
      doc.text("Issue Title & Remediation", margin + 92, currentY + 4.8);
    };

    renderTableHeader(y);
    y += 7;

    // Table Rows with automatic pagination
    summary.findings.forEach((f, idx) => {
      if (y > pageHeight - 25) {
        doc.addPage();
        y = 16;
        renderTableHeader(y);
        y += 7;
      }

      const isAlt = idx % 2 === 1;
      if (isAlt) {
        doc.setFillColor(248, 250, 252);
        doc.rect(margin, y, contentWidth, 12, "F");
      }

      const sev = f.severity.toUpperCase();
      if (sev === "HIGH" || sev === "CRITICAL") {
        doc.setTextColor(190, 18, 60);
      } else if (sev === "MEDIUM") {
        doc.setTextColor(180, 83, 9);
      } else {
        doc.setTextColor(15, 118, 110);
      }
      doc.setFontSize(7.5);
      doc.setFont("helvetica", "bold");
      doc.text(sev, margin + 2, y + 4.8);

      doc.setTextColor(71, 85, 105);
      doc.setFont("helvetica", "normal");
      doc.text(f.category.slice(0, 14), margin + 20, y + 4.8);

      doc.setFontSize(7);
      doc.setTextColor(100, 116, 139);
      const loc = `${f.filePath.split("/").slice(-2).join("/")}:${f.lineNumber ?? 1}`;
      doc.text(loc.slice(0, 24), margin + 48, y + 4.8);

      doc.setFontSize(7.5);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(15, 23, 42);
      doc.text(f.title.slice(0, 52), margin + 92, y + 4.2);

      if (f.suggestion) {
        doc.setFontSize(6.5);
        doc.setFont("helvetica", "italic");
        doc.setTextColor(100, 116, 139);
        doc.text(f.suggestion.slice(0, 70), margin + 92, y + 8.5);
      }

      y += 12;
    });

    // Page Footers
    const totalPages = doc.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setFontSize(7.5);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(148, 163, 184);
      doc.text(
        `Page ${i} of ${totalPages}  |  CodeSense AI Code Intelligence Report`,
        margin,
        pageHeight - 8
      );
      doc.text(
        "CONFIDENTIAL - FOR INTERNAL ENGINEERING USE ONLY",
        pageWidth - margin - 80,
        pageHeight - 8
      );
    }

    const filename = `codesense-${type}-${summary.repository.replace(/[^a-zA-Z0-9_-]/g, "_")}.pdf`;
    doc.save(filename);
  },

  printReport(summary: ReportSummary, type: "quality" | "debt"): void {
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      window.print();
      return;
    }

    const title =
      type === "debt"
        ? "CodeSense AI - Technical Debt Analysis & Remediation Plan"
        : "CodeSense AI - Quality & Security Assessment Report";

    const contentHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${title}</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #1e293b; padding: 40px; }
            h1 { font-size: 24px; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }
            h2 { font-size: 18px; color: #334155; margin-top: 24px; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
            .score { font-size: 32px; font-weight: bold; color: #0f766e; }
            .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 20px 0; }
            .card { background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 6px; }
            table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }
            th, td { border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }
            th { background: #f1f5f9; }
            .critical { color: #be123c; font-weight: bold; }
            .high { color: #e11d48; }
            .medium { color: #d97706; }
            .low { color: #0f766e; }
            @media print {
              body { padding: 0; }
              button { display: none; }
            }
          </style>
        </head>
        <body>
          <h1>${title}</h1>
          <p><strong>Repository:</strong> ${summary.repository} | <strong>Branch:</strong> ${summary.branch} | <strong>Language:</strong> ${summary.language}</p>
          <p><strong>Generated:</strong> ${new Date(summary.completedAt).toLocaleString()}</p>

          <div class="grid">
            <div class="card">
              <div>Maintainability Score</div>
              <div class="score">${summary.maintainabilityScore}/100</div>
            </div>
            <div class="card">
              <div>Estimated Technical Debt</div>
              <div class="score" style="color: #d97706">${summary.technicalDebtHours} hours</div>
            </div>
            <div class="card">
              <div>Total Findings</div>
              <div class="score" style="color: #be123c">${summary.findingsCount}</div>
            </div>
          </div>

          <h2>Findings Summary by Category</h2>
          <table>
            <thead>
              <tr><th>Category</th><th>Count</th></tr>
            </thead>
            <tbody>
              ${Object.entries(summary.findingsByCategory)
                .map(([cat, count]) => `<tr><td>${cat}</td><td>${count}</td></tr>`)
                .join("")}
            </tbody>
          </table>

          <h2>Identified Code & Security Issues</h2>
          <table>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Category</th>
                <th>File Location</th>
                <th>Issue Description</th>
                <th>Remediation Suggestion</th>
              </tr>
            </thead>
            <tbody>
              ${summary.findings
                .map(
                  (f) => `
                <tr>
                  <td class="${f.severity.toLowerCase()}">${f.severity}</td>
                  <td>${f.category}</td>
                  <td>${f.filePath}:${f.lineNumber ?? 1}</td>
                  <td><strong>${f.title}</strong></td>
                  <td>${f.suggestion || "N/A"}</td>
                </tr>`
                )
                .join("")}
            </tbody>
          </table>

          <div style="margin-top: 40px; text-align: center;">
            <button onclick="window.print()" style="padding: 10px 20px; font-size: 14px; background: #0f172a; color: white; border: none; border-radius: 4px; cursor: pointer;">
              Print to PDF
            </button>
          </div>
        </body>
      </html>
    `;

    printWindow.document.open();
    printWindow.document.write(contentHtml);
    printWindow.document.close();
  },
};
