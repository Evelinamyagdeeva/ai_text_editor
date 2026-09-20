import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { EmptyEditorState } from "./EmptyEditorState";
import { RichEditor, type RichEditorHandle, type SelectionInfo } from "../RichEditor";
import { SelectionAIToolbar } from "./SelectionAIToolbar";
import { VersionList } from "../VersionList";
import { DocumentExportBar } from "./DocumentExportBar";
import type { CommandPreset, ExportFormat, VersionMeta } from "../../lib/api";
import { isEmptyHtml } from "../../lib/api";

type Props = {
  content: string;
  onChange: (html: string) => void;
  selection: SelectionInfo | null;
  onSelection: (s: SelectionInfo | null) => void;
  commands: CommandPreset[];
  onTool: (id: string) => void;
  onCustom: () => void;
  onUpload: (file: File) => void;
  versions: VersionMeta[];
  onRestore: (id: number) => void;
  applyWhole: boolean;
  onApplyWhole: (v: boolean) => void;
  showEmpty: boolean;
  canExport?: boolean;
  onExport?: (format: ExportFormat) => void;
};

export function EditorWorkspace({
  content,
  onChange,
  selection,
  onSelection,
  commands,
  onTool,
  onCustom,
  onUpload,
  versions,
  onRestore,
  applyWhole,
  onApplyWhole,
  showEmpty,
  canExport,
  onExport,
}: Props) {
  const { t } = useTranslation();
  const editorRef = useRef<RichEditorHandle>(null);
  const empty = showEmpty && isEmptyHtml(content);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      onUpload(file);
      return;
    }
    const text = e.dataTransfer.getData("text/plain");
    if (text) editorRef.current?.insertText(text);
  };

  return (
    <section className="editor-column">
      <div className="editor-subheader">
        <label className="toggle">
          <input type="checkbox" checked={applyWhole} onChange={(e) => onApplyWhole(e.target.checked)} />
          {t("tools.applyWhole")}
        </label>
        {onExport && (
          <DocumentExportBar disabled={!canExport} onExport={onExport} />
        )}
      </div>
      <div className="editor-stage" onDragOver={(e) => e.preventDefault()} onDrop={handleDrop}>
        <div className="editor-relative">
          <RichEditor
            ref={editorRef}
            content={content}
            onChange={onChange}
            onSelection={onSelection}
          />
          <SelectionAIToolbar
            selection={selection}
            commands={commands}
            onCommand={onTool}
            onCustom={onCustom}
          />
          {empty && (
            <EmptyEditorState
              onUpload={onUpload}
              onStartWriting={() => editorRef.current?.focus()}
            />
          )}
        </div>
      </div>
      <VersionList versions={versions} onRestore={onRestore} />
    </section>
  );
}
