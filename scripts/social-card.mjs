// SPDX-License-Identifier: AGPL-3.0-only

import sharp from "sharp";

// Canonical pixel ghost from yurei-so/assets/img/yurei-labs.png. Embedded so
// the Pages build remains self-contained and the card uses the real brand mark.
const ghostPng = "iVBORw0KGgoAAAANSUhEUgAAANAAAAEACAYAAADC7fjvAAAACXBIWXMAAA7EAAAOxAGVKw4bAAACpElEQVR4nO3csU0DQRRF0VlqoB0KowIKox16gHwCJ1f27mfPyf21snSz0TsWD31+/PyW3399vx//+f7dvZ39ATCZgCAQEAQCgkBAEAgIAgFBICAIBASBgCAQEAQCgkBAEAgIAgEBAAAAAAAAbMZvfk3fVXN/9u6clwgQCAgCAUEgIAgEBIGAIBAQBAKCQEAQCAgCAUEgIAgEBIGAIBAQAAAAAAAAwGb0Jtda83fJfL9dOLgtAUEgIAgEBIGAIBAQBAKCQEAQCAgCAUEgIAgEBIGAIBAQBAICAAAAAAAA2Ize5Frr+btk7p97/+q8RIBAQBAICAIBQSAgCAQEgYAgEBAEAoJAQBAICAIBQSAgCAQEgYAAAAAAAAAANk/f5Jq+SzZ992z6/3P1/99LBAgEBIGAIBAQBAKCQEAQCAgCAUEgIAgEBIGAIBAQBAKCQEAQCAgAAAAAAABgc0zf9XLf/TPve4kAgYAgEBAEAoJAQBAICAIBQSAgCAQEgYAgEBAEAoJAQBAICAIBAQAAAAAAAGzswrnvfuAlAgQCgkBAEAgIAgFBICAIBASBgCAQEAQCgkBAEAgIAgFBICAIBAQAAAAAAACwebiZNcHVd8Pcb/evzksECAQEgYAgEBAEAoJAQBAICAIBQSAgCAQEgYAgEBAEAoJAQBAICAAAAAAAAGAzepNrrfm7Z+7bhYPbEhAEAoJAQBAICAIBQSAgCAQEgYAgEBAEAoJAQBAICAIBQSAgAAAAAAAAgM3oTa5XmL6rdvfdtmfzEgECAUEgIAgEBIGAIBAQBAKCQEAQCAgCAUEgIAgEBIGAIBAQBAICAAAAAAAA2Nj8Opndttm8RIBAQBAICAIBQSAgCAQEgYAgEBAEAoJAQBAICAIBQSAgCAQEgYAg+AN+edaYePAdtwAAAABJRU5ErkJggg==";

const colors = {
  positive: "#52d6a1", negative: "#ff728f", mixed: "#f2c263",
  inconclusive: "#68c9ed", pending: "#a5acba", "not-applicable": "#a5acba",
};

