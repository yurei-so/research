import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { writeAudioFixture, writeFixture } from "./helpers.mjs";

async function startServer(directory, mode = "text") {
  const { bundlePath, keyPath } = mode === "audio"
    ? await writeAudioFixture(directory) : await writeFixture(directory);
  const tokenPath = join(directory, "token"); const token = "owner-enrollment-token";
  await writeFile(tokenPath, `${token}\n`, { mode: 0o600 });
  const child = spawn(process.execPath, ["src/server.mjs"], {
    cwd: new URL("..", import.meta.url),
    env: { ...process.env, COMPOSITION_REVIEW_PORT: "0", COMPOSITION_REVIEW_HOST: "127.0.0.1",
      COMPOSITION_REVIEW_BUNDLE: bundlePath, COMPOSITION_REVIEW_KEY: keyPath,
      COMPOSITION_REVIEW_STATE: join(directory, "state/judgments.json"),
      COMPOSITION_REVIEW_TOKEN: tokenPath, COMPOSITION_REVIEW_ASSET_ROOT: directory },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stderr = "";
  child.stderr.on("data", (chunk) => { stderr += String(chunk); });
  const line = await new Promise((resolve, reject) => {
    child.stdout.once("data", (chunk) => resolve(String(chunk)));
    child.once("exit", (code) => reject(new Error(`server exited ${code}: ${stderr}`)));
  });
  const port = Number(line.match(/:(\d+)/)?.[1]);
  return { child, base: `http://127.0.0.1:${port}`, token };
}

test("server requires enrollment and withholds results until completion", async (context) => {
  const directory = await mkdtemp(join(tmpdir(), "composition-review-server-"));
  const { child, base, token } = await startServer(directory);
  context.after(() => child.kill("SIGTERM"));
  const locked = await fetch(base);
  assert.equal(locked.status, 401);
  const enrolled = await fetch(`${base}/enroll/${token}`, { redirect: "manual" });
  assert.equal(enrolled.status, 303);
  const cookie = enrolled.headers.get("set-cookie").split(";")[0];
  const headers = { cookie, "content-type": "application/json" };
  const sessionResponse = await fetch(`${base}/api/session`, { headers });
  assert.equal(sessionResponse.status, 200);
  const session = await sessionResponse.json();
  assert.equal(session.pair.pair_id, "pair-one");
  assert.equal(JSON.stringify(session).includes("schema_revision"), false);
  assert.equal((await fetch(`${base}/api/results`, { headers })).status, 409);
  const next = await fetch(`${base}/api/judgments`, { method: "POST", headers,
    body: JSON.stringify({ pair_id: "pair-one", choice: "tie", secondary: {} }) });
  assert.equal(next.status, 200);
  const page = await fetch(base, { headers });
  assert.equal(page.status, 200);
  assert.match(page.headers.get("content-security-policy"), /frame-ancestors 'none'/);
  const app = await (await fetch(`${base}/app.js`, { headers })).text();
  assert.match(app, /treatment_arm/);
  assert.doesNotMatch(app, /schema_revision|Structured revision/);
});

test("server serves verified audio only after enrollment", async (context) => {
  const directory = await mkdtemp(join(tmpdir(), "composition-review-audio-server-"));
  const { child, base, token } = await startServer(directory, "audio");
  context.after(() => child.kill("SIGTERM"));
  assert.equal((await fetch(`${base}/v1/audio/clip-one`)).status, 401);
  const enrolled = await fetch(`${base}/enroll/${token}`, { redirect: "manual" });
  const cookie = enrolled.headers.get("set-cookie").split(";")[0];
  const headers = { cookie, "content-type": "application/json" };
  const session = await (await fetch(`${base}/api/session`, { headers })).json();
  assert.equal(session.mode, "audio");
  assert.equal(JSON.stringify(session).includes("gold_ir"), false);
  const audio = await fetch(`${base}${session.pair.audio_a}`, { headers });
  assert.equal(audio.status, 200);
  assert.equal(audio.headers.get("content-type"), "audio/wav");
  assert.match(await (await fetch(`${base}/app.js`, { headers })).text(), /composition_audio_ready/);
});
