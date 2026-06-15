const initialPayload = clone(window.P2P_INITIAL_DATA || {});
let availableConfigFiles = clone(window.P2P_CONFIG_FILES || []);
let data = clone(initialPayload);
let activeNetwork = networkFromPayload(data);
let searchSequence = readSearchSequence(data.result && data.result.search_id);

const svg = document.getElementById("network");
const log = document.getElementById("log");
const resources = document.getElementById("resources");
const stepLabel = document.getElementById("stepLabel");
const playButton = document.getElementById("play");
const statusLabel = document.getElementById("statusLabel");
const messagePanel = document.getElementById("messagePanel");
const graphPanel = document.querySelector(".graph-panel");
const graphError = document.getElementById("graphError");
const caches = document.getElementById("caches");
const cachePanel = document.getElementById("cachePanel");
const searchStats = document.getElementById("searchStats");
const cacheLegendItem = document.getElementById("cacheLegendItem");
const appTitle = document.getElementById("appTitle");
const editorStatus = document.getElementById("editorStatus");
const errorPanel = document.getElementById("errorPanel");
const resourceOptions = document.getElementById("resourceOptions");
const nodeOptions = document.getElementById("nodeOptions");

const controls = {
  form: document.getElementById("searchForm"),
  algorithm: document.getElementById("algorithm"),
  startNode: document.getElementById("startNode"),
  resourceId: document.getElementById("resourceId"),
  ttl: document.getElementById("ttl"),
  configSelect: document.getElementById("configSelect"),
  ignoreCache: document.getElementById("ignoreCache"),
  randomExample: document.getElementById("randomExample"),
  applyMesh: document.getElementById("applyMesh"),
  meshNumNodes: document.getElementById("meshNumNodes"),
  meshMinNeighbors: document.getElementById("meshMinNeighbors"),
  meshMaxNeighbors: document.getElementById("meshMaxNeighbors"),
  meshResources: document.getElementById("meshResources"),
  meshEdges: document.getElementById("meshEdges"),
  meshCaches: document.getElementById("meshCaches"),
};

const ns = "http://www.w3.org/2000/svg";
let resourceByNode = new Map();
const visualNodes = new Map();
const nodeElements = new Map();
const edgeElements = new Map();
const eventEndpoints = new Map();
let frames = buildFrames(data.events || []);
let currentFrame = -1;
let timer = null;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function readSearchSequence(searchId) {
  const match = String(searchId || "").match(/^s(\d+)$/);
  return match ? Number(match[1]) : 0;
}

function cleanToken(value) {
  return String(value || "").trim();
}

function normalizeAlgorithm(algorithm) {
  return cleanToken(algorithm);
}

function stripComment(line) {
  return line.split("#", 1)[0].trim();
}

function splitList(value) {
  return String(value || "")
    .split(",")
    .map((item) => cleanToken(item))
    .filter(Boolean);
}

function compareNodeIds(a, b) {
  const left = String(a).match(/^n(\d+)$/i);
  const right = String(b).match(/^n(\d+)$/i);
  if (left && right) return Number(left[1]) - Number(right[1]);
  if (left) return -1;
  if (right) return 1;
  return String(a).localeCompare(String(b), "pt-BR", { numeric: true });
}

function compareResources(a, b) {
  return String(a).localeCompare(String(b), "pt-BR", { numeric: true });
}

function sortedUnique(values, sorter = undefined) {
  return Array.from(new Set(values.map(cleanToken).filter(Boolean))).sort(
    sorter,
  );
}

function mapToObject(map) {
  const object = {};
  for (const [key, value] of map.entries()) {
    object[key] = value instanceof Map ? mapToObject(value) : value;
  }
  return object;
}

function parseResourcesText(text) {
  const resourcesByNode = new Map();
  for (const rawLine of String(text || "").split(/\r?\n/)) {
    const line = stripComment(rawLine);
    if (!line) continue;
    const separatorIndex = line.indexOf(":");
    if (separatorIndex < 0) {
      throw new Error(`Linha de recurso inválida: ${line}`);
    }
    const node = cleanToken(line.slice(0, separatorIndex));
    const values = splitList(line.slice(separatorIndex + 1));
    if (!node) throw new Error("Nó vazio na lista de recursos");
    if (values.length === 0)
      throw new Error(`${node} precisa ter ao menos um recurso`);
    resourcesByNode.set(node, sortedUnique(values, compareResources));
  }
  if (resourcesByNode.size === 0) {
    throw new Error("Informe ao menos um nó em recursos");
  }
  return resourcesByNode;
}

function parseEdgesText(text) {
  const edges = [];
  for (const rawLine of String(text || "").split(/\r?\n/)) {
    const line = stripComment(rawLine);
    if (!line) continue;
    const normalized = line.replace(/--|->/g, ",");
    const parts = splitList(normalized);
    if (parts.length !== 2) {
      throw new Error(`Aresta inválida: ${line}`);
    }
    edges.push({ source: parts[0], target: parts[1] });
  }
  return edges;
}

function parseCacheEntry(entry) {
  const text = cleanToken(entry);
  const arrowIndex = text.indexOf("->");
  if (arrowIndex >= 0) {
    return [
      cleanToken(text.slice(0, arrowIndex)),
      cleanToken(text.slice(arrowIndex + 2)),
    ];
  }
  const equalIndex = text.indexOf("=");
  if (equalIndex >= 0) {
    return [
      cleanToken(text.slice(0, equalIndex)),
      cleanToken(text.slice(equalIndex + 1)),
    ];
  }
  throw new Error(`Cache inválido: ${entry}`);
}

function parseCachesText(text) {
  const configuredCaches = new Map();
  for (const rawLine of String(text || "").split(/\r?\n/)) {
    const line = stripComment(rawLine);
    if (!line) continue;
    const separatorIndex = line.indexOf(":");
    if (separatorIndex < 0) {
      throw new Error(`Linha de cache inválida: ${line}`);
    }
    const node = cleanToken(line.slice(0, separatorIndex));
    const entries = splitList(line.slice(separatorIndex + 1));
    if (!node) throw new Error("Nó vazio na lista de caches");
    const cacheMap = configuredCaches.get(node) || new Map();
    for (const entry of entries) {
      const [resource, holder] = parseCacheEntry(entry);
      if (!resource || !holder)
        throw new Error(`Cache incompleto em ${node}: ${entry}`);
      cacheMap.set(resource, holder);
    }
    configuredCaches.set(node, cacheMap);
  }
  return configuredCaches;
}

function parseRequiredInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) {
    throw new Error(`${name} deve ser inteiro`);
  }
  return parsed;
}

function parseEditorNetwork() {
  return normalizeNetwork({
    numNodes: parseRequiredInteger(controls.meshNumNodes.value, "num_nodes"),
    minNeighbors: parseRequiredInteger(
      controls.meshMinNeighbors.value,
      "min_neighbors",
    ),
    maxNeighbors: parseRequiredInteger(
      controls.meshMaxNeighbors.value,
      "max_neighbors",
    ),
    resourcesByNode: parseResourcesText(controls.meshResources.value),
    edges: parseEdgesText(controls.meshEdges.value),
    configuredCaches: parseCachesText(controls.meshCaches.value),
  });
}

