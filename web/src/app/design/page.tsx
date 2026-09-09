import { api } from "@/lib/api";
import { PartIntake } from "./PartIntake";

export default async function DesignEngineerPage() {
  const [partTypes, systemPackages] = await Promise.all([
    api.partTypes(),
    api.systemPackages(),
  ]);

  return (
    <div>
      <h2 className="font-display text-lg font-bold text-ink">New Part Intake</h2>
      <p className="mt-1 max-w-[80ch] text-[13px] text-ink-faint">
        Enter a single part or a whole package. Mechnari works out what kind of
        part each one is, finds the parts the company has already built like it,
        pulls what actually went wrong with those from the warranty record, and
        drafts the DFMEA in the AIAG-VDA form sheet layout — an 8D reference on
        every row, Occurrence measured from real claims rather than estimated,
        and the reassessed risk each recommended action would actually achieve.
      </p>
      <PartIntake partTypes={partTypes} systemPackages={systemPackages} />
    </div>
  );
}
