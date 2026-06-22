import { ChevronRight } from "lucide-react";
import TrustApp from "@/components/TrustApp";

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-7">

      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm mb-6">
        <span className="text-gray-500 hover:text-gray-700 cursor-pointer transition-colors">
          Home
        </span>
        <ChevronRight className="w-4 h-4 text-gray-400" strokeWidth={1.75} />
        <span className="text-gray-900 font-semibold">
          Trust Filter (Verification)
        </span>
      </nav>

      <TrustApp />

    </div>
  );
}
