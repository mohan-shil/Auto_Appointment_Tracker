import { createServer as createHttpServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const htmlPath = join(here, "index.html");

export function createMockServer() {
  return createHttpServer(async (request, response) => {
    const pathname = new URL(request.url ?? "/", "http://127.0.0.1").pathname;

    if (request.method === "GET" && pathname === "/health") {
      response.writeHead(200, { "content-type": "application/json; charset=utf-8" });
      response.end(JSON.stringify({ ok: true, service: "synthetic-ivac-mock", livePortalConnected: false }));
      return;
    }

    if (request.method === "GET" && (pathname === "/" || pathname === "/index.html")) {
      try {
        const html = await readFile(htmlPath);
        response.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
        response.end(html);
      } catch {
        response.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
        response.end("Mock page could not be loaded.");
      }
      return;
    }

    response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ error: "Not found", livePortalConnected: false }));
  });
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const port = Number(process.env.MOCK_PORT || 4173);
  const host = "127.0.0.1";
  const server = createMockServer();
  server.listen(port, host, () => {
    process.stdout.write(`Synthetic IVAC mock: http://${host}:${port}\n`);
  });
}
