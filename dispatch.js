const TOOLS = [
  { id: "load1", label: "Load 1", url: "https://fleet.load1.com/vehicles", mode: "frame", description: "Load 1 fleet and dispatch workspace." },
  { id: "expeditus", label: "Expeditus", url: "https://www.fleet-vu.com", mode: "frame", description: "Expeditus fleet workspace." },
  { id: "whatsapp", label: "WhatsApp", url: "https://web.whatsapp.com/", mode: "external", description: "Open WhatsApp Web in a separate tab." },
  { id: "momentum", label: "Momentum IoT", url: "https://app.momentumiot.com/#/", mode: "momentum", description: "View live vehicle assets and open the full Momentum IoT dashboard." },
  { id: "try-hours", label: "Try Hours", url: "https://fleet-vision.com/ooindex.htm", mode: "external", description: "Open Fleet Vision / Try Hours in a separate tab." },
  { id: "settings", label: "Settings", mode: "settings", description: "Dispatch workspace settings." }
];

const navigation = document.getElementById("navigation");
const content = document.getElementById("page-content");
const title = document.getElementById("page-title");
const subtitle = document.getElementById("page-subtitle");

function renderNavigation() {
  navigation.innerHTML = "";
  TOOLS.forEach((tool) => {
    const button = document.createElement("button");
    button.className = "nav-button";
    button.type = "button";
    button.dataset.toolId = tool.id;
    button.textContent = tool.label;
    button.addEventListener("click", () => selectTool(tool.id));
    navigation.appendChild(button);
  });
}

function selectTool(toolId, updateUrl = true) {
  const tool = TOOLS.find((item) => item.id === toolId) || TOOLS[0];
  document.querySelectorAll(".nav-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.toolId === tool.id);
  });
  title.textContent = tool.label;
  subtitle.textContent = tool.description;
  content.innerHTML = "";

  if (tool.mode === "settings") {
    renderSettings();
  } else if (tool.mode === "momentum") {
    renderMomentum();
  } else {
    renderTool(tool);
  }
  if (updateUrl) history.replaceState({}, "", `?tool=${encodeURIComponent(tool.id)}`);
}

function renderMomentum() {
  const panel = document.createElement("section");
  panel.className = "tool-panel";
  panel.innerHTML = `
    <h2>Live Vehicle Assets</h2>
    <p>Vehicle data is requested securely through the server. Momentum credentials and JWTs are never sent to the browser.</p>
    <div class="tool-actions">
      <button class="button" type="button" id="refresh-assets">Refresh Vehicle Data</button>
      <a class="button secondary" href="https://app.momentumiot.com/#/" target="_blank" rel="noreferrer">Open Momentum IoT</a>
    </div>
    <div id="asset-status" class="notice">Click Refresh Vehicle Data to request the latest asset locations.</div>
    <div id="asset-table" class="asset-table-wrap"></div>
  `;
  content.appendChild(panel);
  panel.querySelector("#refresh-assets").addEventListener("click", loadMomentumAssets);
}

async function loadMomentumAssets() {
  const status = document.getElementById("asset-status");
  const table = document.getElementById("asset-table");
  const button = document.getElementById("refresh-assets");
  if (!status || !table || !button) return;
  button.disabled = true;
  status.className = "notice";
  status.textContent = "Loading vehicle data...";
  table.innerHTML = "";
  try {
    const response = await fetch("/api/momentum-assets", { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
    const assets = Array.isArray(payload.assets) ? payload.assets : [];
    status.textContent = `${assets.length} vehicle asset${assets.length === 1 ? "" : "s"} returned${payload.fetchedAt ? ` at ${new Date(payload.fetchedAt).toLocaleTimeString()}` : ""}.`;
    if (!assets.length) {
      table.innerHTML = `<div class="empty-state">Momentum connected, but no vehicle assets were returned.</div>`;
      return;
    }
    const rows = assets.map((asset) => `
      <tr>
        <td>${escapeHtml(asset.unit || asset.name || "Unknown")}</td>
        <td>${escapeHtml([asset.city, asset.state].filter(Boolean).join(", ") || "Unavailable")}</td>
        <td>${escapeHtml(asset.driver || "Unassigned")}</td>
        <td>${escapeHtml(asset.status || "Unavailable")}</td>
        <td>${escapeHtml(asset.lastSeen || "Unavailable")}</td>
      </tr>
    `).join("");
    table.innerHTML = `<table><thead><tr><th>Unit</th><th>Location</th><th>Driver</th><th>Status</th><th>Last seen</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (error) {
    status.className = "notice error";
    status.textContent = error.message || "Unable to load Momentum vehicle data.";
  } finally {
    button.disabled = false;
  }
}

function renderTool(tool) {
  const panel = document.createElement("section");
  panel.className = "tool-panel";
  panel.innerHTML = `<h2>${escapeHtml(tool.label)}</h2><p>${escapeHtml(tool.description)}</p>`;
  const actions = document.createElement("div");
  actions.className = "tool-actions";

  const open = document.createElement("a");
  open.className = "button";
  open.href = tool.url;
  open.target = "_blank";
  open.rel = "noreferrer";
  open.textContent = tool.mode === "external" ? `Open ${tool.label}` : "Open Site";
  actions.appendChild(open);

  const note = document.createElement("div");
  note.className = "notice";
  note.textContent = tool.mode === "external"
    ? `${tool.label} opens in a separate browser tab because its sign-in session or framing policy prevents reliable embedding.`
    : "Some sites block embedded frames. Use Open Site if the workspace is blank or asks you to sign in.";
  panel.append(actions, note);

  if (tool.mode === "frame") {
    const frame = document.createElement("iframe");
    frame.className = "embedded-frame";
    frame.src = tool.url;
    frame.title = `${tool.label} workspace`;
    frame.loading = "lazy";
    panel.appendChild(frame);
  }
  content.appendChild(panel);
}

function renderSettings() {
  const panel = document.createElement("section");
  panel.className = "tool-panel";
  panel.innerHTML = `
    <h2>Dispatch Workspace Settings</h2>
    <p>This Vercel workspace is the stable dispatch shell. External board credentials remain with each provider.</p>
    <div class="status-grid">
      <div class="status-card"><div class="status-label">Hosting</div><div class="status-value">Vercel</div></div>
      <div class="status-card"><div class="status-label">Workspace</div><div class="status-value">F&amp;C Packaging</div></div>
      <div class="status-card"><div class="status-label">Retired features</div><div class="status-value">Heat map / relocation</div></div>
    </div>
    <div class="notice">Use the individual provider windows for Load 1, Expeditus, WhatsApp, Momentum IoT, and Try Hours sign-in.</div>
  `;
  content.appendChild(panel);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[character]));
}

renderNavigation();
const requestedTool = new URLSearchParams(window.location.search).get("tool");
selectTool(requestedTool || "load1", false);
