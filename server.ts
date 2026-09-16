import express from "express";
import path from "path";
import fs from "fs";
import { execFile, exec } from "child_process";
import { promisify } from "util";
import { createServer as createViteServer } from "vite";

const execPromise = promisify(exec);
const PORT = 3000;

async function startServer() {
  const app = express();
  app.use(express.json());

  // API Routes
  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok", brand: "AmazonHelp", provider: "Groq" });
  });

  // Get discovered intent taxonomy
  app.get("/api/taxonomy", (_req, res) => {
    const taxonomyPath = path.join(process.cwd(), "config", "intents.json");
    if (fs.existsSync(taxonomyPath)) {
      const data = JSON.parse(fs.readFileSync(taxonomyPath, "utf-8"));
      res.json(data);
    } else {
      res.status(404).json({ error: "Taxonomy config not found" });
    }
  });

  // Process inbound customer tweet through agent pipeline
  app.post("/api/agent/process", async (req, res) => {
    try {
      const { message, context } = req.body;
      if (!message || typeof message !== "string") {
        return res.status(400).json({ error: "Message is required" });
      }

      const scriptPath = path.join(process.cwd(), "src", "agent", "pipeline.py");
      const safeMsg = message.replace(/"/g, '\\"');
      const safeCtx = (context || "Twitter inquiry").replace(/"/g, '\\"');

      const cmd = `python3 "${scriptPath}" --message "${safeMsg}" --context "${safeCtx}"`;
      const { stdout, stderr } = await execPromise(cmd, { cwd: process.cwd() });

      // Extract JSON from output
      const start = stdout.indexOf("{");
      const end = stdout.lastIndexOf("}");
      if (start !== -1 && end !== -1 && end > start) {
        const jsonStr = stdout.substring(start, end + 1);
        const parsed = JSON.parse(jsonStr);
        return res.json(parsed);
      }

      res.status(500).json({ error: "Failed to parse agent output", raw: stdout, stderr });
    } catch (err: any) {
      console.error("Agent execution error:", err);
      res.status(500).json({ error: err.message || "Pipeline execution failed" });
    }
  });

  // Get evaluation summary
  app.get("/api/evaluation/summary", (_req, res) => {
    const summaryPath = path.join(process.cwd(), "results", "evaluation_summary.json");
    if (fs.existsSync(summaryPath)) {
      const data = JSON.parse(fs.readFileSync(summaryPath, "utf-8"));
      res.json(data);
    } else {
      res.status(404).json({ error: "Evaluation summary not found. Run evaluation first." });
    }
  });

  // Get confusion matrix
  app.get("/api/evaluation/confusion-matrix", (_req, res) => {
    const cmPath = path.join(process.cwd(), "results", "confusion_matrix.json");
    if (fs.existsSync(cmPath)) {
      const data = JSON.parse(fs.readFileSync(cmPath, "utf-8"));
      res.json(data);
    } else {
      res.status(404).json({ error: "Confusion matrix not found" });
    }
  });

  // Helper: parse CSV line handling quoted delimiters
  function parseCSVLine(text: string): string[] {
    const result: string[] = [];
    let cur = "";
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === '"') {
        if (inQuotes && text[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (c === "," && !inQuotes) {
        result.push(cur.trim());
        cur = "";
      } else {
        cur += c;
      }
    }
    result.push(cur.trim());
    return result;
  }

  // Get golden evaluation set samples enriched with generated reply and judge scores
  app.get("/api/evaluation/golden-set", (_req, res) => {
    const csvPath = path.join(process.cwd(), "evaluation", "golden_set.csv");
    if (!fs.existsSync(csvPath)) {
      return res.status(404).json({ error: "Golden set not found" });
    }

    // Check if predictions.csv exists to attach responses & judge scores
    const predPath = path.join(process.cwd(), "results", "predictions.csv");
    const predMap: Record<string, Record<string, any>> = {};
    if (fs.existsSync(predPath)) {
      try {
        const predContent = fs.readFileSync(predPath, "utf-8");
        const predLines = predContent.split("\n").filter((l) => l.trim().length > 0);
        if (predLines.length > 1) {
          const predHeaders = parseCSVLine(predLines[0]);
          for (let i = 1; i < predLines.length; i++) {
            const vals = parseCSVLine(predLines[i]);
            const row: Record<string, any> = {};
            predHeaders.forEach((h, idx) => {
              row[h] = vals[idx] || "";
            });
            if (row.id) {
              predMap[row.id] = row;
            }
          }
        }
      } catch (err) {
        console.error("Error reading predictions.csv:", err);
      }
    }

    const content = fs.readFileSync(csvPath, "utf-8");
    const lines = content.split("\n").filter((l) => l.trim().length > 0);
    if (lines.length < 2) return res.json([]);

    const headers = parseCSVLine(lines[0]);
    const records = [];

    for (let i = 1; i < lines.length; i++) {
      const values = parseCSVLine(lines[i]);
      const rec: Record<string, any> = {};
      headers.forEach((h, idx) => {
        rec[h] = values[idx] || "";
      });

      // Enrich with prediction reply & judge scores if present
      const pred = predMap[rec.id];
      if (pred) {
        rec.reply = pred.reply || "";
        rec.pred_intent = pred.pred_intent || "";
        rec.pred_escalation = pred.pred_escalation || "";
        rec.judge_relevance = pred.judge_relevance ? Number(pred.judge_relevance) : undefined;
        rec.judge_groundedness = pred.judge_groundedness ? Number(pred.judge_groundedness) : undefined;
        rec.judge_correctness = pred.judge_correctness ? Number(pred.judge_correctness) : undefined;
        rec.judge_helpfulness = pred.judge_helpfulness ? Number(pred.judge_helpfulness) : undefined;
        rec.judge_unsupported_claims = pred.judge_unsupported_claims ? Number(pred.judge_unsupported_claims) : undefined;
        rec.judge_average_score = pred.judge_average_score ? Number(pred.judge_average_score) : undefined;
        rec.judge_verdict = pred.judge_verdict || "";
      }

      records.push(rec);
    }

    res.json(records);
  });

  // Get saved human judgments (JSON state)
  app.get("/api/evaluation/human-judgments", (_req, res) => {
    const jsonPath = path.join(process.cwd(), "results", "human_judgments.json");
    if (fs.existsSync(jsonPath)) {
      try {
        const data = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
        return res.json(data);
      } catch (err) {
        console.error("Error reading human_judgments.json:", err);
      }
    }
    res.json({});
  });

  // Save human judgments to local JSON file
  app.post("/api/evaluation/human-judgments", (req, res) => {
    try {
      const { id, rating, judgments } = req.body;
      const jsonPath = path.join(process.cwd(), "results", "human_judgments.json");
      let current: Record<string, any> = {};
      if (fs.existsSync(jsonPath)) {
        try {
          current = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
        } catch {}
      }

      if (judgments && typeof judgments === "object") {
        current = { ...current, ...judgments };
      } else if (id && rating) {
        current[id] = {
          ...rating,
          updated_at: rating.updated_at || new Date().toISOString()
        };
      }

      fs.writeFileSync(jsonPath, JSON.stringify(current, null, 2), "utf-8");
      res.json({ success: true, count: Object.keys(current).length, judgments: current });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Compute human-LLM agreement using human_agreement.py
  app.get("/api/evaluation/human-agreement", async (_req, res) => {
    try {
      const scriptPath = path.join(process.cwd(), "evaluation", "human_agreement.py");
      const cmd = `python3 "${scriptPath}" --json`;
      const { stdout } = await execPromise(cmd, { cwd: process.cwd() });
      
      const start = stdout.indexOf("{");
      const end = stdout.lastIndexOf("}");
      if (start !== -1 && end !== -1 && end >= start) {
        const parsed = JSON.parse(stdout.substring(start, end + 1));
        return res.json(parsed);
      }
      res.json({ status: "pending_human_annotations", stdout });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Verify a golden evaluation set record
  app.post("/api/evaluation/verify", (req, res) => {
    try {
      const { id } = req.body;
      const csvPath = path.join(process.cwd(), "evaluation", "golden_set.csv");
      if (!fs.existsSync(csvPath)) return res.status(404).json({ error: "File not found" });

      const content = fs.readFileSync(csvPath, "utf-8");
      const lines = content.split("\n");
      const updatedLines = lines.map((line) => {
        if (line.startsWith(id + ",")) {
          return line.replace(/,PROPOSED$/, ",VERIFIED_BY_HUMAN");
        }
        return line;
      });

      fs.writeFileSync(csvPath, updatedLines.join("\n"), "utf-8");
      res.json({ success: true, id, status: "VERIFIED_BY_HUMAN" });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Run evaluation harness
  app.post("/api/evaluation/run", async (req, res) => {
    try {
      const maxSamples = req.body.maxSamples || 25;
      const scriptPath = path.join(process.cwd(), "evaluation", "run_evaluation.py");
      const cmd = `python3 "${scriptPath}" --max-samples ${maxSamples}`;
      const { stdout } = await execPromise(cmd, { cwd: process.cwd() });
      
      const summaryPath = path.join(process.cwd(), "results", "evaluation_summary.json");
      if (fs.existsSync(summaryPath)) {
        const data = JSON.parse(fs.readFileSync(summaryPath, "utf-8"));
        return res.json({ success: true, summary: data, stdout });
      }
      res.json({ success: true, stdout });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Vite Middleware Setup
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server listening at http://0.0.0.0:${PORT}`);
  });
}

startServer();
