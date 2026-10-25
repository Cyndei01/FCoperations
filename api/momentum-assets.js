const BASE_URL = (process.env.MOMENTUM_API_BASE_URL || "https://api.momentumiot.com").replace(/\/$/, "");

function findFirst(value, keys) {
  if (!value || typeof value !== "object") return "";
  for (const key of keys) {
    if (value[key] !== undefined && value[key] !== null && value[key] !== "") return value[key];
  }
  const lowered = Object.fromEntries(Object.entries(value).map(([key, item]) => [key.toLowerCase(), item]));
  for (const key of keys) {
    const item = lowered[key.toLowerCase()];
    if (item !== undefined && item !== null && item !== "") return item;
  }
  return "";
}

function tokenTenant(token) {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return findFirst(JSON.parse(Buffer.from(normalized, "base64").toString("utf8")), ["TenantId", "tenantId", "tenant_id"]);
  } catch (_error) {
    return "";
  }
}

async function signIn() {
  const email = process.env.MOMENTUM_EMAIL || process.env.MOMENTUM_USERNAME;
  const password = process.env.MOMENTUM_PASSWORD;
  if (!email || !password) throw new Error("Momentum credentials are not configured on the server.");

  const response = await fetch(`${BASE_URL}/v1/signin`, {
    method: "POST",
    headers: { Accept: "*/*", "Content-Type": "application/json-patch+json" },
    body: JSON.stringify({ emailAddress: email, password })
  });
  if (!response.ok) throw new Error(`Momentum sign-in failed (${response.status}).`);
  const payload = await response.json();
  if (typeof payload === "string") return payload;
  const token = findFirst(payload, ["token", "jwt", "accessToken", "access_token", "idToken"]);
  if (!token) throw new Error("Momentum sign-in did not return a JWT.");
  return String(token);
}

function normalizeAsset(asset) {
  const location = findFirst(asset, ["location", "lastLocation", "position", "gps"]);
  const fleetStatus = findFirst(asset, ["fleetStatus"]);
  return {
    id: findFirst(asset, ["id", "assetId"]),
    unit: String(findFirst(asset, ["unit", "unitNumber", "vehicleNumber", "name", "displayName", "assetName"])),
    name: String(findFirst(asset, ["name", "displayName", "assetName"])),
    driver: String(findFirst(asset, ["driverName", "employeeName", "assignedEmployeeName"])),
    city: String(findFirst(asset, ["city", "lastCity"]) || (location && findFirst(location, ["city", "lastCity"]))),
    state: String(findFirst(asset, ["state", "lastState"]) || (location && findFirst(location, ["state", "lastState"]))),
    status: String(findFirst(asset, ["status", "operatingStatus", "ignitionStatus"]) || (fleetStatus && findFirst(fleetStatus, ["fleetStatusType", "status"]))),
    latitude: findFirst(asset, ["latitude", "lat"]) || (location && findFirst(location, ["latitude", "lat"])),
    longitude: findFirst(asset, ["longitude", "lng", "lon"]) || (location && findFirst(location, ["longitude", "lng", "lon"])),
    lastSeen: String(findFirst(asset, ["lastUpdatedDate", "lastUpdated", "lastReportDate", "lastEventDate", "updatedAt", "timestamp"]))
  };
}

function collection(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  for (const key of ["data", "items", "results", "assets", "value"]) {
    if (Array.isArray(payload[key])) return payload[key];
  }
  return [payload];
}

module.exports = async function handler(request, response) {
  if (request.method !== "GET") return response.status(405).json({ error: "Method not allowed" });

  try {
    const token = process.env.MOMENTUM_JWT || await signIn();
    const tenantId = process.env.MOMENTUM_TENANT_ID || tokenTenant(token);
    if (!tenantId) throw new Error("Momentum tenant ID is not configured or present in the JWT.");

    const assetsResponse = await fetch(`${BASE_URL}/v1/tenant/${encodeURIComponent(tenantId)}/asset`, {
      headers: { Authorization: `Bearer ${token}`, Accept: "application/json" }
    });
    if (!assetsResponse.ok) return response.status(502).json({ error: `Momentum asset request failed (${assetsResponse.status}).` });

    const payload = await assetsResponse.json();
    return response.status(200).json({ assets: collection(payload).filter((item) => item && typeof item === "object").map(normalizeAsset), fetchedAt: new Date().toISOString() });
  } catch (error) {
    return response.status(500).json({ error: error instanceof Error ? error.message : "Momentum integration failed." });
  }
}
