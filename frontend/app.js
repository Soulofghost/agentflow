let workflows = [];
let activeWorkflow = null;
let currentExecutionId = null;
let pollInterval = null;

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    setupEventListeners();
    await loadWorkflows();
}

function setupEventListeners() {
    // Custom DAG Modal
    const modal = document.getElementById("custom-wf-modal");
    document.getElementById("btn-new-wf-modal").addEventListener("click", () => {
        // Pre-fill sample JSON
        document.getElementById("custom-dag-json").value = JSON.stringify({
            "nodes": [
                {"id": "planner", "role": "Architect Planner", "tool": "none", "dependencies": []},
                {"id": "researcher", "role": "Security Researcher", "tool": "search_mock", "dependencies": ["planner"]},
                {"id": "verifier", "role": "Verification Critic", "tool": "schema_validator", "dependencies": ["researcher"]}
            ]
        }, null, 2);
        modal.classList.add("open");
    });

    document.getElementById("btn-close-wf-modal").addEventListener("click", () => {
        modal.classList.remove("open");
    });
    document.getElementById("btn-cancel-wf").addEventListener("click", () => {
        modal.classList.remove("open");
    });

    // Custom WF Submission
    document.getElementById("custom-wf-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        await handleCustomWfSubmit();
    });

    // Dispatch Execution
    document.getElementById("btn-dispatch-exec").addEventListener("click", () => {
        dispatchExecution();
    });

    // Copy Artifact
    document.getElementById("btn-copy-artifact").addEventListener("click", () => {
        const text = document.getElementById("final-deliverable").textContent;
        navigator.clipboard.writeText(text);
        alert("Synthesized deliverable copied to clipboard.");
    });
}

async function loadWorkflows() {
    try {
        const res = await fetch("/api/v1/workflows");
        if (!res.ok) throw new Error("Failed to load workflows");
        workflows = await res.json();
        renderWorkflowList();
        document.getElementById("wf-count").textContent = workflows.length;

        if (workflows.length > 0 && !activeWorkflow) {
            selectWorkflow(workflows[0].id);
        }
    } catch (err) {
        console.error("Workflow load error:", err);
    }
}

function renderWorkflowList() {
    const list = document.getElementById("workflow-list");
    list.innerHTML = "";

    workflows.forEach(wf => {
        const card = document.createElement("div");
        card.className = `workflow-card ${activeWorkflow && activeWorkflow.id === wf.id ? 'active' : ''}`;
        card.innerHTML = `
            <div class="wf-card-title">${escapeHtml(wf.name)}</div>
            <div class="wf-card-desc">${escapeHtml(wf.description)}</div>
        `;
        card.addEventListener("click", () => {
            selectWorkflow(wf.id);
        });
        list.appendChild(card);
    });
}

function selectWorkflow(wfId) {
    const wf = workflows.find(w => w.id === wfId);
    if (!wf) return;

    activeWorkflow = wf;
    document.getElementById("active-wf-name").textContent = wf.name;
    document.getElementById("exec-status-tag").className = "exec-badge idle";
    document.getElementById("exec-status-tag").textContent = "IDLE";

    // Set default prompt if empty
    const promptInput = document.getElementById("task-prompt");
    if (!promptInput.value.trim()) {
        if (wf.id.includes("code")) {
            promptInput.value = "Analyze pull request #402 for SQL injection, insecure eval() calls, and secret leaks.";
        } else {
            promptInput.value = "Conduct technical literature review on Byzantine fault-tolerance thresholds in distributed networks.";
        }
    }

    renderWorkflowList();
    renderDagCanvas(wf.dag);
}