function xml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function glyphWidth(value, fontSize) {
  let units = 0;
  for (const character of String(value)) {
    if (/[MW@%&]/.test(character)) units += 0.9;
    else if (/[ilI1'.,:;!|]/.test(character)) units += 0.3;
    else if (/[A-Z0-9]/.test(character)) units += 0.66;
    else if (character === " ") units += 0.3;
    else units += 0.56;
  }
  return units * fontSize;
}

function wrap(value, width, limit, fontSize = null) {
  const words = String(value).trim().split(/\s+/);
  const lines = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    const fits = fontSize ? glyphWidth(candidate, fontSize) <= width : candidate.length <= width;
    if (fits || !current) current = candidate;
    else { lines.push(current); current = word; }
  }
  if (current) lines.push(current);
  if (lines.length > limit) {
    lines.length = limit;
    lines[limit - 1] = `${lines[limit - 1].slice(0, Math.max(1, width - 1)).trimEnd()}…`;
  }
  return lines;
}

export function socialCardSvg(note) {
  let titleSize = 72;
  let titleLines = wrap(note.title, 1020, 3, titleSize);
  if (titleLines.length > 1) {
    titleSize = titleLines.length === 2 ? 64 : 54;
    titleLines = wrap(note.title, 1020, 3, titleSize);
  }
  const titleStart = 174;
  const titleStep = titleSize * 1.06;
  const summaryLines = wrap(note.result_summary || note.question, 76, 2);
  const summaryStart = Math.max(430, titleStart + titleLines.length * titleStep + 48);
  const outcome = note.outcome.toUpperCase();
  const accent = colors[note.outcome] ?? "#a98cff";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#080a10"/><rect x="0" y="0" width="12" height="630" fill="#8b5cf6"/>
<text x="104" y="76" fill="#e8e9f0" font-family="Inter,system-ui,sans-serif" font-size="25" font-weight="700" letter-spacing="4">YUREI RESEARCH</text>
<text x="1138" y="76" text-anchor="end" fill="#7f8798" font-family="ui-monospace,monospace" font-size="19">${xml(note.id.toUpperCase())}</text>
<line x1="46" y1="112" x2="1140" y2="112" stroke="#252a37" stroke-width="2"/>
<text x="62" y="151" fill="#ad8bff" font-family="ui-monospace,monospace" font-size="18" letter-spacing="3">LABNOTE / ${xml(note.family.toUpperCase())}</text>
${titleLines.map((line, index) => `<text x="58" y="${titleStart + index * titleStep}" dominant-baseline="hanging" fill="#e5e7ef" font-family="Inter,system-ui,sans-serif" font-size="${titleSize}" font-weight="650">${xml(line)}</text>`).join("\n")}
<text x="62" y="${summaryStart}" fill="#b6bbc8" font-family="Inter,system-ui,sans-serif" font-size="26">${xml(summaryLines[0] ?? "")}</text>
<text x="62" y="${summaryStart + 38}" fill="#b6bbc8" font-family="Inter,system-ui,sans-serif" font-size="26">${xml(summaryLines[1] ?? "")}</text>
<line x1="46" y1="551" x2="1140" y2="551" stroke="#252a37" stroke-width="2"/>
<text x="62" y="595" fill="#8d94a5" font-family="ui-monospace,monospace" font-size="19">${xml(note.date)}  ·  ${xml(note.status.toUpperCase())}</text>
<circle cx="638" cy="589" r="6" fill="${accent}"/><text x="658" y="596" fill="${accent}" font-family="ui-monospace,monospace" font-size="21" font-weight="700">${xml(outcome)}</text>
<text x="1138" y="595" text-anchor="end" fill="#8d94a5" font-family="ui-monospace,monospace" font-size="18">yurei-so.github.io/research</text>
</svg>`;
}

function projectedPoints(attention) {
  const raw = Object.values(attention?.projection?.points ?? {});
  if (!raw.length) return [];
  const xs = raw.map((point) => point[0]);
  const ys = raw.map((point) => point[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  return raw.map(([x, y]) => ({
    x: maxX === minX ? .5 : (x - minX) / (maxX - minX),
    y: maxY === minY ? .5 : (y - minY) / (maxY - minY),
  }));
}

function pixelHeatmap(attention) {
  const points = projectedPoints(attention);
  const columns = 30, rows = 18, size = 15, left = 684, top = 181;
  const pixels = [];
  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const x = column / (columns - 1), y = row / (rows - 1);
      const heat = Math.min(1, points.reduce((sum, point) => {
        const distance = (x - point.x) ** 2 + (y - point.y) ** 2;
        return sum + Math.exp(-distance / .028);
      }, 0));
      const level = Math.floor(heat * 5);
      if (!level) continue;
      const opacity = [.12, .2, .32, .48, .72][level - 1];
      pixels.push(`<rect x="${left + column * size}" y="${top + row * size}" width="13" height="13" fill="#9a73f2" opacity="${opacity}"/>`);
    }
  }
  const nodes = points.map((point) => `<rect x="${Math.round(left + point.x * (columns - 1) * size - 4)}" y="${Math.round(top + point.y * (rows - 1) * size - 4)}" width="9" height="9" fill="#d9c8ff"/>`).join("");
  return `${pixels.join("")}\n${nodes}`;
}

export function familySocialCardSvg(family, notes, attention) {
  const titleLines = wrap(family.title, 550, 2, 68);
  const outcomes = Object.entries(family.outcomes).map(([name, count]) => `${count} ${name}`).join("  ·  ");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#080a10"/><rect width="12" height="630" fill="#8b5cf6"/>
<text x="104" y="76" fill="#e8e9f0" font-family="Inter,system-ui,sans-serif" font-size="25" font-weight="700" letter-spacing="4">YUREI RESEARCH</text>
<text x="1138" y="76" text-anchor="end" fill="#7f8798" font-family="ui-monospace,monospace" font-size="19">RESEARCH FAMILY</text>
<line x1="46" y1="112" x2="1140" y2="112" stroke="#252a37" stroke-width="2"/>
<text x="62" y="164" fill="#ad8bff" font-family="ui-monospace,monospace" font-size="18" letter-spacing="3">PROJECT / ${xml(family.id.toUpperCase())}</text>
${titleLines.map((line, index) => `<text x="58" y="${205 + index * 74}" dominant-baseline="hanging" fill="#e5e7ef" font-family="Inter,system-ui,sans-serif" font-size="68" font-weight="650">${xml(line)}</text>`).join("\n")}
<text x="62" y="426" fill="#b6bbc8" font-family="Inter,system-ui,sans-serif" font-size="27">${notes.length} published labnotes</text>
<text x="62" y="472" fill="#8d94a5" font-family="ui-monospace,monospace" font-size="18">${xml(outcomes.toUpperCase())}</text>
<rect x="660" y="151" width="498" height="330" fill="#0b0d14" stroke="#252a37" stroke-width="2"/>
${pixelHeatmap(attention)}
<text x="1138" y="514" text-anchor="end" fill="#737b8e" font-family="ui-monospace,monospace" font-size="16">CORPUS-RELATIVE ATTENTION · PIXEL PREVIEW</text>
<line x1="46" y1="551" x2="1140" y2="551" stroke="#252a37" stroke-width="2"/>
<text x="62" y="595" fill="#ad8bff" font-family="ui-monospace,monospace" font-size="20">DETAILED VIEW</text>
<text x="1138" y="595" text-anchor="end" fill="#8d94a5" font-family="ui-monospace,monospace" font-size="18">yurei-so.github.io/research</text>
</svg>`;
}

export async function writeSocialCard(note, destination) {
  const ghost = await sharp(Buffer.from(ghostPng, "base64"))
    .resize({ width: 42, height: 52, fit: "contain", kernel: sharp.kernel.nearest })
    .png().toBuffer();
  await sharp(Buffer.from(socialCardSvg(note)))
    .composite([{ input: ghost, left: 42, top: 34 }])
    .png({ compressionLevel: 9 }).toFile(destination);
}

export async function writeFamilySocialCard(family, notes, attention, destination) {
  const ghost = await sharp(Buffer.from(ghostPng, "base64"))
    .resize({ width: 42, height: 52, fit: "contain", kernel: sharp.kernel.nearest })
    .png().toBuffer();
  await sharp(Buffer.from(familySocialCardSvg(family, notes, attention)))
    .composite([{ input: ghost, left: 42, top: 34 }])
    .png({ compressionLevel: 9 }).toFile(destination);
}
// SPDX-License-Identifier: AGPL-3.0-only
