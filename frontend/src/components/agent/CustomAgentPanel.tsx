import { useState } from "react";
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
  if (!open) return null;

  return (
    <div className="agent-drawer">
      <header className="agent-head">
        <h2>✨ {t("agent.title")}</h2>
        <button type="button" className="icon-btn" onClick={onClose}>
          ×
        </button>
      </header>
      <div className="agent-body">
        {messages.length === 0 && <p className="bubble ai">{t("agent.greeting")}</p>}
        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "bubble user" : "bubble ai"}>
            <strong>{m.role === "user" ? "User" : "AI"}</strong>
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
        {loading && <p className="muted">…</p>}
      </div>
      <form
        className="agent-input"
        onSubmit={(e) => {
          e.preventDefault();
          if (!draft.trim()) return;
          onSend(draft.trim());
          setDraft("");
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={t("agent.placeholder")}
        />
        <button type="submit" className="btn primary" disabled={loading}>
          ➤
        </button>
      </form>
    </div>
  );
}