function parseConfigFileText(text, filename = "") {
  const content = String(text || "").trim();
  if (!content) throw new Error("O arquivo está vazio");
  if (
    !filename.toLowerCase().endsWith(".yaml") &&
    !filename.toLowerCase().endsWith(".yml")
  ) {
    throw new Error("Topologia da rede deve estar em YAML (.yaml ou .yml)");
  }

  return normalizeNetwork(configToNetworkInput(parseSimpleYamlConfig(content)));
}

function parseSimpleYamlConfig(text) {
  const config = {};
  let section = null;

  for (const rawLine of String(text || "").split(/\r?\n/)) {
    const lineWithoutComment = rawLine.split("#", 1)[0];
    if (!lineWithoutComment.trim()) continue;
    const indent = lineWithoutComment.match(/^\s*/)[0].length;
    const line = lineWithoutComment.trim();

    if (indent === 0 && !line.startsWith("-")) {
      const separatorIndex = line.indexOf(":");
      if (separatorIndex < 0) throw new Error(`Linha YAML inválida: ${line}`);
      const key = cleanToken(line.slice(0, separatorIndex));
      const value = cleanToken(line.slice(separatorIndex + 1));
      if (["resources", "caches", "edges"].includes(key)) {
        section = key;
        config[key] = key === "edges" ? [] : {};
        if (value)
          throw new Error(`A seção ${key} deve ficar em linhas separadas`);
      } else {
        section = null;
        config[key] = value;
      }
      continue;
    }

    if (!section) throw new Error(`Linha fora de seção YAML: ${line}`);

    if (section === "edges") {
      const edgeValue = line.startsWith("-") ? cleanToken(line.slice(1)) : line;
      if (edgeValue) config.edges.push(edgeValue);
      continue;
    }

    const separatorIndex = line.indexOf(":");
    if (separatorIndex < 0)
      throw new Error(`Linha YAML inválida em ${section}: ${line}`);
    const node = cleanToken(line.slice(0, separatorIndex));
    const value = cleanToken(line.slice(separatorIndex + 1));
    config[section][node] = value;
  }

  return config;
}

function configToNetworkInput(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) {
    throw new Error("O arquivo precisa conter um objeto de configuração");
  }
  return {
    numNodes: parseRequiredInteger(config.num_nodes, "num_nodes"),
    minNeighbors: parseRequiredInteger(config.min_neighbors, "min_neighbors"),
    maxNeighbors: parseRequiredInteger(config.max_neighbors, "max_neighbors"),
    resourcesByNode: resourcesFromConfig(config.resources),
    edges: edgesFromConfig(config.edges || []),
    configuredCaches: cachesFromConfig(config.caches || {}),
  };
}

function resourcesFromConfig(rawResources) {
  if (
    !rawResources ||
    typeof rawResources !== "object" ||
    Array.isArray(rawResources)
  ) {
    throw new Error("O arquivo precisa conter a seção resources");
  }
  const resourcesByNode = new Map();
  for (const [node, rawValues] of Object.entries(rawResources)) {
    const values = Array.isArray(rawValues)
      ? rawValues.map(cleanToken).filter(Boolean)
      : splitList(rawValues);
    resourcesByNode.set(
      cleanToken(node),
      sortedUnique(values, compareResources),
    );
  }
  return resourcesByNode;
}

function parseEdgeValue(rawEdge) {
  if (typeof rawEdge === "string") {
    const normalized = rawEdge.replace(/--|->/g, ",");
    const parts = splitList(normalized);
    if (parts.length !== 2) throw new Error(`Aresta inválida: ${rawEdge}`);
    return { source: parts[0], target: parts[1] };
  }
  if (Array.isArray(rawEdge)) {
    const parts = rawEdge.map(cleanToken).filter(Boolean);
    if (parts.length !== 2)
      throw new Error(`Aresta inválida: ${JSON.stringify(rawEdge)}`);
    return { source: parts[0], target: parts[1] };
  }
  if (rawEdge && typeof rawEdge === "object") {
    const source = cleanToken(rawEdge.from || rawEdge.source || rawEdge.a);
    const target = cleanToken(rawEdge.to || rawEdge.target || rawEdge.b);
    if (!source || !target)
      throw new Error(`Aresta inválida: ${JSON.stringify(rawEdge)}`);
    return { source, target };
  }
  throw new Error(`Aresta inválida: ${String(rawEdge)}`);
}

function edgesFromConfig(rawEdges) {
  if (!Array.isArray(rawEdges))
    throw new Error("A seção edges precisa ser uma lista");
  return rawEdges.map(parseEdgeValue);
}

function cachesFromConfig(rawCaches) {
  const configuredCaches = new Map();
  if (!rawCaches) return configuredCaches;
  if (typeof rawCaches !== "object" || Array.isArray(rawCaches)) {
    throw new Error("A seção caches precisa ser um mapa");
  }

  for (const [rawNode, rawEntries] of Object.entries(rawCaches)) {
    const node = cleanToken(rawNode);
    const entries = new Map();
    if (Array.isArray(rawEntries)) {
      for (const entry of rawEntries) {
        const [resource, holder] = parseCacheEntry(entry);
        entries.set(resource, holder);
      }
    } else if (rawEntries && typeof rawEntries === "object") {
      for (const [resource, holder] of Object.entries(rawEntries)) {
        entries.set(cleanToken(resource), cleanToken(holder));
      }
    } else {
      for (const entry of splitList(rawEntries)) {
        const [resource, holder] = parseCacheEntry(entry);
        entries.set(resource, holder);
      }
    }
    configuredCaches.set(node, entries);
  }
  return configuredCaches;
}

