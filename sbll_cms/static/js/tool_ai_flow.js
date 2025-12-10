(() => {
  const escapeHtml = (value) => {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  };

  const defaultExtract = (item, field) => {
    const raw = item && field in item ? item[field] : [];
    if (!Array.isArray(raw)) return [];
    return raw
      .map((entry) => {
        if (typeof entry === "string") return entry.trim();
        if (entry && typeof entry === "object" && "content" in entry) {
          return String(entry.content || "").trim();
        }
        return "";
      })
      .filter(Boolean);
  };

  const collapseValues = (results, extractValues) =>
    (results || []).map((item) => ({
      ref: item.ref || "",
      values: extractValues(item),
    }));

  const collectSelections = (container) => {
    const nodes = Array.from(container.querySelectorAll(".ai-choice:checked"));
    return nodes
      .map((node) => ({
        ref: node.dataset.ref || "",
        value: node.value,
      }))
      .filter((item) => item.value && item.value.trim());
  };

  function initAiTool(config) {
    const {
      postUrl,
      resultField = "values",
      resultsContainer,
      messageContainer,
      generateButton,
      acceptAllButton,
      acceptSelectedButton,
      discardButton,
      getGeneratePayload,
      getMetaPayload = () => ({}),
      extractValues = (item) => defaultExtract(item, resultField),
      titleForResult = (item) => item.content || item.ref || "Result",
      emptyCopy = "No AI results yet.",
    } = config;

    if (!postUrl || !resultsContainer || !messageContainer || !generateButton) {
      return;
    }

    const state = { results: [] };
    const interactive = [generateButton, acceptAllButton, acceptSelectedButton, discardButton].filter(Boolean);

    const setBusy = (flag) => {
      interactive.forEach((el) => {
        el.disabled = Boolean(flag);
        if (flag) {
          el.classList.add("btn-disabled");
        } else {
          el.classList.remove("btn-disabled");
        }
      });
    };

    const showMessage = (text, tone = "info") => {
      if (!messageContainer) return;
      if (!text) {
        messageContainer.innerHTML = "";
        return;
      }
      const toneClass =
        tone === "error" ? "alert-error" : tone === "success" ? "alert-success" : "alert-info";
      messageContainer.innerHTML = `<div class="alert ${toneClass}">${escapeHtml(text)}</div>`;
    };

    const renderResults = () => {
      resultsContainer.innerHTML = "";
      if (!state.results.length) {
        resultsContainer.innerHTML = `<div class="alert">${escapeHtml(emptyCopy)}</div>`;
        return;
      }

      state.results.forEach((item) => {
        const card = document.createElement("div");
        card.className = "border rounded p-2 space-y-2";

        const title = document.createElement("div");
        title.className = "font-semibold";
        title.textContent = titleForResult(item);
        card.appendChild(title);

        if (item.error) {
          const err = document.createElement("div");
          err.className = "alert alert-error";
          err.textContent = item.error;
          card.appendChild(err);
        } else {
          const values = extractValues(item);
          if (!values.length) {
            const empty = document.createElement("div");
            empty.className = "text-sm text-base-content/70";
            empty.textContent = "No suggestions returned.";
            card.appendChild(empty);
          } else {
            const list = document.createElement("div");
            list.className = "space-y-1";
            values.forEach((val) => {
              const label = document.createElement("label");
              label.className = "flex items-center gap-2";

              const checkbox = document.createElement("input");
              checkbox.type = "checkbox";
              checkbox.className = "checkbox checkbox-sm ai-choice";
              checkbox.checked = true;
              checkbox.value = val;
              checkbox.dataset.ref = item.ref || "";

              const span = document.createElement("span");
              span.textContent = val;

              label.appendChild(checkbox);
              label.appendChild(span);
              list.appendChild(label);
            });
            card.appendChild(list);
          }
        }

        resultsContainer.appendChild(card);
      });
    };

    const postJson = async (payload) => {
      const response = await fetch(postUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      let data = {};
      try {
        data = await response.json();
      } catch (err) {
        throw new Error("Invalid server response");
      }
      if (!response.ok || data.ai_error || data.error) {
        const message = data.ai_error || data.error || response.statusText;
        throw new Error(message);
      }
      return data;
    };

    const handleGenerate = async () => {
      if (!getGeneratePayload) return;
      showMessage("");
      setBusy(true);
      try {
        const payload = {
          mode: "generate",
          ...getMetaPayload(),
          ...getGeneratePayload(),
        };
        const data = await postJson(payload);
        state.results = data.ai_results || data.results || [];
        renderResults();
        if (data.ai_message) {
          showMessage(data.ai_message, "success");
        } else {
          showMessage("Generated suggestions.", "info");
        }
      } catch (err) {
        showMessage(err.message, "error");
      } finally {
        setBusy(false);
      }
    };

    const handleAcceptAll = async () => {
      showMessage("");
      if (!state.results.length) {
        showMessage("No AI results to accept.", "error");
        return;
      }
      setBusy(true);
      try {
        const payload = {
          mode: "accept_all",
          ...getMetaPayload(),
          results: state.results,
        };
        const data = await postJson(payload);
        state.results = [];
        renderResults();
        const msg = data.ai_message || data.message || "Accepted.";
        showMessage(msg, "success");
        if (data.reload) {
          window.location.reload();
        }
      } catch (err) {
        showMessage(err.message, "error");
      } finally {
        setBusy(false);
      }
    };

    const handleAcceptSelection = async () => {
      showMessage("");
      const selections = collectSelections(resultsContainer);
      if (!selections.length) {
        showMessage("No selections made.", "error");
        return;
      }
      setBusy(true);
      try {
        const payload = {
          mode: "accept_selection",
          ...getMetaPayload(),
          selections,
        };
        const data = await postJson(payload);
        state.results = [];
        renderResults();
        const msg = data.ai_message || data.message || "Accepted.";
        showMessage(msg, "success");
        if (data.reload) {
          window.location.reload();
        }
      } catch (err) {
        showMessage(err.message, "error");
      } finally {
        setBusy(false);
      }
    };

    const handleDiscard = () => {
      state.results = [];
      renderResults();
      showMessage("Discarded.", "info");
    };

    generateButton.addEventListener("click", handleGenerate);
    acceptAllButton?.addEventListener("click", handleAcceptAll);
    acceptSelectedButton?.addEventListener("click", handleAcceptSelection);
    discardButton?.addEventListener("click", handleDiscard);

    renderResults();

    return {
      post: postJson,
      showMessage,
      clearResults: handleDiscard,
      getResults: () => state.results.slice(),
    };
  }

  window.initAiTool = initAiTool;
})();
