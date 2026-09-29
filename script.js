(() => {
  "use strict";

  const root = document.documentElement;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const motionButton = document.getElementById("motion-toggle");
  const pauseListeners = new Set();
  let motionPaused = reducedMotion.matches;

  function setMotionPaused(paused) {
    motionPaused = paused;
    root.classList.toggle("motion-paused", paused);
    if (motionButton) {
      motionButton.setAttribute("aria-pressed", String(paused));
      motionButton.setAttribute("aria-label", paused ? "Enable animations" : "Pause animations");
      motionButton.title = paused ? "Enable animations" : "Pause animations";
      motionButton.querySelector("span").textContent = paused ? "▷" : "Ⅱ";
    }
    if (paused) pauseListeners.forEach((pause) => pause());
  }

  function revealControls(container) {
    container.querySelectorAll(".js-control").forEach((control) => {
      control.hidden = false;
    });
  }

  function selectButton(buttons, selected, attribute) {
    buttons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.getAttribute(attribute) === selected));
    });
  }

  setMotionPaused(motionPaused);
  if (motionButton) {
    motionButton.addEventListener("click", () => setMotionPaused(!motionPaused));
    motionButton.hidden = false;
  }
  reducedMotion.addEventListener("change", (event) => setMotionPaused(event.matches));
  document.addEventListener("visibilitychange", () => {
    root.classList.toggle("page-hidden", document.hidden);
    if (document.hidden) pauseListeners.forEach((pause) => pause());
  });

  function initializeNavigation() {
    const menu = document.getElementById("menu-toggle");
    const navigation = document.getElementById("navigation");
    if (!menu || !navigation) return;
    const mobileLayout = window.matchMedia("(max-width: 760px)");

    function closeMenu(restoreFocus = false) {
      document.body.classList.remove("menu-open");
      menu.setAttribute("aria-expanded", "false");
      navigation.hidden = mobileLayout.matches;
      if (restoreFocus && mobileLayout.matches) menu.focus();
    }

    function updateLayout() {
      menu.hidden = !mobileLayout.matches;
      closeMenu();
    }

    menu.addEventListener("click", () => {
      const expanded = menu.getAttribute("aria-expanded") === "true";
      menu.setAttribute("aria-expanded", String(!expanded));
      document.body.classList.toggle("menu-open", !expanded);
      navigation.hidden = expanded;
    });
    navigation.addEventListener("click", (event) => {
      const link = event.target.closest("a");
      if (!link || !mobileLayout.matches) return;
      closeMenu();
      if (link.hash && link.origin === location.origin && link.pathname === location.pathname) {
        const destination = document.getElementById(link.hash.slice(1));
        if (destination) {
          destination.setAttribute("tabindex", "-1");
          destination.focus({ preventScroll: true });
          destination.addEventListener("blur", () => destination.removeAttribute("tabindex"), { once: true });
        }
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && menu.getAttribute("aria-expanded") === "true") closeMenu(true);
    });
    document.addEventListener("click", (event) => {
      if (mobileLayout.matches && !event.target.closest(".nav-wrap")) closeMenu();
    });
    mobileLayout.addEventListener("change", updateLayout);
    updateLayout();
  }

  function initializeScene() {
    const panel = document.getElementById("scene-panel");
    if (!panel) return;
    const buttons = [...panel.querySelectorAll("[data-view]")];
    const status = document.getElementById("scene-status");
    const explanation = document.getElementById("scene-explanation");
    const description = document.getElementById("scene-description");
    const observerDescription = "Observer at the origin with identity rotation. Chair 01 stays at (−1, 2, 0), table 02 stays at (1, 2, 0). ";
    if (!buttons.length || !status || !explanation || !description) return;

    buttons.forEach((button) => button.addEventListener("click", () => {
      const local = button.dataset.view === "local";
      panel.classList.toggle("is-local", local);
      selectButton(buttons, button.dataset.view, "data-view");
      status.textContent = local ? "Unobserved ≠ absent" : "Geometry-backed";
      explanation.textContent = local
        ? "Chair 01 is outside this illustrative local observation. Its location and ID stay fixed, but the local expert cannot infer absence from missing evidence."
        : "The chair is left of the observer. Its stable ID and transformed coordinates support the relation.";
      description.textContent = observerDescription + (local
        ? "The chair is not observed locally, so its evidence is unknown. The question mark marks missing evidence, not an empty location. This is a conceptual illustration."
        : "Global geometry contains both objects, and chair 01 is to the observer’s left. This is a conceptual illustration.");
    }));
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => panel.classList.toggle("is-offscreen", !entry.isIntersecting));
      });
      observer.observe(panel);
    }
    revealControls(panel);
  }

  function initializeController() {
    const controller = document.getElementById("controller");
    if (!controller) return;
    const play = document.getElementById("controller-play");
    const next = document.getElementById("controller-next");
    const reset = document.getElementById("controller-reset");
    const title = document.getElementById("stage-title");
    const description = document.getElementById("stage-description");
    const roundText = document.getElementById("round-text");
    const candidateSet = document.getElementById("candidate-set");
    const decision = document.getElementById("decision-label");
    const setExplanation = document.getElementById("set-explanation");
    const budget = document.getElementById("controller-budget");
    const status = document.getElementById("controller-status");
    const caseButtons = [...controller.querySelectorAll("[data-case]")];
    const stages = [...controller.querySelectorAll("[data-stage]")];
    const roundDots = [...controller.querySelectorAll(".round-dots i")];
    if (![play, next, reset, title, description, roundText, candidateSet, decision, setExplanation].every(Boolean)) return;
    const cases = {
      answer: { name: "Answer now", sets: [["chair"]] },
      acquire: { name: "Look again", sets: [["chair", "table"], ["chair"]] },
      abstain: { name: "Stay uncertain", sets: [["chair", "Other"], ["Other"], ["Other"]] },
    };
    const stageNames = ["Manager", "Experts", "Critic", "Alignment", "Conformal set"];
    let activeCase = "answer";
    let step = 0;
    let timer = null;
    let playing = false;
    let visible = true;

    function stopPlayback() {
      window.clearTimeout(timer);
      timer = null;
      playing = false;
      play.textContent = "Play walkthrough ▷";
      play.setAttribute("aria-pressed", "false");
    }

    function currentNarrative(round, stage) {
      if (stage === 0) return round === 0
        ? ["Frame a grounded question.", "The manager asks what is to the observer’s left, fixes the shared coordinate frame and object IDs, and plans complementary evidence checks. The extra-observation budget is two."]
        : ["Acquire another observation.", `The previous set did not justify an ordinary singleton answer. The manager uses extra observation ${round} of 2, supplying new evidence to both experts while keeping the frame and candidate identities fixed.`];
      if (stage === 1) return ["Two perspectives inspect one scene.", round === 0
        ? "The egocentric expert inspects locally observed evidence; the global expert reasons over scene geometry. An object missing from one view remains unknown to that expert, not proven absent."
        : "Both experts update their evidence using the additional observation. More evidence may resolve the ambiguity, but it does not guarantee a supported answer."];
      if (stage === 2) return ["Check what the evidence supports.", "The critic checks typed geometric evidence, coordinate transforms and object identities. Unsupported claims are revised before scores are combined; agreement alone is not enough."];
      if (stage === 3) return ["Make the scores comparable.", "Temperatures fitted on development scenes align the experts’ score scales before fusion over shared candidates and Other. Temperatures stay fixed here. No numerical confidence scores are invented for this illustration."];
      const candidates = cases[activeCase].sets[round];
      if (candidates.length === 1 && candidates[0] !== "Other") return ["A single supported answer.", `The calibrated set contains only “${candidates[0]}”, an ordinary candidate. The controller accepts it and stops after ${round} extra ${round === 1 ? "observation" : "observations"}.`];
      if (round === 2) return ["The budget ends; uncertainty remains.", "The set still contains Other, which represents an answer omitted from the ordinary candidate list. The controller abstains after two extra observations. A singleton Other is never an answer."];
      return activeCase === "acquire"
        ? ["Two candidates are still plausible.", "The set contains chair and table. Multiple candidates do not justify an answer, so the controller requests another observation. An empty set would also require acquisition while budget remains."]
        : ["A residual label keeps the case open.", "Other means the true answer may be missing from the candidate list. Even a singleton Other cannot be accepted. The controller requests another observation while budget remains; empty sets follow the same rule."];
    }

    function render(announce = true) {
      const round = Math.floor(step / 5);
      const stage = step % 5;
      const terminal = step === cases[activeCase].sets.length * 5 - 1;
      const narrative = currentNarrative(round, stage);
      title.textContent = narrative[0];
      description.textContent = narrative[1];
      roundText.textContent = round === 0 ? "INITIAL OBSERVATION · ROUND 0" : `EXTRA OBSERVATION ${round} · ROUND ${round}`;
      if (budget) budget.textContent = `Used ${round} / 2 extra observations`;
      roundDots.forEach((dot, index) => dot.classList.toggle("active", index <= round));
      stages.forEach((element, index) => {
        element.classList.toggle("is-active", index === stage);
        element.classList.toggle("is-complete", index < stage);
        if (index === stage) element.setAttribute("aria-current", "step");
        else element.removeAttribute("aria-current");
      });
      candidateSet.replaceChildren();
      const computed = stage === 4;
      const candidates = computed ? cases[activeCase].sets[round] : [];
      if (computed) {
        candidates.forEach((candidate) => {
          const label = document.createElement("span");
          label.textContent = candidate;
          label.classList.toggle("residual", candidate === "Other");
          candidateSet.append(label);
        });
      } else {
        const placeholder = document.createElement("span");
        placeholder.className = "placeholder";
        placeholder.textContent = "Not formed yet";
        candidateSet.append(placeholder);
      }
      const accepts = computed && candidates.length === 1 && candidates[0] !== "Other";
      const abstains = computed && !accepts && round === 2;
      decision.className = `decision-label ${accepts ? "answer" : abstains ? "abstain" : "pending"}`;
      decision.textContent = accepts ? "Accept answer" : abstains ? "Abstain" : computed ? "Acquire more evidence" : "Checking evidence";
      setExplanation.textContent = accepts
        ? "One ordinary label. No unresolved residual category."
        : abstains
          ? "Budget exhausted. Other or an empty or multi-label set cannot be automatically answered."
          : computed
            ? `No ordinary singleton. ${2 - round} extra ${2 - round === 1 ? "observation remains" : "observations remain"}.`
            : "The set is formed after evidence checks and score alignment, using a held-out calibration threshold.";
      next.textContent = terminal ? "Restart steps ↺" : "Next step →";
      if (status && announce) status.textContent = `${cases[activeCase].name}. Round ${round}. ${stageNames[stage]}. ${narrative[0]} ${decision.textContent}. Used ${round} of 2 extra observations.`;
      if (terminal) stopPlayback();
    }

    function scheduleStep() {
      window.clearTimeout(timer);
      if (!playing || document.hidden || !visible) return;
      timer = window.setTimeout(() => {
        step += 1;
        render();
        if (playing) scheduleStep();
      }, 3400);
    }

    caseButtons.forEach((button) => button.addEventListener("click", () => {
      if (!cases[button.dataset.case]) return;
      stopPlayback();
      activeCase = button.dataset.case;
      step = 0;
      selectButton(caseButtons, activeCase, "data-case");
      render();
    }));
    play.addEventListener("click", () => {
      if (playing) {
        stopPlayback();
        return;
      }
      if (step === cases[activeCase].sets.length * 5 - 1) {
        step = 0;
        render();
      }
      if (motionPaused) setMotionPaused(false);
      playing = true;
      play.textContent = "Pause walkthrough Ⅱ";
      play.setAttribute("aria-pressed", "true");
      scheduleStep();
    });
    next.addEventListener("click", () => {
      stopPlayback();
      step = (step + 1) % (cases[activeCase].sets.length * 5);
      render();
    });
    reset.addEventListener("click", () => {
      stopPlayback();
      step = 0;
      render();
    });
    pauseListeners.add(stopPlayback);
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          visible = entry.isIntersecting;
          controller.classList.toggle("is-offscreen", !visible);
          if (!visible) stopPlayback();
        });
      });
      observer.observe(controller);
    }
    play.setAttribute("aria-pressed", "false");
    render(false);
    revealControls(controller);
  }

  function initializeResults() {
    const data = window.TAME3D_RESULTS;
    const workbench = document.querySelector(".results-workbench");
    const metricNames = ["answer", "selective", "coverage", "joint_error"];
    const methods = ["Conformal fixed (0)", "Conformal fixed (2)", "Adaptive aligned"];
    if (!data || !data.conditions || !workbench) return;
    const available = ["test", "shift"].every((condition) => methods.every((method) => {
      const result = data.conditions[condition] && data.conditions[condition][method];
      return result && [...metricNames, "views"].every((metric) => {
        const value = result.metrics && result.metrics[metric];
        return value && Number.isFinite(value.mean) && Number.isFinite(value.std);
      });
    }));
    if (!available) return;
    const conditionButtons = [...workbench.querySelectorAll("[data-condition]")];
    const methodButtons = [...workbench.querySelectorAll("[data-method]")];
    let condition = "test";
    let method = "Adaptive aligned";

    function update(announce = true) {
      const result = data.conditions[condition][method];
      const metrics = result.metrics;
      const conditionName = condition === "test" ? "Clean" : "Shifted";
      const resultName = `${result.display_name} · ${conditionName}`;
      const summary = [];
      selectButton(conditionButtons, condition, "data-condition");
      selectButton(methodButtons, method, "data-method");
      document.getElementById("selected-result").textContent = resultName;
      metricNames.forEach((metric) => {
        const row = workbench.querySelector(`[data-metric="${metric}"]`);
        const value = metrics[metric];
        const label = data.metrics[metric].label;
        row.querySelector(".metric-number").textContent = `${value.mean.toFixed(2)}%`;
        row.querySelector(".metric-sd").textContent = `± ${value.std.toFixed(2)}`;
        row.querySelector(".metric-fill").style.width = `${Math.min(100, Math.max(0, value.mean))}%`;
        const track = row.querySelector(".metric-track");
        track.setAttribute("role", "img");
        track.setAttribute("aria-label", `${label}: ${value.mean.toFixed(2)} percent, sample standard deviation ${value.std.toFixed(2)} percentage points, on a fixed zero to 100 percent scale.`);
        summary.push(`${label} ${value.mean.toFixed(2)} percent, SD ${value.std.toFixed(2)}`);
      });
      document.getElementById("cost-value").textContent = metrics.views.mean.toFixed(2);
      document.getElementById("cost-sd").textContent = `± ${metrics.views.std.toFixed(2)}`;
      document.getElementById("cost-fill").style.width = `${Math.min(100, Math.max(0, 50 * metrics.views.mean))}%`;
      const costTrack = workbench.querySelector(".acquisition-track");
      costTrack.setAttribute("role", "img");
      costTrack.setAttribute("aria-label", `${metrics.views.mean.toFixed(2)} extra observations per question, sample standard deviation ${metrics.views.std.toFixed(2)}, on a fixed zero to two scale.`);
      const fixedCost = data.conditions[condition]["Conformal fixed (2)"].metrics.views.mean;
      const savings = 100 * (1 - metrics.views.mean / fixedCost);
      document.getElementById("cost-highlight").textContent = method === "Adaptive aligned"
        ? `${savings.toFixed(2)}% fewer`
        : method === "Conformal fixed (0)" ? "No extra observations" : "Full acquisition budget";
      document.getElementById("cost-comparison").textContent = method === "Adaptive aligned"
        ? "extra acquisitions than Fixed (2), with a lower answer rate."
        : method === "Conformal fixed (0)"
          ? "Only the initial observation is used; unresolved cases are abstained from immediately."
          : "Two extra observations are always acquired before the final fixed-round decision.";
      document.getElementById("condition-note").textContent = condition === "test"
        ? "Original observation model; temperatures and thresholds fitted on separate development and calibration scenes."
        : "Sparser, noisier observations. Clean-data temperatures and thresholds remain fixed; the exchangeability guarantee need not hold under this shift.";
      document.getElementById("result-caveat").textContent = "Adaptive inference uses α/3 per round; each fixed rule uses α at one round. This comparison changes both stopping and risk allocation.";
      const marker = workbench.querySelector(".target-marker");
      if (marker) marker.title = condition === "test" ? "Nominal clean-distribution target: 90%" : "Clean-calibration reference: 90%. Not a guaranteed target under observation shift.";
      if (announce) document.getElementById("result-status").textContent = `${resultName}. Mean and sample SD across five seeds. ${summary.join(". ")}. Extra observations ${metrics.views.mean.toFixed(2)}, SD ${metrics.views.std.toFixed(2)}.`;
    }

    conditionButtons.forEach((button) => button.addEventListener("click", () => {
      condition = button.dataset.condition;
      update();
    }));
    methodButtons.forEach((button) => button.addEventListener("click", () => {
      method = button.dataset.method;
      update();
    }));
    update(false);
    revealControls(workbench);
  }

  function initializeFigures() {
    const dialog = document.getElementById("figure-dialog");
    const image = document.getElementById("dialog-image");
    const closeButton = document.getElementById("close-figure");
    if (!dialog || !image || !closeButton || typeof dialog.showModal !== "function") return;
    let opener = null;

    document.querySelectorAll("[data-zoom]").forEach((link) => link.addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const original = link.querySelector("img");
      if (!original) return;
      event.preventDefault();
      opener = link;
      image.src = link.href;
      image.alt = original.alt;
      image.width = original.width;
      image.height = original.height;
      document.getElementById("figure-dialog-title").textContent = link.dataset.zoom === "shift" ? "Original observation-shift figure" : "Original method figure";
      document.getElementById("original-image-link").href = link.href;
      dialog.showModal();
      closeButton.focus();
    }));
    closeButton.addEventListener("click", () => dialog.close());
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      dialog.close();
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        const bounds = dialog.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
      }
    });
    dialog.addEventListener("close", () => {
      if (opener && opener.isConnected) opener.focus({ preventScroll: true });
    });
  }

  function initializeCitation() {
    const button = document.getElementById("copy-citation");
    const citation = document.getElementById("citation-text");
    const status = document.getElementById("copy-status");
    if (!button || !citation || !status) return;
    button.addEventListener("click", async () => {
      const content = citation.textContent.trim();
      try {
        if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(content);
        status.textContent = "BibTeX citation copied.";
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(citation);
        citation.parentElement.focus();
        selection.removeAllRanges();
        selection.addRange(range);
        let copied = false;
        try {
          copied = document.execCommand("copy");
        } catch {
          copied = false;
        }
        status.textContent = copied
          ? "BibTeX citation copied."
          : "Automatic copy is unavailable. The citation is selected: press Ctrl+C or Command+C, or download the BibTeX file.";
        if (copied) button.focus();
      }
    });
    button.hidden = false;
  }

  initializeNavigation();
  initializeScene();
  initializeController();
  initializeResults();
  initializeFigures();
  initializeCitation();
})();
