export default function Footer() {
  return (
    <footer className="fixed bottom-0 left-0 right-0 z-50 bg-gray-900 border-t border-gray-800">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between text-xs">

        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">System:</span>
          <span className="text-gray-200 font-semibold">DataCommons_Copilot_v1</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">Active Model:</span>
          <span className="text-gray-200 font-semibold">claude-sonnet-4-6</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          <span className="text-green-400 font-semibold">Live Connection</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">Session Compute:</span>
          <span className="text-gray-200 font-semibold">0 Tokens</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">Est. Cost:</span>
          <span className="text-gray-200 font-semibold">{'$'}0.000</span>
        </div>

      </div>
    </footer>
  );
}
