const TOOLS = [
  { id: "load1", label: "Load 1", url: "https://fleet.load1.com/vehicles", mode: "frame", description: "Load 1 fleet and dispatch workspace." },
  { id: "expeditus", label: "Expeditus", url: "https://www.fleet-vu.com", mode: "frame", description: "Expeditus fleet workspace." },
  { id: "whatsapp", label: "WhatsApp", url: "https://web.whatsapp.com/", mode: "external", description: "Open WhatsApp Web in a separate tab." },
  { id: "momentum", label: "Momentum IoT", url: "https://app.momentumiot.com/#/", mode: "external", description: "Open the authenticated Momentum IoT dashboard." },
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
  } else {
    renderTool(tool);
  }
  if (updateUrl) history.replaceState({}, "", `?tool=${encodeURIComponent(tool.id)}`);
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