function normalizeNetwork({
  numNodes,
  minNeighbors,
  maxNeighbors,
  resourcesByNode,
  edges,
  configuredCaches,
}) {
  const normalizedNumNodes = parseRequiredInteger(numNodes, "num_nodes");
  const normalizedMinNeighbors = parseRequiredInteger(
    minNeighbors,
    "min_neighbors",
  );
  const normalizedMaxNeighbors = parseRequiredInteger(
    maxNeighbors,
    "max_neighbors",
  );

  if (normalizedNumNodes <= 0)
    throw new Error("num_nodes deve ser maior que zero");
  if (normalizedMinNeighbors < 0 || normalizedMaxNeighbors < 0) {
    throw new Error("min_neighbors e max_neighbors não podem ser negativos");
  }
  if (normalizedMinNeighbors > normalizedMaxNeighbors) {
    throw new Error("min_neighbors não pode ser maior que max_neighbors");
  }
  if (normalizedMaxNeighbors > normalizedNumNodes - 1) {
    throw new Error("max_neighbors não pode exceder num_nodes - 1");
  }

  const nodes = Array.from(
    { length: normalizedNumNodes },
    (_, index) => `n${index + 1}`,
  );
  const nodeSet = new Set(nodes);
  const normalizedResources = new Map();
  const resourceOwners = new Map();

  for (const node of resourcesByNode.keys()) {
    if (!nodeSet.has(node))
      throw new Error(`resources contém nó desconhecido: ${node}`);
  }

  for (const node of nodes) {
    const values = sortedUnique(
      resourcesByNode.get(node) || [],
      compareResources,
    );
    if (values.length === 0)
      throw new Error(`${node} precisa ter ao menos um recurso`);
    normalizedResources.set(node, values);
    for (const resource of values) {
      if (resourceOwners.has(resource)) {
        throw new Error(
          `Recurso replicado: ${resource} em ${resourceOwners.get(resource)} e ${node}`,
        );
      }
      resourceOwners.set(resource, node);
    }
  }

  const adjacency = new Map(nodes.map((node) => [node, new Set()]));
  const edgeKeys = new Set();
  const normalizedEdges = [];
  for (const rawEdge of edges || []) {
    const source = cleanToken(rawEdge.source);
    const target = cleanToken(rawEdge.target);
    if (!nodeSet.has(source) || !nodeSet.has(target)) {
      throw new Error(`Aresta com nó desconhecido: ${source}, ${target}`);
    }
    if (source === target)
      throw new Error(`Aresta de ${source} para ele mesmo`);
    const [left, right] = [source, target].sort(compareNodeIds);
    const key = `${left}|${right}`;
    if (edgeKeys.has(key)) continue;
    edgeKeys.add(key);
    normalizedEdges.push({ source: left, target: right });
    adjacency.get(left).add(right);
    adjacency.get(right).add(left);
  }
  normalizedEdges.sort(
    (a, b) =>
      compareNodeIds(a.source, b.source) || compareNodeIds(a.target, b.target),
  );

  if (nodes.length > 1) {
    const isolated = nodes.filter((node) => adjacency.get(node).size === 0);
    if (isolated.length > 0)
      throw new Error(`Nós sem vizinhos: ${isolated.join(", ")}`);
    if (!isConnected(nodes, adjacency))
      throw new Error("A rede está particionada");
  }

  const invalidDegrees = nodes
    .map((node) => [node, adjacency.get(node).size])
    .filter(
      ([, degree]) =>
        degree < normalizedMinNeighbors || degree > normalizedMaxNeighbors,
    );
  if (invalidDegrees.length > 0) {
    const details = invalidDegrees
      .map(([node, degree]) => `${node}=${degree}`)
      .join(", ");
    throw new Error(
      `Quantidade de vizinhos fora dos limites [${normalizedMinNeighbors}, ${normalizedMaxNeighbors}]: ${details}`,
    );
  }

  const resourceLocations = new Map();
  for (const [resource, owner] of resourceOwners.entries()) {
    resourceLocations.set(resource, [owner]);
  }

  const normalizedCaches = new Map(nodes.map((node) => [node, new Map()]));
  for (const [node, entries] of (configuredCaches || new Map()).entries()) {
    if (!nodeSet.has(node))
      throw new Error(`Cache em nó desconhecido: ${node}`);
    for (const [resource, holder] of entries.entries()) {
      if (!resourceLocations.has(resource))
        throw new Error(`Cache referência recurso desconhecido: ${resource}`);
      if (!nodeSet.has(holder))
        throw new Error(`Cache referência nó desconhecido: ${holder}`);
      if (!normalizedResources.get(holder).includes(resource)) {
        throw new Error(
          `Cache aponta ${resource} para ${holder}, mas esse nó não possui o recurso`,
        );
      }
      normalizedCaches.get(node).set(resource, holder);
    }
  }

  return {
    numNodes: normalizedNumNodes,
    minNeighbors: normalizedMinNeighbors,
    maxNeighbors: normalizedMaxNeighbors,
    nodes,
    resources: normalizedResources,
    edges: normalizedEdges,
    adjacency,
    configuredCaches: normalizedCaches,
    resourceLocations,
  };
}

function isConnected(nodes, adjacency) {
  const visited = new Set([nodes[0]]);
  const queue = [nodes[0]];
  while (queue.length) {
    const node = queue.shift();
    for (const neighbor of adjacency.get(node) || []) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push(neighbor);
      }
    }
  }
  return visited.size === nodes.length;
}

function networkFromPayload(payload) {
  const config = payload.config || {};
  const resourcesByNode = new Map();
  for (const node of payload.nodes || []) {
    resourcesByNode.set(node.id, node.resources || []);
  }

  const configuredCaches = new Map();
  for (const node of payload.nodes || []) {
    const entries = new Map();
    for (const cacheEntry of node.cache || []) {
      if (cacheEntry.holder !== node.id) {
        entries.set(cacheEntry.resource, cacheEntry.holder);
      }
    }
    configuredCaches.set(node.id, entries);
  }

  return normalizeNetwork({
    numNodes: config.num_nodes ?? (payload.nodes || []).length,
    minNeighbors: config.min_neighbors ?? 0,
    maxNeighbors:
      config.max_neighbors ?? Math.max(0, (payload.nodes || []).length - 1),
    resourcesByNode,
    edges: payload.edges || [],
    configuredCaches,
  });
}

function serializeResources(network) {
  return network.nodes
    .map((node) => `${node}: ${(network.resources.get(node) || []).join(", ")}`)
    .join("\n");
}

function serializeEdges(network) {
  return network.edges
    .map((edge) => `${edge.source}, ${edge.target}`)
    .join("\n");
}

function serializeCaches(network) {
  const lines = [];
  for (const node of network.nodes) {
    const entries = Array.from(
      (network.configuredCaches.get(node) || new Map()).entries(),
    )
      .sort((a, b) => compareResources(a[0], b[0]))
      .map(([resource, holder]) => `${resource}=${holder}`);
    if (entries.length) lines.push(`${node}: ${entries.join(", ")}`);
  }
  return lines.join("\n");
}

function buildInitialCaches(network) {
  const cacheMap = new Map();
  for (const node of network.nodes) {
    const entries = new Map();
    for (const resource of network.resources.get(node) || []) {
      entries.set(resource, node);
    }
    for (const [resource, holder] of (
      network.configuredCaches.get(node) || new Map()
    ).entries()) {
      entries.set(resource, holder);
    }
    cacheMap.set(node, entries);
  }
  return cacheMap;
}

function snapshotCaches(cachesMap) {
  const snapshot = {};
  for (const [node, entries] of cachesMap.entries()) {
    snapshot[node] = {};
    for (const [resource, holder] of entries.entries()) {
      snapshot[node][resource] = holder;
    }
  }
  return snapshot;
}

function lookup(network, cachesMap, node, resourceId, useCache) {
  if ((network.resources.get(node) || []).includes(resourceId)) {
    return { holder: node, foundVia: "local" };
  }
  if (useCache && (cachesMap.get(node) || new Map()).has(resourceId)) {
    return { holder: cachesMap.get(node).get(resourceId), foundVia: "cache" };
  }
  return { holder: null, foundVia: null };
}

function addEvent(
  events,
  searchId,
  round,
  kind,
  source,
  target,
  resourceId,
  ttl,
) {
  events.push({
    step: events.length + 1,
    search_id: searchId,
    round,
    kind,
    source,
    target,
    resource_id: resourceId,
    ttl,
  });
}

function addDirectReplyIfNeeded(
  events,
  searchId,
  round,
  start,
  informedBy,
  resourceId,
  messages,
) {
  if (start === informedBy) return messages;
  addEvent(
    events,
    searchId,
    round,
    "reply",
    informedBy,
    start,
    resourceId,
    null,
  );
  return messages + 1;
}

function addDirectConnectionIfNeeded(
  events,
  searchId,
  round,
  start,
  holder,
  resourceId,
  messages,
) {
  if (start === holder) return messages;
  addEvent(events, searchId, round, "direct", start, holder, resourceId, null);
  return messages + 1;
}

