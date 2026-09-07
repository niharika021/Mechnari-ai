import { api } from "@/lib/api";
import { DesignEngineerForm } from "./DesignEngineerForm";

export default async function DesignEngineerPage() {
  const [partTypes, systemPackages] = await Promise.all([
    api.partTypes(),
    api.systemPackages(),
  ]);

  return (
    <div>
      <h2 className="font-display text-lg font-bold text-ink">New Part Intake</h2>
      <p className="mt-1 max-w-[80ch] text-[13px] text-ink-faint">
        Describe the part you&apos;re designing. Mechnari identifies what kind of
        part it is, pulls the failure modes the company has already proven on
        parts like it, and drafts a starting DFMEA - evidence on every row, and
        what single change would bring a High row down.
      </p>
      <DesignEngineerForm partTypes={partTypes} systemPackages={systemPackages} />
    </div>
  );
}
