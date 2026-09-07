"use client";

import { useEffect, useState } from "react";
import { api, type AuditResult, type Part } from "@/lib/api";
import { Callout, Select, Spinner } from "@/components/ui";

export function PartAuditor({ parts }: { parts: Part[] }) {
  const [partId, setPartId] = useState(parts[0]?.part_id ?? "");
  const [result, setResult] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!partId) return;
    setLoading(true);
    api
      .auditPart(partId)
      .then(setResult)
      .finally(() => setLoading(false));
  }, [partId]);

  return (
    <div className="mt-3 flex flex-col gap-4">
      <Select
        value={partId}
        onChange={(e) => setPartId(e.target.value)}
        className="max-w-md"
      >
        {parts.map((p) => (
          <option key={p.part_id} value={p.part_id}>
            {p.part_id} — {p.item_reference}
          </option>
        ))}
      </Select>

      {loading ? <Spinner /> : null}

      {result ? (
        <div className="flex flex-col gap-2.5">
          {result.severity_findings.length === 0 ? (
            <Callout tone="ok">
              ✓ Severity matches the organization standard for every effect on
              this part.
            </Callout>
          ) : (
            result.severity_findings.map((f, i) => (
              <Callout tone="crit" key={i}>
                ⚠ <strong>{f.failure_mode}</strong>: {f.finding} (scored S=
                {f.severity}, standard S={f.standard_severity} for {f.effect_description})
              </Callout>
            ))
          )}

          {result.occurrence_findings.length === 0 ? (
            <Callout tone="ok">
              ✓ Occurrence on file is consistent with the warranty record.
            </Callout>
          ) : (
            result.occurrence_findings.map((f, i) => (
              <Callout tone="warn" key={i}>
                ~ <strong>{f.failure_mode}</strong>: filed O={f.occurrence},{" "}
                {f.finding.toLowerCase()} to O={f.derived_occurrence} ({f.evidence_scope},{" "}
                {f.evidence_ids})
              </Callout>
            ))
          )}

          {result.gaps.length === 0 ? (
            <Callout tone="ok">
              ✓ Coverage complete - every catalogued mode for this part&apos;s
              type and family is analysed.
            </Callout>
          ) : (
            <Callout tone="crit">
              ⚠ {result.gaps.length} catalogued failure mode(s) not yet
              analysed, {result.gaps.filter((g) => g.standard_severity >= 9).length} at
              severity 9+.
            </Callout>
          )}
        </div>
      ) : null}
    </div>
  );
}
