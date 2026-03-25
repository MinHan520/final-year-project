import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '50mb' }));

  // In-memory history for demonstration (would normally use a database)
  let scanHistory: any[] = [];

  // API Routes
  app.get("/api/history", (req, res) => {
    res.json(scanHistory);
  });

  app.post("/api/history", (req, res) => {
    const newScan = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      ...req.body
    };
    scanHistory.unshift(newScan);
    // Keep only last 20 scans
    if (scanHistory.length > 20) scanHistory = scanHistory.slice(0, 20);
    res.status(201).json(newScan);
  });

  app.delete("/api/history", (req, res) => {
    scanHistory = [];
    res.status(204).send();
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
