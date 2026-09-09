import { api } from "@/lib/api";
import { PageHeader } from "@/components/RoleNav";
import { PartIntake } from "./PartIntake";

export default async function DesignEngineerPage() {
  const [partTypes, systemPackages, parts] = await Promise.all([
    api.partTypes(),
    api.systemPackages(),
    api.parts(),
  ]);

  return (
    <div>
      {/* The 85-word explanation that used to sit here has moved into
          PartIntake's own "How this works" disclosure. It described what
          Mechnari does to a part - genuinely useful the first time, read
          zero times by an engineer on their fourth draft of the week, and
          it pushed the first form control 617px down a 698px viewport. */}
      <PageHeader
        title="Part Intake"
        purpose="Draft a DFMEA, or open one already on file."
      />
      <PartIntake
        partTypes={partTypes}
        systemPackages={systemPackages}
        parts={parts}
      />
    </div>
  );
}
