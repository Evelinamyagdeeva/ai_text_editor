import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { CommandPreset } from "../../lib/api";

type Props = {
  commands: CommandPreset[];
  loading?: boolean;
  onTool: (cmd: CommandPreset) => void;
  onCustom: () => void;
};

const GROUPS = ["edit", "analyze", "create"] as const;
type GroupId = (typeof GROUPS)[number];

export function AIToolsPanel({ commands, loading, onTool, onCustom }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<Partial<Record<GroupId, boolean>>>({});

  const toggle = (g: GroupId) => {
    setOpen((prev) => ({ ...prev, [g]: !prev[g] }));
  };

  return (
    <aside className="tools-panel">
      <h2>{t("tools.title")}</h2>
      {GROUPS.map((g) => {
        const expanded = Boolean(open[g]);
        const items = commands.filter((c) => c.category === g && c.id !== "custom");
        return (
          <section key={g} className="tool-group">
            <button
              type="button"
              className={expanded ? "tool-group-trigger open" : "tool-group-trigger"}
              aria-expanded={expanded}
              onClick={() => toggle(g)}
            >
              <span>{t(`tools.${g}`)}</span>
              <span className="tool-group-chevron" aria-hidden>{expanded ? "▾" : "▸"}</span>
            </button>
            {expanded && (
              <div className="tool-list">
                {items.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    className="tool-btn"
                    disabled={loading}
                    onClick={() => onTool(c)}
                  >
                    {t(c.i18nKey)}
                  </button>
                ))}
              </div>
            )}
          </section>
        );
      })}
      <button type="button" className="custom-request" disabled={loading} onClick={onCustom}>
        ✨ {t("tools.custom")}
      </button>
    </aside>
  );
}
