/**
 * .xlsx export helpers built on SheetJS.
 *
 * Why SheetJS: produces real Excel files (not CSV pretending to be Excel),
 * keeps numbers numeric in the cells, and works in the browser without any
 * server roundtrip.
 */

import * as XLSX from "xlsx";

export interface ExportColumn<T> {
  /** Header text in the first row of the sheet. */
  header: string;
  /** Pull the value from the row. Return undefined / null for blank cells. */
  value: (row: T) => string | number | boolean | Date | null | undefined;
  /** Optional column width in characters; defaults to 16. */
  width?: number;
}

export interface ExportOptions<T> {
  filename: string;
  sheetName?: string;
  columns: ExportColumn<T>[];
  rows: T[];
}

export function exportToXlsx<T>(opts: ExportOptions<T>): void {
  const headerRow = opts.columns.map((c) => c.header);
  const dataRows = opts.rows.map((row) =>
    opts.columns.map((c) => {
      const v = c.value(row);
      return v === undefined ? null : v;
    })
  );
  const aoa = [headerRow, ...dataRows];

  const ws = XLSX.utils.aoa_to_sheet(aoa);

  // Column widths
  ws["!cols"] = opts.columns.map((c) => ({ wch: c.width ?? 16 }));

  // Freeze the header row + bold
  ws["!freeze"] = { ySplit: 1 };
  for (let col = 0; col < opts.columns.length; col++) {
    const ref = XLSX.utils.encode_cell({ r: 0, c: col });
    if (ws[ref]) {
      ws[ref].s = { font: { bold: true } };
    }
  }

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, opts.sheetName || "Sheet1");
  XLSX.writeFile(wb, opts.filename);
}

export function timestampedFilename(prefix: string): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const stamp = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
  return `${prefix}-${stamp}.xlsx`;
}
