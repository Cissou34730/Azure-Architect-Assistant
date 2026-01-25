import { Card, CardHeader, CardTitle, CardContent, Badge } from "../../../../components/common";
import { Shield, Zap, DollarSign, Settings, Gauge } from "lucide-react";

interface Finding {
  readonly id?: string;
  readonly title?: string;
  readonly severity?: string;
  readonly wafPillar?: string;
}

interface WafAssessmentCardProps {
  findings: readonly Finding[];
}

const PILLARS = [
  { key: "reliability", label: "Reliability", icon: Shield, color: "text-blue-600" },
  { key: "security", label: "Security", icon: Shield, color: "text-red-600" },
  { key: "cost", label: "Cost", icon: DollarSign, color: "text-green-600" },
  { key: "operationalexcellence", label: "Operations", icon: Settings, color: "text-purple-600" },
  { key: "performanceefficiency", label: "Performance", icon: Zap, color: "text-amber-600" },
];

export function WafAssessmentCard({ findings }: WafAssessmentCardProps) {
  const findingsByPillar: Record<string, Finding[]> = {};
  const severityCounts: Record<string, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  };

  for (const finding of findings) {
    const pillar = (finding.wafPillar || "").toLowerCase().replace(/[^a-z]/g, "");
    if (!findingsByPillar[pillar]) {
      findingsByPillar[pillar] = [];
    }
    findingsByPillar[pillar].push(finding);

    const severity = (finding.severity || "medium").toLowerCase();
    severityCounts[severity] = (severityCounts[severity] || 0) + 1;
  }

  const totalFindings = findings.length;
  const criticalOrHigh = severityCounts.critical + severityCounts.high;

  return (
    <Card>
      <CardHeader>
        <CardTitle>WAF Assessment</CardTitle>
      </CardHeader>
      <CardContent>
        {totalFindings === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <Gauge className="h-12 w-12 mx-auto mb-2 text-gray-300" />
            <p>No findings yet</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-900">{totalFindings}</div>
                <div className="text-xs text-gray-600">Total Findings</div>
              </div>
              {criticalOrHigh > 0 && (
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-600">{criticalOrHigh}</div>
                  <div className="text-xs text-gray-600">Critical/High</div>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-gray-200 space-y-3">
              {PILLARS.map((pillar) => {
                const pillarFindings = findingsByPillar[pillar.key] || [];
                const Icon = pillar.icon;

                return (
                  <div
                    key={pillar.key}
                    className="flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <Icon className={`h-4 w-4 ${pillar.color}`} />
                      <span className="text-sm font-medium text-gray-700">
                        {pillar.label}
                      </span>
                    </div>
                    <Badge
                      variant={pillarFindings.length === 0 ? "success" : "warning"}
                      size="sm"
                    >
                      {pillarFindings.length === 0 ? "✓" : `${pillarFindings.length} issues`}
                    </Badge>
                  </div>
                );
              })}
            </div>

            <div className="pt-4 border-t border-gray-200">
              <div className="flex flex-wrap gap-2 justify-center">
                {severityCounts.critical > 0 && (
                  <Badge variant="error" size="sm">
                    {severityCounts.critical} Critical
                  </Badge>
                )}
                {severityCounts.high > 0 && (
                  <Badge variant="warning" size="sm">
                    {severityCounts.high} High
                  </Badge>
                )}
                {severityCounts.medium > 0 && (
                  <Badge variant="info" size="sm">
                    {severityCounts.medium} Medium
                  </Badge>
                )}
                {severityCounts.low > 0 && (
                  <Badge variant="default" size="sm">
                    {severityCounts.low} Low
                  </Badge>
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
