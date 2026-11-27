import http from "node:http";
import fs from "node:fs";

const UPSTREAM = process.env.XAI_URL || "https://api.x.ai";
const LOOPBACK = "127.0.0.1";
const PORT = Number(process.argv[2] || 0);
const ENDPOINT_FILE = process.env.ENDPOINT_FILE || "/tmp/grok_proxy_uri";
const XAPI_KEY = process.env.XAPI || process.env.XAI_API_KEY;

if (!XAPI_KEY) {
  console.error("ERROR: XAPI/XAI_API_KEY not set. Run: export XAPI=xai-...");
  process.exit(1);
}

const server = http.createServer(async (req, res) => {
  const headers = { ...req.headers };
  delete headers.host;
  delete headers.connection;
  delete headers["content-length"];
  headers.authorization = `Bearer ${XAPI_KEY}`;

  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const body = chunks.length ? Buffer.concat(chunks) : undefined;

  try {
    const upstream = await fetch(UPSTREAM + req.url, {
      method: req.method,
      headers,
      body,
    });
    res.writeHead(upstream.status, Object.fromEntries(upstream.headers));
    res.end(Buffer.from(await upstream.arrayBuffer()));
  } catch (err) {
    const msg = JSON.stringify({ error: String(err) });
    res.writeHead(502, { "Content-Type": "application/json" });
    res.end(msg);
  }
});

server.listen(PORT, LOOPBACK, () => {
  const addr = server.address();
  const uri = `http://${LOOPBACK}:${addr.port}`;
  const payload = JSON.stringify({ uri, upstream: UPSTREAM }, null, 2);
  fs.writeFileSync(ENDPOINT_FILE, payload);
  console.log(payload);
});