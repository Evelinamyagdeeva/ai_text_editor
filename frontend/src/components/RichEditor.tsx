import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { useTranslation } from "react-i18next";
import { selectionToPlainRange } from "../lib/selectionPlainRange";

export type SelectionInfo = {
  text: string;
  start: number;
  end: number;
  from: number;
  to: number;
  top: number;
  left: number;
};

export type RichEditorHandle = {
  focus: () => void;
  insertText: (text: string) => void;
};

type Props = {
  content: string;
  onChange: (html: string) => void;
  onSelection: (sel: SelectionInfo | null) => void;
};

export const RichEditor = forwardRef<RichEditorHandle, Props>(function RichEditor(
  { content, onChange, onSelection },
  ref,
) {
  const { t } = useTranslation();
  const localHtml = useRef(content);

  const editor = useEditor({
    extensions: [StarterKit, Placeholder.configure({ placeholder: t("editor.placeholder") })],
    content,
    autofocus: "end",
    onUpdate: ({ editor: ed }) => {
      const html = ed.getHTML();
      localHtml.current = html;
      onChange(html);
    },
    onSelectionUpdate: ({ editor: ed }) => {
      const { from, to } = ed.state.selection;
      if (from === to) {
        onSelection(null);
        return;
      }
      const range = selectionToPlainRange(ed.state.doc, from, to);
      if (!range) {
        onSelection(null);
        return;
      }
      const coords = ed.view.coordsAtPos(from);
      const shell = ed.view.dom.getBoundingClientRect();
      onSelection({
        text: range.text,
        start: range.start,
        end: range.end,
        from,
        to,
        top: coords.top - shell.top - 40,
        left: Math.max(8, coords.left - shell.left),
      });
    },
  });

  useImperativeHandle(ref, () => ({
    focus: () => editor?.chain().focus().run(),
    insertText: (text: string) => {
      editor?.chain().focus().insertContent(text.replace(/\n/g, "<br>")).run();
    },
  }));

  useEffect(() => {
    if (!editor) return;
    if (content === localHtml.current) return;
    if (content === editor.getHTML()) {
      localHtml.current = content;
      return;
    }
    editor.commands.setContent(content, false);
    localHtml.current = content;
  }, [content, editor]);

  return (
    <div className="editor-shell">
      <EditorContent editor={editor} className="tiptap-editor" />
    </div>
  );
});
