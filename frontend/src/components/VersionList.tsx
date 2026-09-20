import { useTranslation } from "react-i18next";
import type { VersionMeta } from "../lib/api";

type Props = {
  versions: VersionMeta[];
  onRestore: (id: number) => void;
};

export function VersionList({ versions, onRestore }: Props) {
  const { t } = useTranslation();

  return (
    <section className="versions-block">
      <h2>{t("versions.title")}</h2>
      <ul className="version-list">
        {versions.map((v) => (
          <li key={v.id}>
            <button type="button" className="link-btn" onClick={() => onRestore(v.id)}>
              {v.label || v.command_id || t("versions.original")}
            </button>
            <span className="muted small">{v.created_at}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
