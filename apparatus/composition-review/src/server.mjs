import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { constants } from "node:fs";
import { access, mkdir, open, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { ReviewError, ReviewStore } from "./storage.mjs";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const PUBLIC = resolve(ROOT, "public");
const host = process.env.COMPOSITION_REVIEW_HOST ?? "127.0.0.1";
const port = Number(process.env.COMPOSITION_REVIEW_PORT ?? 4193);
const bundlePath = process.env.COMPOSITION_REVIEW_BUNDLE;
const keyPath = process.env.COMPOSITION_REVIEW_KEY;
const statePath = process.env.COMPOSITION_REVIEW_STATE;
const tokenPath = process.env.COMPOSITION_REVIEW_TOKEN;
const assetRoot = process.env.COMPOSITION_REVIEW_ASSET_ROOT;
if (![bundlePath, keyPath, statePath, tokenPath].every((value) => value?.startsWith("/"))) {
  throw new Error("absolute review bundle, key, state, and token paths are required");
}

async function loadToken(path) {
  try {
    return (await readFile(path, "utf8")).trim();
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
    await mkdir(resolve(path, ".."), { recursive: true, mode: 0o700 });
    const value = randomBytes(32).toString("base64url");
    const handle = await open(path, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY, 0o600);
    try { await handle.writeFile(`${value}\n`); await handle.sync(); } finally { await handle.close(); }
    return value;
  }
}

const [store, enrollmentToken] = await Promise.all([
  ReviewStore.open({ bundlePath, keyPath, statePath, assetRoot }),
  loadToken(tokenPath),
]);
const sessionToken = createHash("sha256").update(`composition-review:${enrollmentToken}`).digest("base64url");

function equalToken(value, expected) {
  if (typeof value !== "string") return false;
  const left = Buffer.from(value); const right = Buffer.from(expected);
  return left.length === right.length && timingSafeEqual(left, right);
}

function cookie(request) {
  const header = request.headers.cookie ?? "";
  return header.split(";").map((item) => item.trim().split("=")).find(([key]) => key === "composition_review")?.[1];
}

function json(response, status, value) {
  const body = JSON.stringify(value);
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8", "content-length": Buffer.byteLength(body),
    "cache-control": "no-store", "x-content-type-options": "nosniff",
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
  });
  response.end(body);
}

function authorized(request) {
  return equalToken(cookie(request), sessionToken);
}

async function body(request) {
  let raw = "";
  for await (const chunk of request) {
    raw += chunk;
    if (Buffer.byteLength(raw) > 64 * 1024) throw new ReviewError("request_too_large", 413);
  }
  try { return JSON.parse(raw || "{}"); } catch { throw new ReviewError("invalid_json"); }
}

async function staticFile(response, pathname) {
  const names = { "/": "index.html", "/app.js": "app.js", "/styles.css": "styles.css" };
  const name = names[pathname];
  if (!name) return false;
  const path = resolve(PUBLIC, name);
  if (!path.startsWith(`${PUBLIC}/`)) return false;
  await access(path, constants.R_OK);
  const content = await readFile(path);
  const type = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8" }[extname(path)];
  response.writeHead(200, {
    "content-type": type, "content-length": content.length, "cache-control": "no-store",
    "x-content-type-options": "nosniff", "referrer-policy": "no-referrer",
    "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  });
  response.end(content);
  return true;
}

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://${request.headers.host ?? `${host}:${port}`}`);
    if (request.method === "GET" && url.pathname.startsWith("/enroll/")) {
      const supplied = decodeURIComponent(url.pathname.slice("/enroll/".length));
      if (!equalToken(supplied, enrollmentToken)) throw new ReviewError("invalid_enrollment", 403);
      response.writeHead(303, {
        location: "/", "cache-control": "no-store", "referrer-policy": "no-referrer",
        "set-cookie": `composition_review=${sessionToken}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800`,
      });
      response.end(); return;
    }
    if (!authorized(request)) {
      if (request.method === "GET" && url.pathname === "/") {
        const content = "<!doctype html><meta charset=utf-8><title>Composition Review</title><style>body{font:16px system-ui;background:#101017;color:#eee;display:grid;place-items:center;min-height:100vh}main{max-width:34rem;padding:2rem}code{color:#b9a7ff}</style><main><h1>Browser not enrolled</h1><p>Launch this review surface using the owner-only enrollment URL.</p><p><code>Composition Review remains locked.</code></p></main>";
        response.writeHead(401, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
        response.end(content); return;
      }
      throw new ReviewError("unauthorized", 401);
    }
    if (request.method === "GET" && url.pathname === "/api/session") {
      json(response, 200, store.session()); return;
    }
    const audioMatch = url.pathname.match(/^\/v1\/audio\/([a-z0-9][a-z0-9_-]{0,79})$/);
    if (request.method === "GET" && audioMatch) {
      const asset = store.audioAsset(audioMatch[1]);
      const content = await readFile(asset.path);
      response.writeHead(200, {
        "content-type": asset.mediaType, "content-length": content.length,
        "cache-control": "private, no-store", "x-content-type-options": "nosniff",
        "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
      });
      response.end(content); return;
    }
    if (request.method === "POST" && url.pathname === "/api/judgments") {
      json(response, 200, await store.commit(await body(request))); return;
    }
    if (request.method === "GET" && url.pathname === "/api/results") {
      json(response, 200, store.results()); return;
    }
    if (request.method === "GET" && await staticFile(response, url.pathname)) return;
    json(response, 404, { error: "not_found" });
  } catch (error) {
    const status = error instanceof ReviewError ? error.status : 500;
    json(response, status, { error: error instanceof ReviewError ? error.code : "internal_error" });
  }
});

server.listen(port, host, () => {
  const address = server.address();
  process.stdout.write(`Composition Review ready on http://${host}:${address.port}\n`);
});
