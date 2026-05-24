document.addEventListener("DOMContentLoaded", () => {
  // ── State ─────────────────────────────────────────────────────────────────
  let activeTab = "standard";
  let tabResults = {};  // per-tab last generated result

  const editState = {
    ai_prompt:     { editing: false, past: [], future: [], snapshot: null },
    system_prompt: { editing: false, past: [], future: [], snapshot: null },
  };

  // ── Global Synonyms (localStorage) ───────────────────────────────────────
  const STORAGE_KEY = "scriptletai_synonyms";

  function loadGlobalSynonyms() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch { return {}; }
  }

  function saveGlobalSynonyms(obj) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
  }

  function renderGlobalSynonymsList() {
    const container = document.getElementById("globalSynonymsList");
    if (!container) return;
    const synonyms = loadGlobalSynonyms();
    container.innerHTML = "";

    if (Object.keys(synonyms).length === 0) {
      container.innerHTML = '<p class="muted" style="margin:0 0 10px">No synonyms yet. Add words below.</p>';
    }

    Object.entries(synonyms).forEach(([word, variants]) => {
      const row = document.createElement("div");
      row.className = "global-syn-row";
      const varStr = Array.isArray(variants) ? variants.join(", ") : variants;
      row.innerHTML = `
        <input type="text" class="gsyn-word" value="${_esc(word)}" placeholder="Word / term" />
        <input type="text" class="gsyn-variants" value="${_esc(varStr)}" placeholder="Variants (comma separated)" />
        <button type="button" class="btn btn-danger btn-small" data-word="${_esc(word)}">✕</button>
      `;
      row.querySelector("button").addEventListener("click", () => {
        const syns = loadGlobalSynonyms();
        delete syns[word];
        saveGlobalSynonyms(syns);
        renderGlobalSynonymsList();
      });
      ["gsyn-word", "gsyn-variants"].forEach(cls => {
        row.querySelector("." + cls).addEventListener("change", () => {
          const newWord = row.querySelector(".gsyn-word").value.trim();
          const newVariants = row.querySelector(".gsyn-variants").value
            .split(",").map(s => s.trim()).filter(Boolean);
          if (!newWord) return;
          const syns = loadGlobalSynonyms();
          if (newWord !== word) delete syns[word];
          syns[newWord] = newVariants;
          saveGlobalSynonyms(syns);
        });
      });
      container.appendChild(row);
    });
  }

  function addGlobalSynonymRow() {
    const syns = loadGlobalSynonyms();
    syns[""] = [];
    // Don't save empty key — just add an empty row visually
    const container = document.getElementById("globalSynonymsList");
    const row = document.createElement("div");
    row.className = "global-syn-row";
    row.innerHTML = `
      <input type="text" class="gsyn-word" placeholder="Word / term" />
      <input type="text" class="gsyn-variants" placeholder="Variants (comma separated)" />
      <button type="button" class="btn btn-danger btn-small">✕</button>
    `;
    row.querySelector("button").addEventListener("click", () => row.remove());
    row.querySelector(".gsyn-word").addEventListener("change", () => {
      const word = row.querySelector(".gsyn-word").value.trim();
      const variants = row.querySelector(".gsyn-variants").value
        .split(",").map(s => s.trim()).filter(Boolean);
      if (word) {
        const syns2 = loadGlobalSynonyms();
        syns2[word] = variants;
        saveGlobalSynonyms(syns2);
      }
    });
    row.querySelector(".gsyn-variants").addEventListener("change", () => {
      const word = row.querySelector(".gsyn-word").value.trim();
      const variants = row.querySelector(".gsyn-variants").value
        .split(",").map(s => s.trim()).filter(Boolean);
      if (word) {
        const syns2 = loadGlobalSynonyms();
        syns2[word] = variants;
        saveGlobalSynonyms(syns2);
      }
    });
    container.appendChild(row);
    row.querySelector(".gsyn-word").focus();
  }

  function toggleSynonymsPanel() {
    const body = document.getElementById("synonymsPanelBody");
    const arrow = document.getElementById("synonymsPanelArrow");
    if (!body) return;
    const open = body.style.display !== "none";
    body.style.display = open ? "none" : "block";
    arrow.textContent = open ? "▶" : "▼";
    if (!open) renderGlobalSynonymsList();
  }

  // ── Tab management ────────────────────────────────────────────────────────
  const TABLE_TAB = "table_placeholder";
  const GROUPING_TAB = "grouping";
  const NON_TABLE_TABS = ["standard","title","metadata","section_number","drawing","multirow_tabular","ai_over_table"];

  function setActiveTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

    const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    const content = document.getElementById(`tab-${tabName}`);
    if (btn) btn.classList.add("active");
    if (content) content.classList.add("active");

    activeTab = tabName;

    // Show/hide hint note
    const hintSection = document.getElementById("hint_note_section");
    if (hintSection) hintSection.style.display = NON_TABLE_TABS.includes(tabName) ? "flex" : "none";

    // Show/hide generate/save row
    const genRow = document.getElementById("generateSaveRow");
    if (genRow) genRow.style.display = tabName === GROUPING_TAB ? "none" : "flex";

    // Swap between prompt input panel and grouping panel
    const inputPanel   = document.getElementById("promptInputPanel");
    const groupingPanel = document.getElementById("groupingPanel");
    if (tabName === GROUPING_TAB) {
      if (inputPanel)    inputPanel.style.display    = "none";
      if (groupingPanel) groupingPanel.style.display = "block";
    } else {
      if (inputPanel)    inputPanel.style.display    = "block";
      if (groupingPanel) groupingPanel.style.display = "none";
    }

    if (tabName === TABLE_TAB) refreshTableLivePreview();
    if (tabName === GROUPING_TAB) loadGroupingPlaceholders();

    // Restore per-tab result
    renderResult(tabResults[tabName] || null);
  }

  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
  });

  // ── Result rendering ──────────────────────────────────────────────────────
  function renderResult(data) {
    const isTable = data && data.prompt_type === TABLE_TAB;

    document.getElementById("meta_prompt_type").textContent = data ? data.prompt_type : "-";
    document.getElementById("meta_output_key").textContent  = data ? (data.output_key || "N/A") : "-";
    document.getElementById("meta_chunk_count").textContent = data ? (data.chunk_count || "-") : "-";

    document.getElementById("final_prompt_text").textContent = data ? (data.final_prompt_text || "") : "";
    document.getElementById("ai_prompt").textContent         = data ? (data.ai_prompt || "") : "";
    document.getElementById("system_prompt").textContent     = data ? (data.system_prompt || "") : "";
    document.getElementById("column_header_result").textContent  = data ? (data.column_header || "") : "";
    document.getElementById("filters_logic_result").textContent  = data ? (data.filters_logic || "") : "";
    document.getElementById("synonyms_logic_result").textContent = data ? (data.synonyms_logic || "") : "";
    document.getElementById("grouping_logic_result").textContent = data ? (data.grouping_logic || "") : "";

    // Show/hide sections based on type
    // When data is null, hide all three sections (fixes "wizard visible in every tab" bug)
    const showAiSystem = data && !isTable;
    document.getElementById("ai_prompt_section").style.display     = showAiSystem ? "block" : "none";
    document.getElementById("system_prompt_section").style.display = showAiSystem ? "block" : "none";
    document.getElementById("table_result_sections").style.display = isTable ? "block" : "none";

    // Validation
    const statusEl = document.getElementById("validation_status");
    const issuesEl = document.getElementById("validation_issues");
    if (!data) {
      statusEl.textContent = "Not generated";
      statusEl.className = "status-badge";
      issuesEl.innerHTML = "";
      return;
    }
    const status = data.validation?.status || "unknown";
    statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    statusEl.className = "status-badge" + (status !== "valid" ? " invalid" : "");
    issuesEl.innerHTML = "";
    (data.validation?.issues || []).forEach(issue => {
      const li = document.createElement("li");
      li.textContent = issue;
      issuesEl.appendChild(li);
    });

    // Reset edit state — called on new generate, just turn off editing mode
    ["ai_prompt", "system_prompt"].forEach(field => {
      const pre = document.getElementById(field);
      if (pre) pre.contentEditable = "false";
      _showEditButtons(field, false);
      editState[field].editing  = false;
      editState[field].snapshot = null;
      editState[field].past     = [];
      editState[field].future   = [];
    });
  }

  function rebuildFinalPromptText() {
    const data = tabResults[activeTab];
    if (!data) return;
    if (data.prompt_type !== TABLE_TAB) {
      const ai = document.getElementById("ai_prompt").textContent;
      const sys = document.getElementById("system_prompt").textContent;
      data.ai_prompt = ai;
      data.system_prompt = sys;
      data.final_prompt_text = `${ai}\n\n${sys}`;
      document.getElementById("final_prompt_text").textContent = data.final_prompt_text;
    }
  }

  // ── Edit / Undo / Redo (contenteditable on <pre>) ────────────────────────
  function _showEditButtons(field, editing) {
    const editBtn   = document.getElementById(`edit_${field}_btn`);
    const saveBtn   = document.getElementById(`save_${field}_btn`);
    const cancelBtn = document.getElementById(`cancel_${field}_btn`);
    if (editBtn)   editBtn.style.display   = editing ? "none"         : "inline-block";
    if (saveBtn)   saveBtn.style.display   = editing ? "inline-block" : "none";
    if (cancelBtn) cancelBtn.style.display = editing ? "inline-block" : "none";
  }

  function enterEditPrompt(field) {
    const state = editState[field];
    if (state.editing) return;
    const pre = document.getElementById(field);
    if (!pre) return;
    state.snapshot = pre.textContent;   // save original for cancel
    pre.contentEditable = "true";
    pre.focus();
    // move cursor to end
    const range = document.createRange();
    range.selectNodeContents(pre);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    _showEditButtons(field, true);
    state.editing = true;
  }

  function savePromptEdit(field) {
    const state = editState[field];
    if (!state.editing) return;
    const pre    = document.getElementById(field);
    const newVal = pre.innerText;   // innerText gives plain text even after contenteditable edits
    const oldVal = state.snapshot;
    if (newVal !== oldVal) {
      state.past.push(oldVal);
      state.future = [];
    }
    pre.textContent    = newVal;    // normalise back to plain text (strips any inserted HTML)
    pre.contentEditable = "false";
    _showEditButtons(field, false);
    state.editing  = false;
    state.snapshot = null;
    rebuildFinalPromptText();
  }

  function cancelEdit(field) {
    const state = editState[field];
    const pre   = document.getElementById(field);
    if (pre) {
      if (state.snapshot !== null && state.snapshot !== undefined) {
        pre.textContent = state.snapshot;
      }
      pre.contentEditable = "false";
    }
    _showEditButtons(field, false);
    state.editing  = false;
    state.snapshot = null;
  }

  function undoPrompt(field) {
    const state = editState[field];
    if (state.past.length === 0) return;
    const pre = document.getElementById(field);
    state.future.push(pre.textContent);
    pre.textContent = state.past.pop();
    rebuildFinalPromptText();
  }

  function redoPrompt(field) {
    const state = editState[field];
    if (state.future.length === 0) return;
    const pre = document.getElementById(field);
    state.past.push(pre.textContent);
    pre.textContent = state.future.pop();
    rebuildFinalPromptText();
  }

  // ── Table Synonym Rows ────────────────────────────────────────────────────
  function addSynonymRow(left = "", right = "") {
    const container = document.getElementById("synonymRows");
    if (!container) return;

    const row = document.createElement("div");
    row.className = "synonym-row";
    row.innerHTML = `
      <input type="text" class="syn-left" placeholder="Primary term" value="${_esc(left)}">
      <input type="text" class="syn-right" placeholder="Variant term" value="${_esc(right)}">
      <button type="button" class="btn btn-danger btn-small">✕</button>
    `;
    row.querySelector("button").addEventListener("click", () => { row.remove(); refreshTableLivePreview(); });
    row.querySelectorAll("input").forEach(inp => inp.addEventListener("input", refreshTableLivePreview));
    container.appendChild(row);
    refreshTableLivePreview();
  }

  function getSynonymRows() {
    const rows = [];
    document.querySelectorAll("#synonymRows .synonym-row").forEach(row => {
      const left  = row.querySelector(".syn-left")?.value.trim()  || "";
      const right = row.querySelector(".syn-right")?.value.trim() || "";
      if (left || right) rows.push({ left, right });
    });
    return rows;
  }

  function buildSynonymsCsvFromRows() {
    return getSynonymRows()
      .map(r => r.right ? `${r.left} | ${r.right}` : r.left)
      .filter(Boolean)
      .join(",");
  }

  // ── Live Table Preview ────────────────────────────────────────────────────
  function buildLiveFilterString() {
    const filterColumn       = document.getElementById("filter_column")?.value.trim() || "";
    const filterValueRaw     = document.getElementById("filter_value")?.value.trim() || "";
    const tableHeader        = document.getElementById("table_header")?.value.trim() || "";
    const excludeTableHeader = document.getElementById("exclude_table_header")?.value.trim() || "";
    const useWildcard        = document.getElementById("use_wildcard_match")?.checked || false;
    const useNotEquals       = document.getElementById("use_not_equals")?.checked || false;

    let filterValue = filterValueRaw;
    if (useWildcard && filterValue && !filterValue.includes("*")) filterValue = `*${filterValue}*`;

    const operator = useNotEquals ? "!=" : "=";
    const parts = [];
    if (filterColumn && filterValue) parts.push(`"${filterColumn}"${operator}"${filterValue}"`);
    if (tableHeader)        parts.push(`"table_header"="${tableHeader}"`);
    if (excludeTableHeader) parts.push(`"table_header" != "${excludeTableHeader}"`);

    if (parts.length === 0)  return "<filters> () </filters>";
    if (parts.length <= 2)   return `<filters> (${parts.join(" | ")}) </filters>`;
    return `<filters> (${parts[0]} | ${parts[1]} and ${parts[2]}) </filters>`;
  }

  function buildLiveXmlPreviewText() {
    const columnHeader = document.getElementById("column_header")?.value.trim() || "";
    const grouping     = document.getElementById("grouping_placeholders_csv")?.value.trim() || "";
    const synonymRows  = getSynonymRows();
    const parts = [];

    if (grouping) parts.push(`@grouping=[${grouping}]`);
    parts.push(`<column_header> "${columnHeader}" </column_header>`);
    parts.push(buildLiveFilterString());

    if (synonymRows.length > 0) {
      parts.push("<synonyms>");
      synonymRows.forEach(r => {
        if (r.left && r.right) parts.push(`  <synonym> "${r.left}" | "${r.right}" </synonym>`);
        else if (r.left)       parts.push(`  <synonym> "${r.left}" </synonym>`);
        else if (r.right)      parts.push(`  <synonym> "${r.right}" </synonym>`);
      });
      parts.push("</synonyms>");
    }
    return parts.join("\n");
  }

  function refreshTableLivePreview() {
    const fp = document.getElementById("liveFilterPreview");
    const xp = document.getElementById("liveXmlPreview");
    if (fp) fp.textContent = buildLiveFilterString();
    if (xp) xp.textContent = buildLiveXmlPreviewText();
  }

  function registerTablePreviewListeners() {
    ["column_header","filter_column","filter_value","table_header",
     "exclude_table_header","grouping_placeholders_csv","use_wildcard_match","use_not_equals"]
      .forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.addEventListener("input",  refreshTableLivePreview);
          el.addEventListener("change", refreshTableLivePreview);
        }
      });
  }

  // ── Payload builder ───────────────────────────────────────────────────────
  function commonBase() {
    return {
      prompt_type: activeTab,
      placeholder_name: document.getElementById("placeholder_name")?.value || "",
      document_types: (document.getElementById("document_types")?.value || "")
        .split(",").map(x => x.trim()).filter(Boolean),
      hint_note: document.getElementById("hint_note")?.value.trim() || null,
      global_synonyms: JSON.stringify(loadGlobalSynonyms()) || null,
    };
  }

  function getPayload() {
    const base = commonBase();

    if (activeTab === "standard") return {
      ...base,
      requirement_text: document.getElementById("requirement_text_standard")?.value || "",
      expected_json_key: document.getElementById("expected_json_key_standard")?.value || "answer",
      chunk_count: Number(document.getElementById("chunk_count_standard")?.value || 8),
    };

    if (activeTab === "title") return {
      ...base,
      requirement_text: document.getElementById("requirement_text_title")?.value || "Extract the title of the document",
      expected_json_key: document.getElementById("expected_json_key_title")?.value || "title",
      chunk_count: Number(document.getElementById("chunk_count_title")?.value || 3),
    };

    if (activeTab === "metadata") return {
      ...base,
      requirement_text: document.getElementById("requirement_text_metadata")?.value || "",
      expected_json_key: document.getElementById("expected_json_key_metadata")?.value || "answer",
      chunk_count: Number(document.getElementById("chunk_count_metadata")?.value || 8),
    };

    if (activeTab === "section_number") return {
      ...base,
      requirement_text: document.getElementById("requirement_text_section")?.value || "",
      expected_json_key: document.getElementById("expected_json_key_section")?.value || "answer",
      chunk_count: Number(document.getElementById("chunk_count_section")?.value || 8),
    };

    if (activeTab === "drawing") return {
      ...base,
      requirement_text: document.getElementById("requirement_text_drawing")?.value || "",
      drawing_target_field: document.getElementById("drawing_target_field")?.value || "",
      expected_json_key: document.getElementById("expected_json_key_drawing")?.value || "answer",
      use_metadata_tag: true,  // always true for drawing
      chunk_count: Number(document.getElementById("chunk_count_drawing")?.value || 8),
    };

    if (activeTab === "multirow_tabular") return {
      ...base,
      requirement_text: document.getElementById("requirement_text_multirow")?.value || "",
      expected_json_key: document.getElementById("expected_json_key_multirow")?.value || "answer",
      chunk_count: Number(document.getElementById("chunk_count_multirow")?.value || 8),
    };

    if (activeTab === "ai_over_table") return {
      ...base,
      requirement_text: document.getElementById("requirement_text_ai_table")?.value || "",
      table_target_instruction: document.getElementById("table_target_instruction")?.value || "",
      expected_json_key: document.getElementById("expected_json_key_ai_table")?.value || "answer",
      chunk_count: Number(document.getElementById("chunk_count_ai_table")?.value || 8),
    };

    if (activeTab === TABLE_TAB) return {
      ...base,
      column_header: document.getElementById("column_header")?.value || "",
      filter_column: document.getElementById("filter_column")?.value || "",
      filter_value: document.getElementById("filter_value")?.value || "",
      table_header: document.getElementById("table_header")?.value || "",
      exclude_table_header: document.getElementById("exclude_table_header")?.value || null,
      synonyms_csv: buildSynonymsCsvFromRows() || null,
      grouping_placeholders_csv: document.getElementById("grouping_placeholders_csv")?.value || null,
      use_wildcard_match: document.getElementById("use_wildcard_match")?.checked || false,
      use_not_equals: document.getElementById("use_not_equals")?.checked || false,
      chunk_count: 0,
    };

    return base;
  }

  // ── Generate / Save ───────────────────────────────────────────────────────
  async function generatePrompt() {
    try {
      const payload = getPayload();
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const rawText = await response.text();
      if (!response.ok) throw new Error(`Server error ${response.status}: ${rawText}`);

      let data;
      try { data = JSON.parse(rawText); }
      catch { throw new Error(`Invalid JSON from server: ${rawText}`); }

      data.requirement_text = payload.requirement_text || null;
      data.document_types   = payload.document_types;

      tabResults[activeTab] = data;
      renderResult(data);

    } catch (err) {
      console.error("Generate failed:", err);
      alert("Generate Prompt failed.\n\n" + err.message);
    }
  }

  async function savePrompt() {
    const data = tabResults[activeTab];
    if (!data) { alert("Generate a prompt first."); return; }

    try {
      const payload = {
        prompt_type: data.prompt_type,
        placeholder_name: data.placeholder_name,
        requirement_text: data.requirement_text,
        extraction_family: data.extraction_family,
        output_key: data.output_key,
        special_tags: data.special_tags || [],
        document_types: data.document_types || [],
        chunk_count: data.chunk_count,
        ai_prompt: data.ai_prompt,
        system_prompt: data.system_prompt,
        column_header: data.column_header,
        filters_logic: data.filters_logic,
        synonyms_logic: data.synonyms_logic,
        grouping_logic: data.grouping_logic,
        final_prompt_text: data.final_prompt_text,
        validation_status: data.validation.status,
        validation_issues: data.validation.issues || [],
      };

      const response = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const rawText = await response.text();
      if (!response.ok) throw new Error(`Server error ${response.status}: ${rawText}`);

      const result = JSON.parse(rawText);
      alert(`Saved with ID ${result.id}`);

    } catch (err) {
      console.error("Save failed:", err);
      alert("Save Prompt failed.\n\n" + err.message);
    }
  }

  // ── Grouping Tab ──────────────────────────────────────────────────────────
  let groupingRecords = [];
  let groupingSelected = new Set();

  async function loadGroupingPlaceholders() {
    const container = document.getElementById("groupingContent");
    if (!container) return;

    container.innerHTML = `
      <p class="muted" style="margin:0 0 12px">
        Select 2 or more <strong>##</strong> placeholder records saved in the database, then click <strong>Group Selected</strong>.
        Grouping writes <code>@grouping=[…]</code> into each selected record's prompt.
      </p>
      <input class="search-bar" id="grouping_search" placeholder="Search by placeholder name..." oninput="filterGroupingList()" />
      <div id="grouping_list" style="max-height:420px;overflow-y:auto"><p class="muted">Loading…</p></div>
      <div class="action-row" style="margin-top:14px">
        <button class="btn btn-primary" onclick="applyGrouping()">Group Selected</button>
        <button class="btn btn-secondary" onclick="removeGroupingFromSelected()">Remove Grouping</button>
        <button class="btn btn-secondary btn-small" onclick="clearGroupingSelection()">Clear Selection</button>
        <button class="btn btn-secondary btn-small" onclick="importFromExcel()" title="Import ## placeholders from Excel data file">⬆ Import from Excel</button>
      </div>
      <div id="grouping_status" class="muted" style="margin-top:10px"></div>
    `;

    try {
      const resp = await fetch("/api/prompts/table-placeholders");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      groupingRecords = await resp.json();
      groupingSelected.clear();
      renderGroupingList("");
    } catch (err) {
      const listEl = document.getElementById("grouping_list");
      if (listEl) listEl.innerHTML = `<p style="color:#cb4e4e">Failed to load records: ${err.message}</p>`;
    }
  }

  function renderGroupingList(filter) {
    const listEl = document.getElementById("grouping_list");
    if (!listEl) return;

    const q = (filter || "").toLowerCase();
    const filtered = q
      ? groupingRecords.filter(r => r.placeholder_name.toLowerCase().includes(q) || (r.prompt_type || "").toLowerCase().includes(q))
      : groupingRecords;

    if (filtered.length === 0) {
      listEl.innerHTML = '<p class="muted">No ## placeholders found in the database. Save some table placeholder prompts first.</p>';
      return;
    }

    listEl.innerHTML = "";
    filtered.forEach(record => {
      const item = document.createElement("div");
      item.className = "ph-item" + (groupingSelected.has(record.id) ? " selected" : "");
      item.dataset.id = record.id;

      const grouped = record.grouping_logic ? `<span class="ph-grouped">grouped</span>` : "";
      item.innerHTML = `
        <input type="checkbox" ${groupingSelected.has(record.id) ? "checked" : ""} />
        <div style="flex:1">
          <div class="ph-name">${_esc(record.placeholder_name)}</div>
          <div class="ph-meta">${_esc(record.prompt_type)} · ID ${record.id}</div>
          ${record.grouping_logic ? `<div class="ph-meta" style="margin-top:3px;color:#24914b">${_esc(record.grouping_logic)}</div>` : ""}
        </div>
        ${grouped}
      `;

      const toggle = () => {
        if (groupingSelected.has(record.id)) {
          groupingSelected.delete(record.id);
          item.classList.remove("selected");
          item.querySelector("input[type=checkbox]").checked = false;
        } else {
          groupingSelected.add(record.id);
          item.classList.add("selected");
          item.querySelector("input[type=checkbox]").checked = true;
        }
      };

      // Expand/collapse final_prompt_text
      const detailsDiv = document.createElement("div");
      detailsDiv.className = "ph-details";
      detailsDiv.style.cssText = "display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--border-soft);width:100%";
      const promptText = record.final_prompt_text || "";
      detailsDiv.innerHTML = `
        <pre style="margin:0;font-size:12px;max-height:200px;overflow:auto;background:#f7f9fb;border:1px solid var(--border-soft);border-radius:8px;padding:10px">${_esc(promptText)}</pre>
        <button type="button" class="btn btn-secondary btn-small" style="margin-top:6px" onclick="navigator.clipboard.writeText(${JSON.stringify(promptText)}).then(()=>this.textContent='Copied!').catch(()=>alert('Copy failed'))">Copy Prompt</button>
      `;

      const viewBtn = document.createElement("button");
      viewBtn.type = "button";
      viewBtn.className = "btn btn-secondary btn-small";
      viewBtn.style.cssText = "margin-left:auto;flex-shrink:0;align-self:center";
      viewBtn.textContent = "▶ Prompt";
      viewBtn.addEventListener("click", e => {
        e.stopPropagation();
        const open = detailsDiv.style.display !== "none";
        detailsDiv.style.display = open ? "none" : "block";
        viewBtn.textContent = open ? "▶ Prompt" : "▼ Prompt";
      });

      // Wrap item content in a flex row so viewBtn floats right
      const mainRow = document.createElement("div");
      mainRow.style.cssText = "display:flex;align-items:flex-start;gap:12px;width:100%";
      // Move existing inner content to mainRow
      const checkboxEl = item.querySelector("input[type=checkbox]");
      const innerDiv = item.querySelector("div[style]");
      const groupedSpan = item.querySelector(".ph-grouped");
      mainRow.appendChild(checkboxEl);
      mainRow.appendChild(innerDiv);
      if (groupedSpan) mainRow.appendChild(groupedSpan);
      mainRow.appendChild(viewBtn);

      item.innerHTML = "";
      item.style.flexDirection = "column";
      item.style.alignItems = "stretch";
      item.appendChild(mainRow);
      item.appendChild(detailsDiv);

      mainRow.addEventListener("click", e => {
        if (e.target.tagName !== "INPUT" && e.target.tagName !== "BUTTON") toggle();
      });
      mainRow.querySelector("input[type=checkbox]").addEventListener("change", toggle);
      listEl.appendChild(item);
    });
  }

  function filterGroupingList() {
    const q = document.getElementById("grouping_search")?.value || "";
    renderGroupingList(q);
  }

  function clearGroupingSelection() {
    groupingSelected.clear();
    renderGroupingList(document.getElementById("grouping_search")?.value || "");
  }

  async function applyGrouping() {
    if (groupingSelected.size < 2) {
      alert("Select at least 2 placeholders to group.");
      return;
    }
    const ids = Array.from(groupingSelected);
    try {
      const resp = await fetch("/api/prompts/apply-grouping", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ placeholder_ids: ids }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Apply failed");

      const statusEl = document.getElementById("grouping_status");
      if (statusEl) statusEl.textContent = `✔ ${data.message}`;
      await loadGroupingPlaceholders();

    } catch (err) {
      alert("Apply grouping failed: " + err.message);
    }
  }

  async function removeGroupingFromSelected() {
    if (groupingSelected.size === 0) { alert("Select at least one placeholder."); return; }
    const ids = Array.from(groupingSelected);
    let removed = 0;
    for (const id of ids) {
      try {
        const resp = await fetch(`/api/prompts/${id}/grouping`, { method: "DELETE" });
        if (resp.ok) removed++;
      } catch {}
    }
    const statusEl = document.getElementById("grouping_status");
    if (statusEl) statusEl.textContent = `✔ Grouping removed from ${removed} record(s)`;
    await loadGroupingPlaceholders();
  }

  async function importFromExcel() {
    const statusEl = document.getElementById("grouping_status");
    if (statusEl) statusEl.textContent = "⏳ Importing from Excel…";
    try {
      const resp = await fetch("/api/import-excel", { method: "POST" });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Import failed");
      if (statusEl) statusEl.textContent = `✔ ${data.message}`;
      await loadGroupingPlaceholders();
    } catch (err) {
      if (statusEl) statusEl.textContent = "";
      alert("Import failed: " + err.message);
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function _esc(str) {
    return String(str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }

  // ── Expose to HTML onclick ────────────────────────────────────────────────
  window.generatePrompt             = generatePrompt;
  window.savePrompt                 = savePrompt;
  window.addSynonymRow              = addSynonymRow;
  window.addGlobalSynonymRow        = addGlobalSynonymRow;
  window.toggleSynonymsPanel        = toggleSynonymsPanel;
  window.enterEditPrompt            = enterEditPrompt;
  window.savePromptEdit             = savePromptEdit;
  window.cancelEdit                 = cancelEdit;
  window.undoPrompt                 = undoPrompt;
  window.redoPrompt                 = redoPrompt;
  window.filterGroupingList         = filterGroupingList;
  window.applyGrouping              = applyGrouping;
  window.clearGroupingSelection     = clearGroupingSelection;
  window.removeGroupingFromSelected = removeGroupingFromSelected;
  window.importFromExcel            = importFromExcel;

  // ── Init ──────────────────────────────────────────────────────────────────
  registerTablePreviewListeners();
  addSynonymRow("Signal type", "Signal_type");
  addSynonymRow("Analog input", "Analog inputs");
  refreshTableLivePreview();
  setActiveTab("standard");
});
