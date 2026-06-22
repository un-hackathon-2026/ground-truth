"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck, BarChart2, ChevronDown, Globe } from "lucide-react";

export default function Header() {
  const pathname = usePathname();
  const isPolicy = pathname === "/policy-dashboard";

  const tabCls = (active: boolean) =>
    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
      active ? "bg-white text-blue-600 shadow-sm" : "text-gray-500 hover:text-gray-700"
    }`;

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">

        {/* UN Logo */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
            <svg viewBox="0 0 40 40" className="w-8 h-8" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="14" stroke="white" strokeWidth="1.5" fill="none" />
              <ellipse cx="20" cy="20" rx="7" ry="14" stroke="white" strokeWidth="1" fill="none" />
              <line x1="6" y1="20" x2="34" y2="20" stroke="white" strokeWidth="1" />
              <ellipse cx="20" cy="20" rx="14" ry="5.5" stroke="white" strokeWidth="1" fill="none" />
              <path d="M10 8 Q20 4 30 8" stroke="white" strokeWidth="1" fill="none" />
              <path d="M10 32 Q20 36 30 32" stroke="white" strokeWidth="1" fill="none" />
            </svg>
          </div>
          <div className="min-w-0">
            <div className="text-sm font-extrabold text-gray-900 leading-tight tracking-wide">UNITED NATIONS</div>
            <div className="text-xs font-medium text-gray-500 leading-tight tracking-widest">DATA COMMONS PLATFORM</div>
          </div>
        </div>

        {/* Center Nav Toggle */}
        <div className="flex items-center bg-gray-100 rounded-xl p-1 gap-1">
          <Link href="/" className={tabCls(!isPolicy)}>
            <ShieldCheck className="w-4 h-4" />
            Ground-Truth Trust Filter
          </Link>
          <Link href="/policy-dashboard" className={tabCls(isPolicy)}>
            <BarChart2 className="w-4 h-4" />
            Policy Dashboard
          </Link>
        </div>

        {/* Language Dropdown */}
        <button className="flex items-center gap-2 text-sm text-gray-700 border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors">
          <Globe className="w-4 h-4 text-gray-500" />
          English
          <ChevronDown className="w-4 h-4 text-gray-400" />
        </button>

      </div>
    </header>
  );
}
