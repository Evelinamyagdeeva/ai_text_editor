import { useTranslation } from "react-i18next";

type Props = {
  onUpload: (file: File) => void;
  onStartWriting: () => void;
};

export function EmptyEditorState({ onUpload, onStartWriting }: Props) {
  const { t } = useTranslation();

  return (
    <div className="empty-drop overlay" onClick={onStartWriting}>
      <div className="empty-card" onClick={(e) => e.stopPropagation()}>
        <div className="empty-icon">📄</div>
        <h2>{t("editor.dropTitle")}</h2>
        <p className="muted">{t("editor.dropHint")}</p>
        <label className="btn primary" onClick={(e) => e.stopPropagation()}>
          {t("editor.upload")}
          <input
            type="file"
            accept=".txt,.md,.markdown,.docx,.pdf"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
              e.target.value = "";
            }}
          />
        </label>
      </div>
    </div>
  );
}
