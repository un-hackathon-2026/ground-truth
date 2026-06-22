import { ChevronRight } from "lucide-react";
import VisualizationCard from "@/components/dashboard/VisualizationCard";
import SynthesisEngine from "@/components/dashboard/SynthesisEngine";

interface SearchParams {
  dataset?: string;
  country?: string;
  name?: string;
}

export default async function PolicyDashboardPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const { dataset, country, name } = await searchParams;

  return (
    <div className="max-w-4xl mx-auto px-6 py-7">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm mb-6">
        <span className="text-gray-500">Home</span>
        <ChevronRight className="w-4 h-4 text-gray-400" strokeWidth={1.75} />
        <span className="text-gray-900 font-semibold">Policy Dashboard</span>
      </nav>

      <div className="space-y-5">
        <VisualizationCard dataset={dataset} country={country} name={name} />
        <SynthesisEngine />
      </div>
    </div>
  );
}
