import type { ForensicMaps, OpenCVComments } from '../../api/types';

interface ForensicMapTrioProps {
  maps: ForensicMaps;
  comments?: OpenCVComments;
}

export function ForensicMapTrio({ maps, comments }: ForensicMapTrioProps) {
  const items = [
    { title: 'Noise Residuals', b64: maps.noise_png_b64, text: comments?.noise },
    { title: 'Laplacian Edge Gradient', b64: maps.edge_png_b64, text: comments?.edges },
    { title: 'Compression Analysis (ELA)', b64: maps.ela_png_b64, text: comments?.compression },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
      {items.map((item, i) => (
        <div key={i} className="space-y-2">
          <p className="text-xs font-medium text-muted uppercase">{item.title}</p>
          <img
            src={`data:image/png;base64,${item.b64}`}
            alt={item.title}
            className="w-full h-auto rounded-md border border-border bg-black"
          />
          {item.text && <p className="text-sm text-muted mt-2">{item.text}</p>}
        </div>
      ))}
    </div>
  );
}