function makeSuccess({
  searchId,
  algorithm,
  start,
  resourceId,
  ttl,
  ignoreCache,
  holder,
  informedBy,
  foundVia,
  messages,
  involved,
  path,
  events,
  cacheSnapshot,
  cachesMap,
}) {
  if (cachesMap.has(start)) cachesMap.get(start).set(resourceId, holder);
  return {
    search_id: searchId,
    algorithm,
    start_node: start,
    resource_id: resourceId,
    ttl,
    ignore_cache: ignoreCache,
    found: true,
    holder,
    informed_by: informedBy,
    found_via: foundVia,
    messages,
    nodes_involved: involved.size,
    path: path.join(" -> "),
    events,
    cache_snapshot: cacheSnapshot,
  };
}

function makeFailure({
  searchId,
  algorithm,
  start,
  resourceId,
  ttl,
  ignoreCache,
  messages,
  involved,
  path,
  events,
  cacheSnapshot,
}) {
  return {
    search_id: searchId,
    algorithm,
    start_node: start,
    resource_id: resourceId,
    ttl,
    ignore_cache: ignoreCache,
    found: false,
    holder: null,
    informed_by: null,
    found_via: null,
    messages,
    nodes_involved: involved.size,
    path: path.join(" -> "),
    events,
    cache_snapshot: cacheSnapshot,
  };
}

function runSearch(network, options) {
  const start = cleanToken(options.startNode);
  const resourceId = cleanToken(options.resourceId);
  const ttl = Number(options.ttl);
  const algorithm = normalizeAlgorithm(options.algorithm);

  if (!network.nodes.includes(start))
    throw new Error(`Nó inicial desconhecido: ${start}`);
  if (!resourceId) throw new Error("Informe o recurso da busca");
  if (!Number.isInteger(ttl) || ttl < 0)
    throw new Error("TTL deve ser inteiro maior ou igual a zero");
  if (!["flooding", "random_walk"].includes(algorithm)) {
    throw new Error(`Algoritmo inválido: ${algorithm}`);
  }

  searchSequence += 1;
  const searchId = `s${searchSequence}`;
  const cachesMap = buildInitialCaches(network);
  const cacheSnapshot = snapshotCaches(cachesMap);

  if (algorithm === "flooding") {
    return searchFlooding(network, cachesMap, cacheSnapshot, {
      searchId,
      start,
      resourceId,
      ttl,
      algorithm,
      ignoreCache: Boolean(options.ignoreCache),
    });
  }

  return searchRandomWalk(network, cachesMap, cacheSnapshot, {
    searchId,
    start,
    resourceId,
    ttl,
    algorithm,
    seed: options.seed,
    ignoreCache: Boolean(options.ignoreCache),
  });
}

function searchFlooding(network, cachesMap, cacheSnapshot, options) {
  const useCache = !options.ignoreCache;
  const initialLookup = lookup(
    network,
    cachesMap,
    options.start,
    options.resourceId,
    false,
  );
  const involved = new Set([options.start]);
  let messages = 0;
  const events = [];

  if (initialLookup.holder !== null) {
    return makeSuccess({
      searchId: options.searchId,
      algorithm: options.algorithm,
      start: options.start,
      resourceId: options.resourceId,
      ttl: options.ttl,
      ignoreCache: options.ignoreCache,
      holder: initialLookup.holder,
      informedBy: options.start,
      foundVia: initialLookup.foundVia,
      messages,
      involved,
      path: [options.start],
      events,
      cacheSnapshot,
      cachesMap,
    });
  }

  const processed = new Set([options.start]);
  let frontier = [
    {
      current: options.start,
      remainingTtl: options.ttl,
      path: [options.start],
    },
  ];
  let firstSuccess = null;
  let replySent = false;
  let roundNumber = 0;

  while (frontier.length) {
    roundNumber += 1;
    const nextFrontier = new Map();
    let replyNode = null;

    for (const item of frontier) {
      if (item.remainingTtl <= 0) continue;

      const neighbors = Array.from(
        network.adjacency.get(item.current) || [],
      ).sort(compareNodeIds);
      for (const neighbor of neighbors) {
        if (item.path.includes(neighbor)) continue;

        const nextTtl = item.remainingTtl - 1;
        const nextPath = [...item.path, neighbor];
        involved.add(neighbor);
        messages += 1;
        addEvent(
          events,
          options.searchId,
          roundNumber,
          "request",
          item.current,
          neighbor,
          options.resourceId,
          nextTtl,
        );

        if (processed.has(neighbor) || nextFrontier.has(neighbor)) continue;

        processed.add(neighbor);
        const found = lookup(
          network,
          cachesMap,
          neighbor,
          options.resourceId,
          useCache,
        );
        if (found.holder !== null) {
          if (firstSuccess === null) {
            firstSuccess = {
              holder: found.holder,
              informedBy: neighbor,
              foundVia: found.foundVia,
              path: nextPath,
            };
            replyNode = neighbor;
          }
        }

        if (nextTtl > 0) {
          nextFrontier.set(neighbor, {
            current: neighbor,
            remainingTtl: nextTtl,
            path: nextPath,
          });
        }
      }
    }

    if (replyNode !== null && !replySent) {
      const cacheHolder = firstSuccess ? firstSuccess.holder : replyNode;
      const foundVia = firstSuccess ? firstSuccess.foundVia : null;
      messages = addDirectReplyIfNeeded(
        events,
        options.searchId,
        roundNumber,
        options.start,
        replyNode,
        options.resourceId,
        messages,
      );
      if (foundVia === "cache") {
        involved.add(cacheHolder);
        messages = addDirectConnectionIfNeeded(
          events,
          options.searchId,
          roundNumber,
          options.start,
          cacheHolder,
          options.resourceId,
          messages,
        );
      }
      replySent = true;
    }

    frontier = Array.from(nextFrontier.values());
  }

  if (firstSuccess !== null) {
    const path = [...firstSuccess.path];
    if (
      firstSuccess.foundVia === "cache" &&
      firstSuccess.holder !== firstSuccess.informedBy
    ) {
      path.push(firstSuccess.holder);
    }
    return makeSuccess({
      searchId: options.searchId,
      algorithm: options.algorithm,
      start: options.start,
      resourceId: options.resourceId,
      ttl: options.ttl,
      ignoreCache: options.ignoreCache,
      holder: firstSuccess.holder,
      informedBy: firstSuccess.informedBy,
      foundVia: firstSuccess.foundVia,
      messages,
      involved,
      path,
      events,
      cacheSnapshot,
      cachesMap,
    });
  }

  return makeFailure({
    searchId: options.searchId,
    algorithm: options.algorithm,
    start: options.start,
    resourceId: options.resourceId,
    ttl: options.ttl,
    ignoreCache: options.ignoreCache,
    messages,
    involved,
    path: [options.start],
    events,
    cacheSnapshot,
  });
}

