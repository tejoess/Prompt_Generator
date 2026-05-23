document.addEventListener("DOMContentLoaded", () => {
  let lastGenerated = null;
  let activeTab = "standard";

  function setActiveTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach((btn) => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((content) => content.classList.remove("active"));

    const activeBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    const activeContent = document.getElementById(`tab-${tabName}`);

    if (activeBtn) activeBtn.classList.add("active");
    if (activeContent) activeContent.classList.add("active");

    activeTab = tabName;

    if (activeTab === "table_placeholder") {
      refreshTableLivePreview();
    }
  }

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabName = btn.dataset.tab;
      setActiveTab(tabName);
    });
  });

  function commonBase() {
    return {
      prompt_type: activeTab,
      placeholder_name: document.getElementById("placeholder_name")?.value || "",
      document_types: (document.getElementById("document_types")?.value || "")
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
    };
  }

  function addSynonymRow(left = "", right = "") {
    const container = document.getElementById("synonymRows");
    if (!container) return;

    const row = document.createElement("div");
    row.className = "synonym-row";

    row.innerHTML = `
      <input type="text" class="syn-left" placeholder="Primary term" value="${left}">
      <input type="text" class="syn-right" placeholder="Variant term" value="${right}">
      <button type="button" class="btn btn-danger btn-small">Remove</button>
    `;

    const removeBtn = row.querySelector("button");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        row.remove();
        refreshTableLivePreview();
      });
    }

    row.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("input", refreshTableLivePreview);
    });

    container.appendChild(row);
    refreshTableLivePreview();
  }

  function getSynonymRows() {
    const rows = [];
    document.querySelectorAll("#synonymRows .synonym-row").forEach((row) => {
      const left = row.querySelector(".syn-left")?.value.trim() || "";
      const right = row.querySelector(".syn-right")?.value.trim() || "";
      if (left || right) {
        rows.push({ left, right });
      }
    });
    return rows;
  }

  function buildSynonymsCsvFromRows() {
    return getSynonymRows()
      .map((r) => (r.right ? `${r.left} | ${r.right}` : `${r.left}`))
      .filter(Boolean)
      .join(",");
  }

  function buildLiveFilterString() {
    const filterColumn = document.getElementById("filter_column")?.value.trim() || "";
    const filterValueRaw = document.getElementById("filter_value")?.value.trim() || "";
    const tableHeader = document.getElementById("table_header")?.value.trim() || "";
    const excludeTableHeader = document.getElementById("exclude_table_header")?.value.trim() || "";
    const useWildcard = document.getElementById("use_wildcard_match")?.checked || false;
    const useNotEquals = document.getElementById("use_not_equals")?.checked || false;

    let filterValue = filterValueRaw;
    if (useWildcard && filterValue && !filterValue.includes("*")) {
      filterValue = `*${filterValue}*`;
    }

    const operator = useNotEquals ? "!=" : "=";
    const parts = [];

    if (filterColumn && filterValue) {
      parts.push(`"${filterColumn}"${operator}"${filterValue}"`);
    }

    if (tableHeader) {
      parts.push(`"table_header"="${tableHeader}"`);
    }

    if (excludeTableHeader) {
      parts.push(`"table_header" != "${excludeTableHeader}"`);
    }

    if (parts.length === 0) return "<filters> () </filters>";
    if (parts.length <= 2) return `<filters> (${parts.join(" | ")}) </filters>`;
    return `<filters> (${parts[0]} | ${parts[1]} and ${parts[2]}) </filters>`;
  }

  function buildLiveXmlPreviewText() {
    const columnHeader = document.getElementById("column_header")?.value.trim() || "";
    const grouping = document.getElementById("grouping_placeholders_csv")?.value.trim() || "";
    const synonymRows = getSynonymRows();

    const parts = [];

    if (grouping) {
      parts.push(`@grouping=[${grouping}]`);
    }

    parts.push(`<column_header> "${columnHeader}" </column_header>`);
    parts.push(buildLiveFilterString());

    if (synonymRows.length > 0) {
      parts.push("<synonyms>");
      synonymRows.forEach((r) => {
        if (r.left && r.right) {
          parts.push(`  <synonym> "${r.left}" | "${r.right}" </synonym>`);
        } else if (r.left) {
          parts.push(`  <synonym> "${r.left}" </synonym>`);
        } else if (r.right) {
          parts.push(`  <synonym> "${r.right}" </synonym>`);
        }
      });
      parts.push("</synonyms>");
    }

    return parts.join("\n");
  }

  function refreshTableLivePreview() {
    const filterPreview = document.getElementById("liveFilterPreview");
    const xmlPreview = document.getElementById("liveXmlPreview");

    if (!filterPreview || !xmlPreview) return;

    filterPreview.textContent = buildLiveFilterString();
    xmlPreview.textContent = buildLiveXmlPreviewText();
  }

  function registerTablePreviewListeners() {
    [
      "column_header",
      "filter_column",
      "filter_value",
      "table_header",
      "exclude_table_header",
      "grouping_placeholders_csv",
      "use_wildcard_match",
      "use_not_equals",
    ].forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener("input", refreshTableLivePreview);
        el.addEventListener("change", refreshTableLivePreview);
      }
    });
  }

  function getPayload() {
    const base = commonBase();

    if (activeTab === "standard") {
      return {
        ...base,
        requirement_text: document.getElementById("requirement_text_standard")?.value || "",
        expected_json_key: document.getElementById("expected_json_key_standard")?.value || "answer",
        chunk_count: Number(document.getElementById("chunk_count_standard")?.value || 8),
      };
    }

    if (activeTab === "title") {
      return {
        ...base,
        requirement_text: document.getElementById("requirement_text_title")?.value || "Extract the title of the document",
        expected_json_key: document.getElementById("expected_json_key_title")?.value || "title",
        chunk_count: Number(document.getElementById("chunk_count_title")?.value || 3),
      };
    }

    if (activeTab === "metadata") {
      return {
        ...base,
        requirement_text: document.getElementById("requirement_text_metadata")?.value || "",
        expected_json_key: document.getElementById("expected_json_key_metadata")?.value || "answer",
        chunk_count: Number(document.getElementById("chunk_count_metadata")?.value || 8),
      };
    }

    if (activeTab === "section_number") {
      return {
        ...base,
        requirement_text: document.getElementById("requirement_text_section")?.value || "",
        expected_json_key: document.getElementById("expected_json_key_section")?.value || "answer",
        chunk_count: Number(document.getElementById("chunk_count_section")?.value || 8),
      };
    }

    if (activeTab === "drawing") {
      return {
        ...base,
        requirement_text: document.getElementById("requirement_text_drawing")?.value || "",
        drawing_target_field: document.getElementById("drawing_target_field")?.value || "",
        expected_json_key: document.getElementById("expected_json_key_drawing")?.value || "answer",
        use_metadata_tag: document.getElementById("use_metadata_tag_drawing")?.checked || false,
        chunk_count: Number(document.getElementById("chunk_count_drawing")?.value || 8),
      };
    }

    if (activeTab === "multirow_tabular") {
      return {
        ...base,
        requirement_text: document.getElementById("requirement_text_multirow")?.value || "",
        expected_json_key: document.getElementById("expected_json_key_multirow")?.value || "answer",
        chunk_count: Number(document.getElementById("chunk_count_multirow")?.value || 8),
      };
    }

    if (activeTab === "ai_over_table") {
      return {
        ...base,
        requirement_text: document.getElementById("requirement_text_ai_table")?.value || "",
        table_target_instruction: document.getElementById("table_target_instruction")?.value || "",
        expected_json_key: document.getElementById("expected_json_key_ai_table")?.value || "answer",
        chunk_count: Number(document.getElementById("chunk_count_ai_table")?.value || 8),
      };
    }

    if (activeTab === "table_placeholder") {
      return {
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
    }

    return base;
  }

  async function generatePrompt() {
    try {
      const payload = getPayload();
      console.log("Generating prompt with payload:", payload);

      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const rawText = await response.text();
      console.log("Raw /api/generate response:", rawText);

      if (!response.ok) {
        throw new Error(`Server error ${response.status}: ${rawText}`);
      }

      let data;
      try {
        data = JSON.parse(rawText);
      } catch (err) {
        throw new Error(`Invalid JSON returned from server: ${rawText}`);
      }

      lastGenerated = {
        ...data,
        requirement_text: payload.requirement_text || null,
        document_types: payload.document_types,
      };

      document.getElementById("meta_prompt_type").textContent = data.prompt_type || "-";
      document.getElementById("meta_output_key").textContent = data.output_key || "N/A";
      document.getElementById("meta_chunk_count").textContent = data.chunk_count || "-";

      document.getElementById("final_prompt_text").textContent = data.final_prompt_text || "";
      document.getElementById("ai_prompt").textContent = data.ai_prompt || "";
      document.getElementById("system_prompt").textContent = data.system_prompt || "";
      document.getElementById("column_header_result").textContent = data.column_header || "";
      document.getElementById("filters_logic_result").textContent = data.filters_logic || "";
      document.getElementById("synonyms_logic_result").textContent = data.synonyms_logic || "";
      document.getElementById("grouping_logic_result").textContent = data.grouping_logic || "";

      const statusEl = document.getElementById("validation_status");
      const issuesEl = document.getElementById("validation_issues");
      const status = data.validation?.status || "unknown";

      statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
      statusEl.className = "status-badge" + (status !== "valid" ? " invalid" : "");

      issuesEl.innerHTML = "";
      (data.validation?.issues || []).forEach((issue) => {
        const li = document.createElement("li");
        li.textContent = issue;
        issuesEl.appendChild(li);
      });
    } catch (error) {
      console.error("Generate prompt failed:", error);
      alert("Generate Prompt failed.\n\n" + error.message);
    }
  }

  async function savePrompt() {
    try {
      if (!lastGenerated) {
        alert("Generate a prompt first.");
        return;
      }

      const payload = {
        prompt_type: lastGenerated.prompt_type,
        placeholder_name: lastGenerated.placeholder_name,
        requirement_text: lastGenerated.requirement_text,
        extraction_family: lastGenerated.extraction_family,
        output_key: lastGenerated.output_key,
        special_tags: lastGenerated.special_tags || [],
        document_types: lastGenerated.document_types || [],
        chunk_count: lastGenerated.chunk_count,
        ai_prompt: lastGenerated.ai_prompt,
        system_prompt: lastGenerated.system_prompt,
        column_header: lastGenerated.column_header,
        filters_logic: lastGenerated.filters_logic,
        synonyms_logic: lastGenerated.synonyms_logic,
        grouping_logic: lastGenerated.grouping_logic,
        final_prompt_text: lastGenerated.final_prompt_text,
        validation_status: lastGenerated.validation.status,
        validation_issues: lastGenerated.validation.issues || [],
      };

      console.log("Saving prompt with payload:", payload);

      const response = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const rawText = await response.text();
      console.log("Raw /api/save response:", rawText);

      if (!response.ok) {
        throw new Error(`Server error ${response.status}: ${rawText}`);
      }

      let data;
      try {
        data = JSON.parse(rawText);
      } catch (err) {
        throw new Error(`Invalid JSON returned from server: ${rawText}`);
      }

      alert(`Saved with ID ${data.id}`);
    } catch (error) {
      console.error("Save prompt failed:", error);
      alert("Save Prompt failed.\n\n" + error.message);
    }
  }

  window.generatePrompt = generatePrompt;
  window.savePrompt = savePrompt;
  window.addSynonymRow = addSynonymRow;

  registerTablePreviewListeners();
  addSynonymRow("Signal type", "Signal_type");
  addSynonymRow("Analog input", "Analog inputs");
  refreshTableLivePreview();

  const initialTab = document.querySelector(".tab-btn.active")?.dataset.tab || "standard";
  setActiveTab(initialTab);
});