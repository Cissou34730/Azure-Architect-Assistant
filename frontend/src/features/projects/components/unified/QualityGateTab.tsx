import { useEffect, useState } from "react";
import { qualityGateApi } from "../../api/qualityGateService";
import type {
  QualityGateClarificationItem,
  QualityGateMindMapTopic,
  QualityGateMissingArtifact,
  QualityGatePillarSummary,
  QualityGateReport,
  QualityGateTraceEventType,
} from "../../types/quality-gate";

interface QualityGateTabProps {
  readonly projectId: string;
  readonly lastUpdated: string;
}

function formatStatus(status: string): string {
  if (status === "not-addressed") {
    return "Not addressed";
  }
  if (status === "in_progress") {
    return "In progress";
  }
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function SummaryCard({
  label,
  value,
  detail,
}: {
  readonly label: string;
  readonly value: string;
  readonly detail: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-dim">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
      <p className="mt-1 text-sm text-secondary">{detail}</p>
    </div>
  );
}

function WafPillarRow({ pillar }: { readonly pillar: QualityGatePillarSummary }) {
  return (
    <li className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">{pillar.pillar}</p>
          <p className="text-xs text-secondary">
            {pillar.coveredItems} covered · {pillar.partialItems} partial ·{" "}
            {pillar.notCoveredItems} not covered
          </p>
        </div>
        <p className="text-sm font-semibold text-foreground">{pillar.coveragePercentage}%</p>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-border">
        <div
          className="h-full rounded-full bg-brand"
          style={{ width: `${pillar.coveragePercentage}%` }}
        />
      </div>
    </li>
  );
}

function MindMapTopicRow({ topic }: { readonly topic: QualityGateMindMapTopic }) {
  return (
    <li className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-foreground">{topic.label}</p>
        <span className="rounded-full border border-border px-2 py-1 text-xs text-secondary">
          {formatStatus(topic.status)}
        </span>
      </div>
      <p className="mt-2 text-xs text-secondary">
        Confidence {Math.round(topic.confidence * 100)}%
      </p>
    </li>
  );
}

function ClarificationRow({
  clarification,
}: {
  readonly clarification: QualityGateClarificationItem;
}) {
  return (
    <li className="rounded-lg border border-border bg-surface p-3">
      <p className="text-sm font-medium text-foreground">{clarification.question}</p>
      <p className="mt-1 text-xs text-secondary">
        {formatStatus(clarification.status)}
        {clarification.priority !== undefined && clarification.priority !== null
          ? ` · Priority ${clarification.priority}`
          : ""}
      </p>
    </li>
  );
}

function MissingArtifactRow({
  artifact,
}: {
  readonly artifact: QualityGateMissingArtifact;
}) {
  return (
    <li className="rounded-lg border border-border bg-surface p-3">
      <p className="text-sm font-semibold text-foreground">{artifact.label}</p>
      <p className="mt-1 text-xs text-secondary">{artifact.reason}</p>
    </li>
  );
}

function TraceEventTypeRow({
  eventType,
}: {
  readonly eventType: QualityGateTraceEventType;
}) {
  return (
    <li className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-foreground">{eventType.eventType}</p>
        <p className="text-xs text-secondary">{eventType.count} events</p>
      </div>
    </li>
  );
}

export function QualityGateTab({ projectId, lastUpdated }: QualityGateTabProps) {
  const [report, setReport] = useState<QualityGateReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadReport = async () => {
      setLoading(true);
      try {
        const nextReport = await qualityGateApi.get(projectId);
        if (active) {
          setReport(nextReport);
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(
            loadError instanceof Error ? loadError.message : "Failed to load quality gate.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadReport();
    return () => {
      active = false;
    };
  }, [lastUpdated, projectId]);

  if (loading && report === null) {
    return <div className="p-6 text-sm text-secondary">Loading quality gate…</div>;
  }

  if (error !== null && report === null) {
    return <div className="p-6 text-sm text-danger">{error}</div>;
  }

  if (report === null) {
    return <div className="p-6 text-sm text-secondary">No quality gate data available.</div>;
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="rounded-xl border border-border bg-card p-4">
        <h2 className="text-lg font-semibold text-foreground">Quality gate report</h2>
        <p className="mt-1 text-sm text-secondary">
          Actionable coverage and delivery gaps for the current project state.
        </p>
        <p className="mt-2 text-xs text-dim">Generated {report.generatedAt}</p>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <SummaryCard
          label="WAF"
          value={`${report.waf.coveragePercentage}%`}
          detail={`${report.waf.coveredItems}/${report.waf.totalItems} covered`}
        />
        <SummaryCard
          label="Mindmap"
          value={`${report.mindMap.coveragePercentage}%`}
          detail={`${report.mindMap.addressedTopics}/${report.mindMap.totalTopics} addressed`}
        />
        <SummaryCard
          label="Open clarifications"
          value={String(report.openClarifications.count)}
          detail="Unanswered questions still blocking sign-off"
        />
        <SummaryCard
          label="Missing artifacts"
          value={String(report.missingArtifacts.count)}
          detail="Tracked deliverables still missing from the workspace"
        />
        <SummaryCard
          label="Trace events"
          value={String(report.trace.totalEvents)}
          detail={
            report.trace.lastEventAt === null
              ? "No persisted workflow activity yet"
              : `Last activity ${report.trace.lastEventAt}`
          }
        />
      </div>

      <section
        aria-label="WAF Coverage"
        className="rounded-xl border border-border bg-card p-4"
      >
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-foreground">WAF Coverage</h3>
          <p className="text-sm text-secondary">
            {report.waf.coveragePercentage}% weighted coverage across {report.waf.totalItems}{" "}
            checklist items.
          </p>
        </div>
        <ul className="mt-4 space-y-3">
          {report.waf.pillars.map((pillar) => (
            <WafPillarRow key={pillar.pillar} pillar={pillar} />
          ))}
        </ul>
      </section>

      <section
        aria-label="Mindmap Coverage"
        className="rounded-xl border border-border bg-card p-4"
      >
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-foreground">Mindmap Coverage</h3>
          <p className="text-sm text-secondary">
            {report.mindMap.addressedTopics} addressed · {report.mindMap.partialTopics} partial ·{" "}
            {report.mindMap.notAddressedTopics} not addressed
          </p>
        </div>
        <ul className="mt-4 grid gap-3 md:grid-cols-2">
          {report.mindMap.topics.map((topic) => (
            <MindMapTopicRow key={topic.key} topic={topic} />
          ))}
        </ul>
      </section>

      <section
        aria-label="Open Clarifications"
        className="rounded-xl border border-border bg-card p-4"
      >
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-foreground">Open Clarifications</h3>
          <p className="text-sm text-secondary">
            Questions the architect still needs to answer before the quality gate closes.
          </p>
        </div>
        {report.openClarifications.items.length === 0 ? (
          <p className="mt-4 text-sm text-secondary">All clarification questions are answered.</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {report.openClarifications.items.map((clarification) => (
              <ClarificationRow key={clarification.id} clarification={clarification} />
            ))}
          </ul>
        )}
      </section>

      <section
        aria-label="Missing Artifacts"
        className="rounded-xl border border-border bg-card p-4"
      >
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-foreground">Missing Artifacts</h3>
          <p className="text-sm text-secondary">
            Deliverables or validation steps that still need to run for this project.
          </p>
        </div>
        {report.missingArtifacts.items.length === 0 ? (
          <p className="mt-4 text-sm text-secondary">
            All tracked deliverables are already present.
          </p>
        ) : (
          <ul className="mt-4 space-y-3">
            {report.missingArtifacts.items.map((artifact) => (
              <MissingArtifactRow key={artifact.key} artifact={artifact} />
            ))}
          </ul>
        )}
      </section>

      <section
        aria-label="Recent Trace Activity"
        className="rounded-xl border border-border bg-card p-4"
      >
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-foreground">Recent Trace Activity</h3>
          <p className="text-sm text-secondary">
            {report.trace.totalEvents === 0
              ? "No persisted workflow trace events are available yet."
              : `${report.trace.totalEvents} persisted workflow events recorded for this project.`}
          </p>
          {report.trace.lastEventAt !== null ? (
            <p className="text-xs text-dim">Last event {report.trace.lastEventAt}</p>
          ) : null}
        </div>
        {report.trace.eventTypes.length === 0 ? (
          <p className="mt-4 text-sm text-secondary">Trace activity will appear after workflow events are persisted.</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {report.trace.eventTypes.map((eventType) => (
              <TraceEventTypeRow key={eventType.eventType} eventType={eventType} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
