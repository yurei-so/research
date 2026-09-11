const stopwords = new Set("a an and are as at be by can did do does for from had has have how if in into is it its may not of on or our that the their this to was were what when where whether which while who why with without".split(" "));

function terms(note) {
  const prose = `${note.question} ${note.title}`.toLowerCase().match(/[a-z0-9]+(?:-[a-z0-9]+)*/g) ?? [];
  return [...prose.filter((term) => term.length > 1 && !stopwords.has(term)), ...note.tags, ...note.tags];
}

function normalize(weights) {
  const magnitude = Math.hypot(...Object.values(weights));
  return Object.fromEntries(Object.entries(weights).map(([term, value]) => [term, value / (magnitude || 1)]));
}

function cosineDistance(left, right) {
  let similarity = 0;
  for (const [term, value] of Object.entries(left)) similarity += value * (right[term] ?? 0);
  return Math.max(0, Math.min(1, 1 - similarity));
}

function multiply(matrix, vector) {
  return matrix.map((row) => row.reduce((sum, value, index) => sum + value * vector[index], 0));
}

function unit(vector) {
  const magnitude = Math.hypot(...vector) || 1;
  return vector.map((value) => value / magnitude);
}

function dot(left, right) { return left.reduce((sum, value, index) => sum + value * right[index], 0); }

function classicalMds(distances) {
  const count = distances.length;
  if (count === 1) return [[0, 0]];
  const squared = distances.map((row) => row.map((value) => value ** 2));
  const rowMeans = squared.map((row) => row.reduce((sum, value) => sum + value, 0) / count);
  const totalMean = rowMeans.reduce((sum, value) => sum + value, 0) / count;
  const gram = squared.map((row, i) => row.map((value, j) => -.5 * (value - rowMeans[i] - rowMeans[j] + totalMean)));
  const components = [];
  const eigenvalues = [];
  for (let component = 0; component < 2; component += 1) {
    let vector = unit(Array.from({ length: count }, (_, index) => Math.sin((index + 1) * (component + 1) * 1.618)));
    let degenerate = false;
    for (let iteration = 0; iteration < 120; iteration += 1) {
      let next = multiply(gram, vector);
      for (const previous of components) {
        const projection = dot(next, previous);
        next = next.map((value, index) => value - projection * previous[index]);
      }
      if (Math.hypot(...next) < 1e-10) { degenerate = true; break; }
      vector = unit(next);
    }
    if (degenerate) vector = Array(count).fill(0);
    const eigenvalue = degenerate ? 0 : Math.max(0, dot(vector, multiply(gram, vector)));
    components.push(vector);
    eigenvalues.push(eigenvalue);
  }
  return Array.from({ length: count }, (_, index) => components.map((component, axis) => component[index] * Math.sqrt(eigenvalues[axis])));
}

export function buildAttentionModel(corpusNotes, projectNotes) {
  const documentTerms = new Map(corpusNotes.map((note) => [note.id, terms(note)]));
  const vocabulary = [...new Set([...documentTerms.values()].flat())].sort();
  const documentFrequency = Object.fromEntries(vocabulary.map((term) => [term,
    [...documentTerms.values()].filter((tokens) => new Set(tokens).has(term)).length]));
  const vectorFor = (note) => {
    const tokens = documentTerms.get(note.id);
    const counts = tokens.reduce((result, term) => ({ ...result, [term]: (result[term] ?? 0) + 1 }), {});
    return normalize(Object.fromEntries(Object.entries(counts).map(([term, count]) =>
      [term, count / tokens.length * (Math.log((corpusNotes.length + 1) / (documentFrequency[term] + 1)) + 1)])));
  };
  const vectors = new Map(projectNotes.map((note) => [note.id, vectorFor(note)]));
  const distances = projectNotes.map((left) => projectNotes.map((right) => cosineDistance(vectors.get(left.id), vectors.get(right.id))));
  const coordinates = classicalMds(distances);
  let error = 0;
  let total = 0;
  for (let left = 0; left < projectNotes.length; left += 1) for (let right = left + 1; right < projectNotes.length; right += 1) {
    const projected = Math.hypot(coordinates[left][0] - coordinates[right][0], coordinates[left][1] - coordinates[right][1]);
    error += (distances[left][right] - projected) ** 2;
    total += distances[left][right] ** 2;
  }
  return {
    representation: { method: "tf-idf", fields: ["question", "title", "tags"], dimensions: vocabulary.length, metric: "cosine-distance" },
    vectors: Object.fromEntries([...vectors].map(([id, vector]) => [id, Object.fromEntries(Object.entries(vector).map(([term, value]) => [term, Number(value.toFixed(6))]))])),
    pairwise_distances: distances.map((row) => row.map((value) => Number(value.toFixed(6)))),
    projection: { method: "classical-mds", dimensions: 2, normalized_stress: total ? Number(Math.sqrt(error / total).toFixed(6)) : 0,
      points: Object.fromEntries(projectNotes.map((note, index) => [note.id, coordinates[index].map((value) => Number(value.toFixed(6)))])) },
    warning: "Density and sparsity describe only this published Yurei corpus. Two-dimensional geometry is approximate and is not evidence of causality, support, value, truth, or a real knowledge gap.",
  };
}