function searchRandomWalk(network, cachesMap, cacheSnapshot, options) {
  const useCache = !options.ignoreCache;
  const rng = makeRng(options.seed);
  let current = options.start;
  const path = [options.start];
  const stack = [options.start];
  const involved = new Set([options.start]);
  const visited = new Set([options.start]);
  let messages = 0;
  let remainingTtl = options.ttl;
  const events = [];

  while (true) {
    const found = lookup(
      network,
      cachesMap,
      current,
      options.resourceId,
      useCache && current !== options.start,
    );
    if (found.holder !== null) {
      const roundNumber = Math.max(0, path.length - 1);
      messages = addDirectReplyIfNeeded(
        events,
        options.searchId,
        roundNumber,
        options.start,
        current,
        options.resourceId,
        messages,
      );
      if (found.foundVia === "cache") {
        involved.add(found.holder);
        messages = addDirectConnectionIfNeeded(
          events,
          options.searchId,
          roundNumber,
          options.start,
          found.holder,
          options.resourceId,
          messages,
        );
      }
      const resultPath = [...path];
      if (found.foundVia === "cache" && found.holder !== current) {
        resultPath.push(found.holder);
      }
      return makeSuccess({
        searchId: options.searchId,
        algorithm: options.algorithm,
        start: options.start,
        resourceId: options.resourceId,
        ttl: options.ttl,
        ignoreCache: options.ignoreCache,
        holder: found.holder,
        informedBy: current,
        foundVia: found.foundVia,
        messages,
        involved,
        path: resultPath,
        events,
        cacheSnapshot,
        cachesMap,
      });
    }

    const neighbors = Array.from(network.adjacency.get(current) || [])
      .filter((neighbor) => !visited.has(neighbor))
      .sort(compareNodeIds);
    const previous = current;
    let nextEventTtl = remainingTtl;
    if (neighbors.length > 0) {
      if (remainingTtl === 0) {
        return makeFailure({
          searchId: options.searchId,
          algorithm: options.algorithm,
          start: options.start,
          resourceId: options.resourceId,
          ttl: options.ttl,
          ignoreCache: options.ignoreCache,
          messages,
          involved,
          path,
          events,
          cacheSnapshot,
        });
      }
      current = neighbors[Math.floor(rng() * neighbors.length)];
      stack.push(current);
      visited.add(current);
      nextEventTtl = remainingTtl - 1;
      remainingTtl -= 1;
    } else {
      if (stack.length === 1) {
        return makeFailure({
          searchId: options.searchId,
          algorithm: options.algorithm,
          start: options.start,
          resourceId: options.resourceId,
          ttl: options.ttl,
          ignoreCache: options.ignoreCache,
          messages,
          involved,
          path,
          events,
          cacheSnapshot,
        });
      }
      stack.pop();
      current = stack[stack.length - 1];
    }

    path.push(current);
    involved.add(current);
    messages += 1;
    addEvent(
      events,
      options.searchId,
      path.length - 1,
      "request",
      previous,
      current,
      options.resourceId,
      nextEventTtl,
    );
  }
}

function makeRng(seed) {
  const numericSeed = Number(seed);
  if (!Number.isFinite(numericSeed)) return Math.random;
  let value = numericSeed >>> 0;
  return function rng() {
    value += 0x6d2b79f5;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function circularLayout(nodes, width, height) {
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.38;
  if (nodes.length === 1) {
    return new Map([[nodes[0], { x: centerX, y: centerY }]]);
  }

  const positions = new Map();
  nodes.forEach((node, index) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / nodes.length;
    positions.set(node, {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    });
  });
  return positions;
}

function sequentialGraphLayers(nodes, edges, root = "n1") {
  const orderedNodes = [...nodes].sort(compareNodeIds);
  if (orderedNodes.length === 0) return [];

  const nodeSet = new Set(orderedNodes);
  const adjacency = new Map(orderedNodes.map((node) => [node, new Set()]));
  for (const edge of edges) {
    if (!nodeSet.has(edge.source) || !nodeSet.has(edge.target)) continue;
    adjacency.get(edge.source).add(edge.target);
    adjacency.get(edge.target).add(edge.source);
  }

  const start = nodeSet.has(root) ? root : orderedNodes[0];
  const visited = new Set([start]);
  const queue = [{ node: start, depth: 0 }];
  const layers = [[start]];

  while (queue.length > 0) {
    const { node, depth } = queue.shift();
    const neighbors = [...(adjacency.get(node) || [])].sort(compareNodeIds);
    for (const neighbor of neighbors) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      const nextDepth = depth + 1;
      while (layers.length <= nextDepth) layers.push([]);
      layers[nextDepth].push(neighbor);
      queue.push({ node: neighbor, depth: nextDepth });
    }
  }

  const remaining = orderedNodes.filter((node) => !visited.has(node));
  if (remaining.length > 0) layers.push(remaining);

  return layers
    .filter((layer) => layer.length > 0)
    .map((layer) => [...layer].sort(compareNodeIds));
}

function graphLayoutDimensions(nodes, edges) {
  const layers = sequentialGraphLayers(nodes, edges);
  const layerCount = Math.max(1, layers.length);
  const widestLayer = Math.max(1, ...layers.map((layer) => layer.length));
  const width = Math.max(760, 180 + widestLayer * 84);
  const height = Math.max(
    980,
    180 + (layerCount - 1) * 170,
    Math.round(width * 1.18),
  );
  return { width, height };
}

function topologyLayout(nodes, edges, width = null, height = null) {
  const layers = sequentialGraphLayers(nodes, edges);
  if (layers.length === 0) return new Map();

  const dimensions =
    width === null || height === null
      ? graphLayoutDimensions(nodes, edges)
      : { width, height };
  const layoutWidth = dimensions.width;
  const layoutHeight = dimensions.height;
  const paddingX = 90;
  const paddingY = 90;
  const usableWidth = Math.max(1, layoutWidth - 2 * paddingX);
  const usableHeight = Math.max(1, layoutHeight - 2 * paddingY);
  const lastLayerIndex = Math.max(1, layers.length - 1);
  const positions = new Map();

  layers.forEach((layer, layerIndex) => {
    const y =
      layers.length === 1
        ? layoutHeight / 2
        : paddingY + (usableHeight * layerIndex) / lastLayerIndex;
    const gap = usableWidth / (layer.length + 1);
    layer.forEach((node, nodeIndex) => {
      positions.set(node, {
        x: Math.round((paddingX + gap * (nodeIndex + 1)) * 100) / 100,
        y: Math.round(y * 100) / 100,
      });
    });
  });

  return positions;
}

function buildPayload(network, result) {
  const { width: layoutWidth, height: layoutHeight } = graphLayoutDimensions(
    network.nodes,
    network.edges,
  );
  const positions = topologyLayout(
    network.nodes,
    network.edges,
    layoutWidth,
    layoutHeight,
  );
  const resourceHolders =
    network.resourceLocations.get(result.resource_id) || [];
  const resourceHolder = resourceHolders[0] || null;
  const algorithmUsesCache = !result.ignore_cache;
  const cacheSnapshot =
    result.cache_snapshot || mapToObject(buildInitialCaches(network));

  function cacheFor(node) {
    return cacheSnapshot[node] || {};
  }

  function cacheIsRelevant(node) {
    const cachedHolder = cacheFor(node)[result.resource_id];
    return Boolean(
      node !== result.start_node && cachedHolder && cachedHolder !== node,
    );
  }

  const hasRelevantCache = network.nodes.some((node) => cacheIsRelevant(node));
  const hasConfiguredCache = network.nodes.some((node) =>
    Object.values(cacheFor(node)).some((holder) => holder !== node),
  );

  return {
    layout: { width: layoutWidth, height: layoutHeight },
    config: {
      num_nodes: network.numNodes,
      min_neighbors: network.minNeighbors,
      max_neighbors: network.maxNeighbors,
    },
    uses_cache: algorithmUsesCache && hasRelevantCache,
    has_configured_cache: algorithmUsesCache && hasConfiguredCache,
    nodes: network.nodes.map((node) => ({
      id: node,
      resources: [...(network.resources.get(node) || [])].sort(
        compareResources,
      ),
      cache: Object.entries(cacheFor(node))
        .sort((a, b) => compareResources(a[0], b[0]))
        .map(([resource, holder]) => ({
          resource,
          holder,
          local: holder === node,
          searched: resource === result.resource_id,
        })),
      cache_relevant: algorithmUsesCache && cacheIsRelevant(node),
      cache_used:
        algorithmUsesCache &&
        result.found_via === "cache" &&
        result.informed_by === node,
      x: positions.get(node).x,
      y: positions.get(node).y,
    })),
    edges: network.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
    })),
    events: result.events || [],
    resource_holder: resourceHolder,
    result,
  };
}

