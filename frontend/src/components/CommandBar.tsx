import { useTranslation } from "react-i18next";
import type { CommandPreset } from "../lib/api";

type Props = {
  commands: CommandPreset[];
  selectedId: string;
  onSelect: (id: string) => void;
  extra: string;
  onExtraChange: (v: string) => void;
  selectionLen: number;
  onRun: () => void;
  disabled: boolean;
};

export function CommandBar({
  commands,
  selectedId,
  onSelect,
  extra,
  onExtraChange,
  selectionLen,
  onRun,
  disabled,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="command-bar">
      <div className="command-row">
        <span className="label">{t("commands.label")}</span>
        <div className="chips">
          {commands.map((c) => (
            <button
              key={c.id}
              type="button"
              className={selectedId === c.id ? "chip active" : "chip"}
              onClick={() => onSelect(c.id)}
            >
              {t(c.i18nKey)}
            </button>
          ))}
        </div>
      </div>
      <textarea
        className="extra-input"
        placeholder={t("commands.extra")}
        value={extra}
        onChange={(e) => onExtraChange(e.target.value)}
        rows={2}
      />
      <div className="command-footer">
        <span className="muted small">
          {t("commands.selectionHint", { count: selectionLen })}
        </span>
        <button type="button" className="btn primary" disabled={disabled} onClick={onRun}>
          {t("commands.run")}
        </button>
      </div>
    </div>
  );
}
