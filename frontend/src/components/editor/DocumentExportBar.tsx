import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { ExportFormat } from "../../lib/api";

const FORMATS: ExportFormat[] = ["txt", "md", "html", "docx", "pdf"];

type Props = {
  disabled?: boolean;
  onExport: (format: ExportFormat) => void;
};

export function DocumentExportBar({ disabled, onExport }: Props) {
  const { t } = useTranslation();
  const [format, setFormat] = useState<ExportFormat>("docx");

  return (
    <div className="export-bar">
      <label className="export-label">
        <span className="muted small">{t("editor.exportAs")}</span>
        <select
          className="export-select"
          value={format}
          disabled={disabled}
          onChange={(e) => setFormat(e.target.value as ExportFormat)}
        >
          {FORMATS.map((f) => (
            <option key={f} value={f}>
              {t(`editor.format.${f}`)}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="btn primary compact"
        disabled={disabled}
        onClick={() => onExport(format)}
      >
        {t("editor.download")}
      </button>
    </div>
  );
}