function makeSvg(tag, attrs = {}) {
  const el = document.createElementNS(ns, tag);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, value);
  }
  return el;
}

function eventPhase(event) {
  if (event.kind === "reply") return 1;
  if (event.kind === "direct") return 2;
  return 0;
}

function buildFrames(events) {
  const builtFrames = [];
  let current = null;
  for (const event of events) {
    const round = event.round === null ? -1 : event.round;
    const phase = eventPhase(event);
    const key = `${round}:${phase}`;
    if (!current || current.key !== key) {
      current = { key, round, phase, events: [] };
      builtFrames.push(current);
    }
    current.events.push(event);
  }
  return builtFrames;
}

function buildTopologyGraph() {
  const nodeIds = data.nodes.map((node) => node.id);
  const { width, height } = graphLayoutDimensions(nodeIds, data.edges);
  const positions = topologyLayout(nodeIds, data.edges, width, height);
  const eventEdges = (data.events || []).map((event) => ({
    source: event.source,
    target: event.target,
    eventStep: event.step,
    kind: event.kind,
  }));

  return {
    nodes: data.nodes.map((node) => ({
      ...node,
      ...(positions.get(node.id) || { x: node.x, y: node.y }),
    })),
    baseEdges: data.edges,
    eventEdges,
    width,
    height,
  };
}

function clearSvg() {
  svg.innerHTML = "";
  visualNodes.clear();
  nodeElements.clear();
  edgeElements.clear();
  eventEndpoints.clear();
}

function renderGraph() {
  clearSvg();
  const graph = buildTopologyGraph();
  svg.setAttribute("viewBox", `0 0 ${graph.width} ${graph.height}`);
  const baseEdgeLayer = makeSvg("g");
  const eventEdgeLayer = makeSvg("g");
  const nodeLayer = makeSvg("g");
  svg.append(baseEdgeLayer, eventEdgeLayer, nodeLayer);

  const graphNodeById = new Map(graph.nodes.map((node) => [node.id, node]));

  for (const edge of graph.baseEdges) {
    const source = graphNodeById.get(edge.source);
    const target = graphNodeById.get(edge.target);
    if (!source || !target) continue;
    const line = makeSvg("line", {
      class: "graph-edge base",
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
    });
    baseEdgeLayer.append(line);
  }

  for (const edge of graph.eventEdges) {
    const source = graphNodeById.get(edge.source);
    const target = graphNodeById.get(edge.target);
    if (!source || !target) continue;
    const id = `event-${edge.eventStep}`;
    const line = makeSvg("line", {
      class: `graph-edge event-edge ${edge.kind}`,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
    });
    eventEdgeLayer.append(line);
    edgeElements.set(id, line);
    eventEndpoints.set(edge.eventStep, {
      source: edge.source,
      target: edge.target,
      edgeId: id,
    });
  }

  for (const node of graph.nodes) {
    const classes = ["node"];
    if (data.uses_cache && node.cache_relevant) classes.push("cache");
    const group = makeSvg("g", {
      class: classes.join(" "),
      transform: `translate(${node.x}, ${node.y})`,
    });
    group.dataset.node = node.id;
    group.addEventListener("click", () => {
      controls.startNode.value = node.id;
      setEditorStatus(`Nó inicial: ${node.id}`, "ok");
    });

    const title = makeSvg("title");
    const searchedCache = (node.cache || []).find(
      (entry) => entry.resource === data.result.resource_id,
    );
    const cacheText = searchedCache
      ? ` - cache: ${searchedCache.resource} -> ${searchedCache.holder}`
      : "";
    title.textContent = `${node.id}: ${(resourceByNode.get(node.id) || []).join(", ")}${cacheText}`;
    group.append(title);
    if (data.uses_cache && node.cache_relevant) {
      group.append(makeSvg("circle", { class: "cache-ring", r: 31 }));
    }
    group.append(makeSvg("circle", { r: 24 }));
    const label = makeSvg("text");
    label.textContent = node.id;
    group.append(label);
    nodeLayer.append(group);
    nodeElements.set(node.id, group);
    visualNodes.set(node.id, node);
  }
}

function renderCacheList() {
  caches.innerHTML = "";
  const showCachePanel = Boolean(data.has_configured_cache || data.uses_cache);
  cachePanel.classList.toggle("hidden", !showCachePanel);
  cacheLegendItem.classList.toggle("hidden", !data.uses_cache);
  if (!showCachePanel) return;

  const relevantNodes = data.nodes.filter((node) => node.cache_relevant);
  if (relevantNodes.length === 0) {
    const item = document.createElement("li");
    item.textContent = `Nenhum nó tem ${data.result.resource_id} em cache.`;
    caches.append(item);
    return;
  }

  for (const node of relevantNodes) {
    const entry = node.cache.find(
      (cacheEntry) => cacheEntry.resource === data.result.resource_id,
    );
    if (!entry) continue;
    const item = document.createElement("li");
    item.dataset.node = node.id;
    const origin = entry.local ? "local" : "aprendido";
    const label = `${node.id}: ${entry.resource} -> ${entry.holder} (${origin})`;
    item.textContent = label;
    if (node.cache_used)
      item.dataset.usedLabel = `${label} - usado nesta busca`;
    caches.append(item);
  }
}

function renderResourcesList() {
  resources.innerHTML = "";
  for (const node of data.nodes) {
    const item = document.createElement("li");
    item.textContent = `${node.id}: ${node.resources.join(", ")}`;
    resources.append(item);
  }
}

function renderSearchStats() {
  const result = data.result || {};
  const holder = data.resource_holder || result.holder || "-";
  const foundVia = result.found_via || "-";
  const pairs = [
    ["Nó inicial", result.start_node || "-"],
    ["Recurso", result.resource_id || "-"],
    ["Algoritmo", result.algorithm || "-"],
    ["TTL", result.ttl ?? "-"],
    ["Mensagens", result.messages ?? "-"],
    ["Nós envolvidos", result.nodes_involved ?? "-"],
    ["Nó com recurso", holder],
    ["Encontrado via", foundVia],
    ["Caminho", result.path || "-"],
  ];

  searchStats.innerHTML = "";
  for (const [label, value] of pairs) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = String(value);
    searchStats.append(dt, dd);
  }
}

function renderDynamicSections() {
  appTitle.textContent = `Rede P2P - ${data.result.algorithm}`;
  document.title = `Rede P2P`;
  resourceByNode = new Map(data.nodes.map((node) => [node.id, node.resources]));
  frames = buildFrames(data.events || []);
  statusLabel.dataset.finalStatus = data.result.found
    ? "ENCONTRADO"
    : "NÃO ENCONTRADO";
  statusLabel.dataset.finalClass = data.result.found ? "found" : "not-found";
  renderSearchStats();
  renderCacheList();
  renderResourcesList();
}

