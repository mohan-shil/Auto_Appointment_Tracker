import test from "node:test";
import assert from "node:assert/strict";
import { createMockServer } from "../mock-server/server.js";

async function withServer(run) {
  const server = createMockServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  try {
    await run(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
}

test("health endpoint identifies the isolated mock and confirms no live connection", async () => {
  await withServer(async (base) => {
    const response = await fetch(`${base}/health`);
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), {
      ok: true,
      service: "synthetic-ivac-mock",
      livePortalConnected: false
    });
  });
});

test("mock page is served and clearly marked as synthetic", async () => {
  await withServer(async (base) => {
    const response = await fetch(base);
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.match(html, /Synthetic Mock Portal/);
    assert.match(html, /TEST ENVIRONMENT ONLY/);
    assert.match(html, /STOPPED — PAYMENT PAGE DETECTED/);
    assert.doesNotMatch(html, /appointment\.ivacbd\.com/);
  });
});

test("unknown routes are not proxied to a real portal", async () => {
  await withServer(async (base) => {
    const response = await fetch(`${base}/anything`);
    assert.equal(response.status, 404);
    assert.deepEqual(await response.json(), {
      error: "Not found",
      livePortalConnected: false
    });
  });
});
