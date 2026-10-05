import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ChatMessage } from "../../lib/api";

type Props = {
  open: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  loading: boolean;
  awaitingConfirm: boolean;
  onSend: (text: string) => void;
  onConfirm: () => void;
  onRevise: () => void;
};

export function CustomAgentPanel({
  open,
  onClose,
  messages,
  loading,
  awaitingConfirm,
  onSend,
  onConfirm,
  onRevise,
}: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => textareaRef.current?.focus(), 50);
    return () => window.clearTimeout(id);
  }, [open]);

  if (!open) return null;

  const submit = () => {
    const text = draft.trim();
    if (!text || loading) return;
    onSend(text);
    setDraft("");
  };

  return (
    <div className="agent-drawer">
      <header className="agent-head">
        <h2>✨ {t("agent.title")}</h2>
        <button type="button" className="icon-btn" onClick={onClose} aria-label={t("settingsPanel.close")}>
          ×
        </button>
      </header>
      <p className="agent-hint">{t("agent.customHint")}</p>
      <div className="agent-body">
        {messages.length === 0 && <p className="bubble ai">{t("agent.greeting")}</p>}
        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "bubble user" : "bubble ai"}>
            <strong>{m.role === "user" ? t("agent.userLabel") : t("agent.aiLabel")}</strong>
            <p>{m.content}</p>
          </div>
        ))}
        {awaitingConfirm && (
          <div className="confirm-row">
            <button type="button" className="btn primary" onClick={onConfirm} disabled={loading}>
              {t("agent.confirm")}
            </button>
            <button type="button" className="btn" onClick={onRevise}>
              {t("agent.revise")}
            </button>
          </div>
        )}
        {loading && <p className="muted">{t("tools.working")}</p>}
      </div>
      <form
        className="agent-input"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <div className="agent-input-row">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={t("agent.placeholder")}
            rows={3}
            disabled={loading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <button type="submit" className="btn primary" disabled={loading || !draft.trim()}>
            ➤
          </button>
        </div>
      </form>
    </div>
  );
}
