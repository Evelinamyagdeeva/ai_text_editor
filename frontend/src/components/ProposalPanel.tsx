import { useTranslation } from "react-i18next";
import type { DiffChunk, EditProposal } from "../lib/api";

type Props = {
  proposal: EditProposal | null;
  loading: boolean;
  onAccept: () => void;
  onReject: () => void;
};

function MetricsRow({
  label,
  before,
  after,
}: {
  label: string;
  before: number;
  after: number;
}) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <span>
        {before} → <strong>{after}</strong>
      </span>
    </div>
  );
}

function DiffView({ chunks }: { chunks: DiffChunk[] }) {
  return (
    <div className="diff-view">
      {chunks.map((c, i) => (
        <span key={i} className={`diff-${c.kind}`}>
          {c.text}
        </span>
      ))}
    </div>
  );
}

export function ProposalPanel({ proposal, loading, onAccept, onReject }: Props) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <aside className="side-panel">
        <h2>{t("preview.title")}</h2>
        <p className="muted">…</p>
      </aside>
    );
  }

  if (!proposal) {
    return (
      <aside className="side-panel muted">
        <h2>{t("preview.title")}</h2>
        <p>{t("commands.run")}</p>
      </aside>
    );
  }

  const passed = proposal.critic?.pass !== false;

  return (
    <aside className="side-panel">
      <h2>{t("preview.title")}</h2>
      <div className="panel-actions">
        <button type="button" className="btn primary" onClick={onAccept}>
          {t("preview.accept")}
        </button>
        <button type="button" className="btn primary" onClick={onAccept}>
          {t("preview.acceptAll")}
        </button>
        <button type="button" className="btn" onClick={onReject}>
          {t("preview.reject")}
        </button>
        <button type="button" className="btn" onClick={onReject}>
          {t("preview.rejectAll")}
        </button>
      </div>

      <h3>{t("preview.diff")}</h3>
      <DiffView chunks={proposal.diff} />

      <h3>{t("preview.metrics")}</h3>
      <MetricsRow
        label={t("preview.clarity")}
        before={proposal.metrics_before.clarity}
        after={proposal.metrics_after.clarity}
      />
      <MetricsRow
        label={t("preview.readability")}
        before={proposal.metrics_before.readability}
        after={proposal.metrics_after.readability}
      />
      <MetricsRow
        label={t("preview.formality")}
        before={proposal.metrics_before.formality}
        after={proposal.metrics_after.formality}
      />

      <h3>{t("preview.critic")}</h3>
      {passed ? (
        <p className="ok">{t("preview.passed")}</p>
      ) : (
        <ul>
          {(proposal.critic.issues ?? []).map((issue, i) => (
            <li key={i}>{issue}</li>
          ))}
        </ul>
      )}

      {proposal.fact_claims?.length > 0 && (
        <>
          <h3>{t("preview.facts")}</h3>
          <p className="muted small">{t("preview.factNote")}</p>
          <ul>
            {proposal.fact_claims.map((c, i) => (
              <li key={i}>
                <em>{c.quote}</em> — {c.reason}
              </li>
            ))}
          </ul>
        </>
      )}
    </aside>
  );
}