function formatLogMessage(event) {
  const ttl = event.ttl === null ? "" : `, ttl=${event.ttl}`;
  const round = event.round === null ? "-" : event.round;
  const kindLabel = event.kind === "direct" ? "conexão direta" : event.kind;
  return `${event.step}. round=${round} ${kindLabel}: ${event.source} -> ${event.target}${ttl}`;
}

function appendFrameLog(frame) {
  for (const item of log.children) item.classList.remove("active");
  for (const event of frame.events) {
    const item = document.createElement("li");
    item.dataset.step = event.step;
    item.textContent = formatLogMessage(event);
    item.classList.add("active");
    log.append(item);
  }
  log.scrollTop = log.scrollHeight;
}

function renderView() {
  renderGraph();
  markBaseNodes();
}

function clearActive() {
  for (const edge of edgeElements.values()) {
    edge.classList.remove("active-request", "active-reply", "active-direct");
  }
  for (const node of nodeElements.values()) {
    node.classList.remove("active");
  }
}

function hideFinalStatus() {
  statusLabel.textContent = "EXPLORANDO";
  statusLabel.classList.remove("found", "not-found");
  statusLabel.classList.add("pending");
  if (frames.length === 0) {
    revealFinalStatus();
  }
}

function revealFinalStatus() {
  statusLabel.textContent = statusLabel.dataset.finalStatus;
  statusLabel.classList.remove("pending", "found", "not-found");
  statusLabel.classList.add(statusLabel.dataset.finalClass);
}

function markBaseNodes() {
  for (const node of nodeElements.values()) {
    const nodeId = node.dataset.node;
    if (nodeId === data.result.start_node) {
      node.classList.add("start", "involved");
    }
    if (data.result.holder && nodeId === data.result.holder) {
      node.classList.add("holder");
    }
    if (data.resource_holder && nodeId === data.resource_holder) {
      node.classList.add("holder");
    }
  }
}

function markCacheAccessed(nodeId) {
  if (!data.uses_cache) return;
  const node = nodeElements.get(nodeId);
  if (!node) return;
  const nodeData = data.nodes.find((item) => item.id === nodeId);
  if (!nodeData || !nodeData.cache_used) return;
  node.classList.add("cache-accessed");
  const cacheItem = caches.querySelector(`[data-node="${nodeId}"]`);
  if (cacheItem) {
    cacheItem.classList.add("used");
    cacheItem.textContent =
      cacheItem.dataset.usedLabel || cacheItem.textContent;
  }
}

function setStepLabel() {
  if (frames.length === 0 || currentFrame < 0) {
    stepLabel.textContent = `Quadro 0 / ${frames.length}`;
    return;
  }
  const frame = frames[currentFrame];
  const round = frame.round < 0 ? "-" : frame.round;
  const phase =
    frame.phase === 1
      ? "resposta"
      : frame.phase === 2
        ? "conexão direta"
        : "requisições";
  stepLabel.textContent = `Quadro ${currentFrame + 1} / ${frames.length} - rodada ${round} - ${phase}`;
}

function reset() {
  stop();
  currentFrame = -1;
  clearActive();
  for (const node of nodeElements.values()) {
    node.classList.remove("involved", "start", "holder", "cache-accessed");
  }
  log.innerHTML = "";
  messagePanel.classList.remove("playing");
  svg.querySelectorAll(".message").forEach((message) => message.remove());
  renderView();
  hideFinalStatus();
  setStepLabel();
}

function animateSingleEvent(event) {
  const endpoint = eventEndpoints.get(event.step);
  if (!endpoint) return;
  const source = visualNodes.get(endpoint.source);
  const target = visualNodes.get(endpoint.target);
  if (!source || !target) return;
  const edge = edgeElements.get(endpoint.edgeId);
  const sourceNode = nodeElements.get(endpoint.source);
  const targetNode = nodeElements.get(endpoint.target);
  const activeClass =
    event.kind === "reply"
      ? "active-reply"
      : event.kind === "direct"
        ? "active-direct"
        : "active-request";
  if (edge) edge.classList.add(activeClass);
  if (sourceNode) sourceNode.classList.add("active", "involved");
  if (targetNode) targetNode.classList.add("active", "involved");
  const touchedNodes = [sourceNode, targetNode];
  for (const node of touchedNodes) {
    if (node) markCacheAccessed(node.dataset.node);
  }

  const message = makeSvg("circle", {
    class: `message ${event.kind}`,
    r: 7,
    cx: source.x,
    cy: source.y,
  });
  const moveX = makeSvg("animate", {
    attributeName: "cx",
    from: source.x,
    to: target.x,
    dur: "1s",
    fill: "freeze",
  });
  const moveY = makeSvg("animate", {
    attributeName: "cy",
    from: source.y,
    to: target.y,
    dur: "1s",
    fill: "freeze",
  });
  message.append(moveX, moveY);
  svg.append(message);
  moveX.beginElement();
  moveY.beginElement();
  setTimeout(() => message.remove(), 1150);
}

function animateFrame(frame) {
  clearActive();
  messagePanel.classList.add("playing");
  svg.querySelectorAll(".message").forEach((message) => message.remove());
  for (const event of frame.events) {
    animateSingleEvent(event);
  }
  appendFrameLog(frame);
  setStepLabel();
}

function step() {
  if (currentFrame + 1 >= frames.length) {
    revealFinalStatus();
    stop();
    return;
  }
  currentFrame += 1;
  animateFrame(frames[currentFrame]);
  if (currentFrame + 1 >= frames.length) {
    revealFinalStatus();
    stop();
  }
}

function play() {
  if (timer) {
    stop();
    return;
  }
  if (currentFrame + 1 >= frames.length) reset();
  playButton.textContent = "Pausar";
  step();
  if (currentFrame + 1 < frames.length) {
    timer = setInterval(step, 1250);
  } else {
    playButton.textContent = "Reproduzir animação completa";
  }
}

function stop() {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  playButton.textContent = "Reproduzir animação completa";
}

function showGraphError(message) {
  graphError.textContent = message;
  graphError.classList.remove("hidden");
  graphPanel.classList.add("has-error");
}

function clearGraphError() {
  graphError.textContent = "";
  graphError.classList.add("hidden");
  graphPanel.classList.remove("has-error");
}

function setEditorStatus(message, type = "") {
  editorStatus.textContent = type === "error" ? "" : message;
  editorStatus.classList.remove("error", "ok");
  if (type && type !== "error") editorStatus.classList.add(type);
  if (type === "error") {
    errorPanel.textContent = message;
    errorPanel.classList.remove("hidden");
    showGraphError(
      `Não foi possível renderizar o grafo. Corrija a validação da topologia para continuar. Detalhes: ${message}`,
    );
  } else if (!message || type === "ok") {
    errorPanel.textContent = "";
    errorPanel.classList.add("hidden");
    if (type === "ok") clearGraphError();
  }
}

function reportUnexpectedError(error) {
  const message =
    error && error.message
      ? error.message
      : String(error || "erro desconhecido");
  stop();
  setEditorStatus(`Erro inesperado: ${message}`, "error");
}

