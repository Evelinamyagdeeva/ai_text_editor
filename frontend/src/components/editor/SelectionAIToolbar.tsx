import { useTranslation } from "react-i18next";
import type { CommandPreset } from "../../lib/api";
import type { SelectionInfo } from "../RichEditor";

type Props = {
  selection: SelectionInfo | null;
  commands: CommandPreset[];
  onCommand: (id: string) => void;
  onCustom: () => void;
};

const QUICK = ["improve", "rephrase", "shorten", "simplify", "translate"];

export function SelectionAIToolbar({ selection, commands, onCommand, onCustom }: Props) {
  const { t } = useTranslation();
  if (!selection) return null;
  const items = commands.filter((c) => QUICK.includes(c.id));

  return (
    <div className="selection-toolbar" style={{ top: selection.top, left: selection.left }}>
      <span className="selection-ai">AI</span>
      {items.map((c) => (
        <button key={c.id} type="button" className="chip" onClick={() => onCommand(c.id)}>
          {t(c.i18nKey)}
        </button>
      ))}
      <button type="button" className="chip active" onClick={onCustom}>
        {t("commands.custom")}
      </button>
    </div>
  );
}
