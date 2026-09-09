import { api } from "@/lib/api";
import { PartIntake } from "./PartIntake";

export default async function DesignEngineerPage() {
  const [partTypes, systemPackages, parts] = await Promise.all([
    api.partTypes(),
    api.systemPackages(),
    api.parts(),
  ]);

  return (
    <div>
      <h2 className="font-display text-lg font-bold text-ink">Part Intake</h2>
      <p className="mt-1 max-w-[80ch] text-[13px] text-ink-faint">
        Draft a DFMEA for a new part or a whole package, or open the one already
        on file for an existing part. Mechnari works out what kind of part each
        one is, finds what the company has already built like it, pulls what
        actually went wrong from the warranty record, and lays the result out in
        the AIAG-VDA form sheet — an 8D reference on every row, Occurrence
        measured from real claims rather than estimated, and the reassessed risk
        each recommended action would actually achieve.
      </p>
      <PartIntake
        partTypes={partTypes}
        systemPackages={systemPackages}
        parts={parts}
      />
    </div>
  );
}
