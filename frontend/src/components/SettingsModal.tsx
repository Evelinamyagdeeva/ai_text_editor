import { useTranslation } from "react-i18next";
import type { AppSettings } from "../lib/api";

type Props = {
  open: boolean;
  settings: AppSettings | null;
  onClose: () => void;
  onSave: (patch: Partial<AppSettings>) => void;
};

export function SettingsModal({ open, settings, onClose, onSave }: Props) {
  const { t, i18n } = useTranslation();

  if (!open || !settings) return null;

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="modal" role="dialog" onClick={(e) => e.stopPropagation()}>
        <h2>{t("settingsPanel.title")}</h2>
        <label>
          {t("settingsPanel.polzaUrl")}
          <input
            id="polza-url"
            defaultValue={settings.ollama_base_url}
            onBlur={(e) => onSave({ ollama_base_url: e.target.value })}
          />
        </label>
        <label>
          {t("settingsPanel.model")}
          <input
            id="ollama-model"
            defaultValue={settings.ollama_model}
            onBlur={(e) => onSave({ ollama_model: e.target.value })}
          />
        </label>
        <label>
          {t("settingsPanel.language")}
          <select
            defaultValue={settings.ui_locale}
            onChange={(e) => {
              const lng = e.target.value;
              void i18n.changeLanguage(lng);
              onSave({ ui_locale: lng });
            }}
          >
            <option value="ru">Русский</option>
            <option value="en">English</option>
          </select>
        </label>
        <button type="button" className="btn" onClick={onClose}>
          {t("settingsPanel.close")}
        </button>
      </div>
    </div>
  );
}