function renderDagCanvas(dag) {
    const svg = document.getElementById("dag-svg");
    svg.innerHTML = "";

    const nodes = dag.nodes || [];
    if (nodes.length === 0) return;

    const width = svg.clientWidth || 700;
    const height = svg.clientHeight || 450;

    // Calculate tiers using simple topological levels
    const nodeMap = {};
    nodes.forEach(n => nodeMap[n.id] = { ...n, tier: 0 });

    let changed = true;
    while (changed) {
        changed = false;
        nodes.forEach(n => {
            (n.dependencies || []).forEach(depId => {
                if (nodeMap[depId] && nodeMap[n.id].tier <= nodeMap[depId].tier) {
                    nodeMap[n.id].tier = nodeMap[depId].tier + 1;
                    changed = true;
                }
            });
        });
    }

    const tiers = {};
    Object.values(nodeMap).forEach(n => {
        tiers[n.tier] = tiers[n.tier] || [];
        tiers[n.tier].push(n);
    });

    const maxTier = Math.max(...Object.keys(tiers).map(Number));
    const tierWidth = (width - 160) / Math.max(1, maxTier);

    const positions = {};
    Object.entries(tiers).forEach(([tierStr, tierNodes]) => {
        const tier = Number(tierStr);
        const x = 80 + (tier * tierWidth);
        const stepY = height / (tierNodes.length + 1);

        tierNodes.forEach((node, idx) => {
            const y = stepY * (idx + 1);
            positions[node.id] = { x, y, node };
        });
    });

    // Draw directed edges
    nodes.forEach(n => {
        const targetPos = positions[n.id];
        (n.dependencies || []).forEach(depId => {
            const srcPos = positions[depId];
            if (srcPos && targetPos) {
                const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
                const dx = (targetPos.x - srcPos.x) / 2;
                const d = `M ${srcPos.x + 60} ${srcPos.y} C ${srcPos.x + 60 + dx} ${srcPos.y}, ${targetPos.x - 60 - dx} ${targetPos.y}, ${targetPos.x - 60} ${targetPos.y}`;
                path.setAttribute("d", d);
                path.setAttribute("fill", "none");
                path.setAttribute("stroke", "#374151");
                path.setAttribute("stroke-width", "2");
                path.setAttribute("stroke-dasharray", "4 4");
                svg.appendChild(path);
            }
        });
    });

    // Draw Nodes
    Object.values(positions).forEach(p => {
        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        g.id = `dag-node-${p.node.id}`;

        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", p.x - 60);
        rect.setAttribute("y", p.y - 28);
        rect.setAttribute("width", 120);
        rect.setAttribute("height", 56);
        rect.setAttribute("rx", 6);
        rect.setAttribute("fill", "#111827");
        rect.setAttribute("stroke", "#2e3b52");
        rect.setAttribute("stroke-width", "2");

        let roleColor = "#8b5cf6";
        if (p.node.role.includes("Critic") || p.node.role.includes("Verification")) roleColor = "#10b981";
        if (p.node.role.includes("Worker") || p.node.role.includes("Analyzer") || p.node.role.includes("Researcher")) roleColor = "#06b6d4";

        const topBar = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        topBar.setAttribute("x", p.x - 60);
        topBar.setAttribute("y", p.y - 28);
        topBar.setAttribute("width", 120);
        topBar.setAttribute("height", 4);
        topBar.setAttribute("fill", roleColor);

        const textId = document.createElementNS("http://www.w3.org/2000/svg", "text");
        textId.setAttribute("x", p.x);
        textId.setAttribute("y", p.y - 4);
        textId.setAttribute("fill", "#f3f4f6");
        textId.setAttribute("font-size", "11");
        textId.setAttribute("font-weight", "700");
        textId.setAttribute("font-family", "JetBrains Mono, monospace");
        textId.setAttribute("text-anchor", "middle");
        textId.textContent = p.node.id;

        const textRole = document.createElementNS("http://www.w3.org/2000/svg", "text");
        textRole.setAttribute("x", p.x);
        textRole.setAttribute("y", p.y + 14);
        textRole.setAttribute("fill", "#9ca3af");
        textRole.setAttribute("font-size", "9");
        textRole.setAttribute("font-family", "Plus Jakarta Sans, sans-serif");
        textRole.setAttribute("text-anchor", "middle");
        textRole.textContent = p.node.role.length > 18 ? p.node.role.substring(0, 16) + '..' : p.node.role;

        g.appendChild(rect);
        g.appendChild(topBar);
        g.appendChild(textId);
        g.appendChild(textRole);
        svg.appendChild(g);
    });
}