function updateQueryOptions(network) {
  const selectedStart = controls.startNode.value || data.result.start_node;
  nodeOptions.innerHTML = "";
  for (const node of network.nodes) {
    const option = document.createElement("option");
    option.value = node;
    nodeOptions.append(option);
  }
  controls.startNode.value = network.nodes.includes(selectedStart)
    ? selectedStart
    : network.nodes[0];

  const resourcesList = Array.from(network.resourceLocations.keys()).sort(
    compareResources,
  );
  resourceOptions.innerHTML = "";
  for (const resource of resourcesList) {
    const option = document.createElement("option");
    option.value = resource;
    resourceOptions.append(option);
  }
  if (!controls.resourceId.value && resourcesList.length) {
    controls.resourceId.value = data.result.resource_id || resourcesList[0];
  }
}

function fillEditorFromNetwork(network) {
  controls.meshNumNodes.value = network.numNodes;
  controls.meshMinNeighbors.value = network.minNeighbors;
  controls.meshMaxNeighbors.value = network.maxNeighbors;
  controls.meshResources.value = serializeResources(network);
  controls.meshEdges.value = serializeEdges(network);
  controls.meshCaches.value = serializeCaches(network);
}

function normalizeCurrentQueryForNetwork(network) {
  updateQueryOptions(network);
  const resourcesList = Array.from(network.resourceLocations.keys()).sort(
    compareResources,
  );
  if (!resourcesList.includes(controls.resourceId.value)) {
    controls.resourceId.value = resourcesList[0] || "";
  }
}

function sameConfigFiles(left, right) {
  const comparable = (items) =>
    items.map((item) => ({ path: item.path, content: item.content }));
  return JSON.stringify(comparable(left)) === JSON.stringify(comparable(right));
}

async function discoverConfigFiles() {
  const response = await fetch("examples/", { cache: "no-store" });
  if (!response.ok) throw new Error("Pasta examples indisponível");
  const html = await response.text();
  const documentFragment = new DOMParser().parseFromString(html, "text/html");
  const paths = Array.from(documentFragment.querySelectorAll("a"))
    .map((link) => link.getAttribute("href") || "")
    .map((href) => decodeURIComponent(href.split(/[?#]/, 1)[0]))
    .filter((href) => /\.ya?ml$/i.test(href))
    .filter((href) => !href.includes("/") && !href.includes("\\"))
    .map((href) => `examples/${href}`);

  const uniquePaths = sortedUnique(paths);
  const configs = [];
  for (const path of uniquePaths) {
    const fileResponse = await fetch(path, { cache: "no-store" });
    if (!fileResponse.ok) continue;
    const content = await fileResponse.text();
    configs.push({
      name: path.split("/").pop(),
      path,
      content,
    });
  }
  return configs;
}

async function refreshConfigFiles() {
  try {
    const discovered = await discoverConfigFiles();
    if (!discovered.length || sameConfigFiles(discovered, availableConfigFiles)) {
      return;
    }
    const selectedPath = controls.configSelect.value;
    availableConfigFiles = discovered;
    populateConfigSelect(selectedPath);
  } catch {
    // Browsers block directory listing from file://; keep the embedded fallback list.
  }
}

function populateConfigSelect(preferredPath = "") {
  controls.configSelect.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Selecionar rede predefinida";
  controls.configSelect.append(placeholder);

  for (const config of availableConfigFiles) {
    const option = document.createElement("option");
    option.value = config.path;
    option.textContent = config.name;
    controls.configSelect.append(option);
  }
  const defaultConfig = availableConfigFiles.find(
    (config) => config.name === "mesh.yaml",
  );
  const preferredConfig = availableConfigFiles.find(
    (config) => config.path === preferredPath,
  );
  if (preferredConfig) {
    controls.configSelect.value = preferredConfig.path;
  } else if (defaultConfig) {
    controls.configSelect.value = defaultConfig.path;
  }
}

function hydrateControls() {
  populateConfigSelect();
  fillEditorFromNetwork(activeNetwork);
  controls.algorithm.value = normalizeAlgorithm(data.result.algorithm || "flooding");
  controls.resourceId.value = data.result.resource_id || "";
  controls.ttl.value = data.result.ttl ?? 3;
  controls.ignoreCache.checked = !Boolean(data.result.ignore_cache);
  updateQueryOptions(activeNetwork);
  updateAlgorithmControls();
}

function isRandomAlgorithm(algorithm) {
  return normalizeAlgorithm(algorithm) === "random_walk";
}

function createAutoSeed() {
  return Math.floor(Math.random() * 1000000000) + 1;
}

function updateAlgorithmControls() {
  const isRandom = isRandomAlgorithm(controls.algorithm.value);
  controls.randomExample.classList.toggle("hidden", !isRandom);
}

function collectSearchOptions() {
  const algorithm = controls.algorithm.value;
  return {
    algorithm,
    startNode: controls.startNode.value,
    resourceId: controls.resourceId.value,
    ttl: Number(controls.ttl.value),
    seed: isRandomAlgorithm(algorithm) ? createAutoSeed() : null,
    ignoreCache: !controls.ignoreCache.checked,
  };
}

function executeFromInterface(successMessage = "Busca executada.") {
  try {
    const network = parseEditorNetwork();
    updateQueryOptions(network);
    const options = collectSearchOptions();
    const result = runSearch(network, options);
    activeNetwork = network;
    data = buildPayload(activeNetwork, result);
    renderDynamicSections();
    reset();
    setEditorStatus(successMessage, "ok");
  } catch (error) {
    stop();
    setEditorStatus(error.message, "error");
  }
}

function loadSelectedConfig() {
  const selectedPath = controls.configSelect.value;
  if (!selectedPath) return;
  const config = availableConfigFiles.find(
    (item) => item.path === selectedPath,
  );
  if (!config) {
    setEditorStatus("Rede não encontrada na lista.", "error");
    return;
  }

  try {
    const network = parseConfigFileText(config.content, config.name);
    fillEditorFromNetwork(network);
    activeNetwork = network;
    normalizeCurrentQueryForNetwork(activeNetwork);
    executeFromInterface(`Rede ${config.name} carregada.`);
  } catch (error) {
    stop();
    setEditorStatus(error.message, "error");
  }
}

document.getElementById("play").addEventListener("click", play);
document.getElementById("step").addEventListener("click", step);
document.getElementById("reset").addEventListener("click", reset);

controls.form.addEventListener("submit", (event) => {
  event.preventDefault();
  executeFromInterface();
});
controls.applyMesh.addEventListener("click", () => executeFromInterface());
controls.randomExample.addEventListener("click", () =>
  executeFromInterface("Novo exemplo random gerado."),
);
controls.algorithm.addEventListener("change", updateAlgorithmControls);
controls.configSelect.addEventListener("change", loadSelectedConfig);
controls.configSelect.addEventListener("focus", refreshConfigFiles);
controls.configSelect.addEventListener("pointerdown", refreshConfigFiles);

for (const input of [
  controls.meshNumNodes,
  controls.meshMinNeighbors,
  controls.meshMaxNeighbors,
  controls.meshResources,
  controls.meshEdges,
  controls.meshCaches,
]) {
  input.addEventListener("input", () => setEditorStatus(""));
}

window.addEventListener("error", (event) => {
  reportUnexpectedError(event.error || event.message);
});

window.addEventListener("unhandledrejection", (event) => {
  reportUnexpectedError(event.reason);
});

hydrateControls();
refreshConfigFiles();
renderDynamicSections();
reset();
