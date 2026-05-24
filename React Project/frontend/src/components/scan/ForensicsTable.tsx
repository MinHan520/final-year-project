import { Link } from 'react-router-dom';
import { useScansList } from '../../hooks/useScansList';
import { RiskBar } from './RiskBar';
import { StatusBadge } from './StatusBadge';
import { Trash2 } from 'lucide-react';

export function ForensicsTable() {
  const { scans, isLoading, deleteScan } = useScansList();

  if (isLoading) {
    return <div className="rounded-card border border-border bg-card/60 p-10 text-center text-sm text-muted animate-pulse">Loading scans...</div>;
  }

  if (scans.length === 0) {
    return (
      <div className="rounded-card border border-border bg-card/60 p-10 text-center text-sm text-muted">
        No scans yet. Upload an image above to populate the table.
      </div>
    );
  }

  return (
    <div className="rounded-card border border-border bg-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-card/50 text-xs uppercase tracking-wider text-muted border-b border-border">
            <tr>
              <th className="px-6 py-4 font-medium">File Name</th>
              <th className="px-6 py-4 font-medium">Type</th>
              <th className="px-6 py-4 font-medium">Risk Score</th>
              <th className="px-6 py-4 font-medium">Status</th>
              <th className="px-6 py-4 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {scans.map((scan) => (
              <tr key={scan.scan_id} className="hover:bg-card/60 transition-colors">
                <td className="px-6 py-4">
                  <Link to={`/scan/${scan.scan_id}`} className="text-fg font-medium hover:underline">
                    {scan.filename}
                  </Link>
                  <div className="text-xs text-muted mt-1">{new Date(scan.created_at).toLocaleString()}</div>
                </td>
                <td className="px-6 py-4">
                  <span className="px-2 py-1 bg-bg-elevated border border-border rounded text-xs uppercase tracking-wider text-muted font-bold">
                    {scan.media_type}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <RiskBar score={scan.score} label={scan.risk_label} />
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={scan.status} risk_label={scan.risk_label} />
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-3">
                    <Link to={`/scan/${scan.scan_id}`} className="text-primary hover:text-primary-hover text-xs font-medium">
                      Details
                    </Link>
                    <button 
                      onClick={() => deleteScan(scan.scan_id)}
                      className="text-muted hover:text-danger p-1 rounded transition-colors"
                      title="Delete Scan"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