async function dispatchExecution() {
    if (!activeWorkflow) return;
    const prompt = document.getElementById("task-prompt").value.trim();
    if (!prompt) {
        alert("Please provide an execution prompt.");
        return;
    }

    const statusTag = document.getElementById("exec-status-tag");
    statusTag.className = "exec-badge running";
    statusTag.textContent = "RUNNING";

    document.getElementById("agent-log-stream").innerHTML = `<div style="padding:20px; text-align:center; color:var(--accent-purple-light); font-size:12px;">Coordinating agent swarm and initializing topological runner...</div>`;
    document.getElementById("final-deliverable").textContent = "Awaiting agent synthesis...";

    try {
        const res = await fetch("/api/v1/executions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                workflow_id: activeWorkflow.id,
                input_prompt: prompt
            })
        });

        if (!res.ok) throw new Error("Execution dispatch failed");
        const data = await res.json();
        currentExecutionId = data.execution_id;

        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(pollExecutionProgress, 400);

    } catch (err) {
        console.error("Execution error:", err);
        statusTag.className = "exec-badge failed";
        statusTag.textContent = "FAILED";
    }
}

async function pollExecutionProgress() {
    if (!currentExecutionId) return;

    try {
        const res = await fetch(`/api/v1/executions/${currentExecutionId}`);
        if (!res.ok) return;
        const data = await res.json();

        // Update Steps
        renderAgentLogs(data.steps || []);
        document.getElementById("step-counter").textContent = `${data.steps.length} Steps Completed`;

        // Highlight Active Nodes on Canvas
        data.steps.forEach(step => {
            const nodeEl = document.getElementById(`dag-node-${step.step_name}`);
            if (nodeEl) {
                const rect = nodeEl.querySelector("rect");
                if (rect) rect.setAttribute("stroke", "#10b981");
            }
        });

        if (data.status === "succeeded" || data.status === "failed") {
            clearInterval(pollInterval);
            pollInterval = null;

            const statusTag = document.getElementById("exec-status-tag");
            statusTag.className = `exec-badge ${data.status}`;
            statusTag.textContent = data.status.toUpperCase();

            if (data.final_output) {
                document.getElementById("final-deliverable").textContent = data.final_output;
            }
        }

    } catch (err) {
        console.error("Poll error:", err);
    }
}

function renderAgentLogs(steps) {
    const stream = document.getElementById("agent-log-stream");
    stream.innerHTML = "";

    steps.forEach(s => {
        const card = document.createElement("div");
        card.className = "log-step-card";
        
        let toolHtml = "";
        if (s.tool_calls_json) {
            try {
                const toolData = JSON.parse(s.tool_calls_json);
                toolHtml = `<span class="tool-badge">🔧 Tool: ${escapeHtml(toolData.tool || 'none')}</span>`;
            } catch (e) {}
        }

        card.innerHTML = `
            <div class="log-step-header">
                <span class="step-node">[${escapeHtml(s.step_name)}] • ${escapeHtml(s.agent_role)}</span>
                <span class="step-time">${s.duration_ms}ms</span>
            </div>
            ${toolHtml}
            <div class="step-artifact">${escapeHtml(s.output_artifact)}</div>
        `;
        stream.appendChild(card);
    });

    stream.scrollTop = stream.scrollHeight;
}

async function handleCustomWfSubmit() {
    const name = document.getElementById("custom-name").value.trim();
    const description = document.getElementById("custom-desc").value.trim();
    const jsonStr = document.getElementById("custom-dag-json").value.trim();

    try {
        const dag = JSON.parse(jsonStr);
        const res = await fetch("/api/v1/workflows", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, description, dag })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Validation error");
        }

        const created = await res.json();
        document.getElementById("custom-wf-modal").classList.remove("open");
        document.getElementById("custom-wf-form").reset();
        await loadWorkflows();
        selectWorkflow(created.id);

    } catch (err) {
        alert("Custom DAG Error: " + err.message);
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
