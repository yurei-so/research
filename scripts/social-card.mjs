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

function wrap(value, width, limit) {
  const words = String(value).trim().split(/\s+/);
  const lines = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= width || !current) current = candidate;
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
  const titleLines = wrap(note.title, 32, 3);
  const titleSize = titleLines.length === 1 ? 78 : titleLines.length === 2 ? 68 : 58;
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

export async function writeSocialCard(note, destination) {
  const ghost = await sharp(Buffer.from(ghostPng, "base64"))
    .resize({ width: 42, height: 52, fit: "contain", kernel: sharp.kernel.nearest })
    .png().toBuffer();
  await sharp(Buffer.from(socialCardSvg(note)))
    .composite([{ input: ghost, left: 42, top: 34 }])
    .png({ compressionLevel: 9 }).toFile(destination);
}
