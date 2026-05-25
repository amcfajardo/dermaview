const defaultProcedures = [
  {
    id: "general-skin-assessment",
    name: "General Skin Assessment",
    description:
      "Upload a skin image and get educational treatment suggestions based on visible image signals.",

    category: "Assessment",

    details: [
      "Checks basic image brightness, redness, contrast, and texture patterns",
      "Suggests possible procedure categories for consultation",
      "Helps patients decide which treatment preview to explore next",
      "Designed for education, not diagnosis",
      "Best used with a clear, well-lit photo"
    ],

    info:
      "DermaView uses client-side image processing heuristics to suggest treatments that may be worth discussing with a licensed dermatologist."
  },

  {
    id: "co2-fractional-laser-dermapen",
    name: "CO₂ Fractional Laser + Dermapen",
    description:
      "A minimally invasive skin resurfacing treatment that improves acne scars, skin texture, and facial clarity.",

    category: "Skin Resurfacing",

    details: [
      "Improves acne scars and uneven texture",
      "Stimulates collagen production",
      "Enhances skin clarity and smoothness",
      "Minimally invasive with visible results",
      "Popular for facial rejuvenation"
    ],

    info:
      "DermaView simulates realistic skin texture improvements and post-treatment clarity using image processing visualization."
  },

  {
    id: "face_slimming",
    name: "Face Slimming",

    description:
      "A contour-enhancing treatment designed to improve facial definition and slimming effects.",

    category: "Facial Contouring",

    details: [
      "Enhances jawline definition",
      "Improves facial contour symmetry",
      "Creates a slimmer facial appearance",
      "Minimally invasive procedure",
      "Ideal for contour visualization"
    ],

    info:
      "DermaView previews potential contour and slimming effects on the patient's own facial structure."
  },

  {
    id: "diamond-peel-facial",
    name: "Diamond Peel With Facial",

    description:
      "A non-invasive exfoliation treatment that brightens skin and improves facial smoothness.",

    category: "Facial Treatment",

    details: [
      "Removes dead skin cells",
      "Brightens dull complexion",
      "Improves facial smoothness",
      "Enhances skin clarity",
      "Gentle and non-invasive"
    ],

    info:
      "DermaView simulates smoother texture, reduced dullness, and improved skin radiance after treatment."
  },

  {
    id: "undereye-lip-filler",
    name: "Undereye and Lip Filler Procedure",

    description:
      "A minimally invasive enhancement procedure targeting undereye hollowness and lip volume.",

    category: "Filler Enhancement",

    details: [
      "Reduces appearance of eye bags",
      "Enhances lip fullness",
      "Improves facial balance",
      "Restores youthful appearance",
      "Provides natural-looking enhancement"
    ],

    info:
      "DermaView visualizes filler enhancement effects such as volume restoration and facial symmetry adjustments."
  },

  {
    id: "pico-carbon-laser",
    name: "PICO Carbon Laser Facial Procedure",

    description:
      "A laser facial treatment that targets acne, pores, blemishes, and uneven skin texture.",

    category: "Laser Facial",

    details: [
      "Targets acne and blemishes",
      "Refines enlarged pores",
      "Improves skin texture",
      "Brightens overall complexion",
      "Non-invasive laser technology"
    ],

    info:
      "DermaView simulates smoother skin, reduced blemishes, and refined pores for treatment visualization."
  },

  {
    id: "lip-chin-jawtox",
    name: "Lip Filler, Chin Filler, and Jawtox",

    description:
      "A combination facial contouring procedure using fillers and jawtox enhancements.",

    category: "Advanced Contouring",

    details: [
      "Enhances chin projection",
      "Defines jawline contour",
      "Improves facial harmony",
      "Adds lip volume and symmetry",
      "Visible contour enhancement"
    ],

    info:
      "DermaView projects contour adjustments and volume enhancement before treatment consultation."
  }
];

let procedures = defaultProcedures.slice();

const app = document.getElementById("app");
let selectedProcedureId = null;
let uploadedImageUrl = null;
let uploadedImageFile = null;
let processedImageUrl = null;
let assessmentResult = null;
let isProcessing = false;
let showResults = false;
let isSavingAnalysis = false;
let analysisSaveMessage = "";
let lastSavedRecordId = null;

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

function getClinicName() {
  const settings = window.DermaViewBranding?.loadSettings?.() || {};
  return (settings.clinicName || "DermaView").trim() || "DermaView";
}

const procedureIdByName = {
  "General Skin Assessment": "general-skin-assessment",
  "CO2 Fractional Laser + Dermapen": "co2-fractional-laser-dermapen",
  "CO₂ Fractional Laser + Dermapen": "co2-fractional-laser-dermapen",
  "Face Slimming Package": "face_slimming",
  "Face Slimming": "face_slimming",
  "Diamond Peel with Facial": "diamond-peel-facial",
  "Diamond Peel With Facial": "diamond-peel-facial",
  "Undereye and Lip Filler": "undereye-lip-filler",
  "Undereye and Lip Filler Procedure": "undereye-lip-filler",
  "PICO Carbon Laser Facial": "pico-carbon-laser",
  "PICO Carbon Laser Facial Procedure": "pico-carbon-laser",
  "Lip Filler, Chin Filler, and Jawtox": "lip-chin-jawtox"
};

const processableProcedureIds = new Set([
  "general-skin-assessment",
  "co2-fractional-laser-dermapen",
  "face_slimming",
  "diamond-peel-facial",
  "undereye-lip-filler",
  "pico-carbon-laser",
  "lip-chin-jawtox"
]);

function slugifyProcedureName(name, id) {
  const slug = String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || `procedure-${id}`;
}

function splitProcedureText(value) {
  return String(value || "")
    .split(/\r?\n|;|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeDatabaseProcedure(row) {
  const name = row.procedure_name || row.name || "";
  const id = procedureIdByName[name] || slugifyProcedureName(name, row.id);
  const details = [
    ...splitProcedureText(row.benefits),
    row.session_duration ? `Estimated duration: ${row.session_duration}` : "",
    row.recommended_sessions ? `Recommended sessions: ${row.recommended_sessions}` : ""
  ].filter(Boolean);

  return {
    id,
    databaseId: row.id,
    name,
    description: row.short_description || row.description || "",
    category: row.category || "Procedure",
    details: details.length ? details : ["Review this procedure with clinic staff before treatment."],
    info: row.full_description || row.short_description || "",
    preparation: row.preparation_guidelines || "",
    aftercare: row.aftercare_instructions || "",
    supportsProcessing: processableProcedureIds.has(id)
  };
}

function getProceduresEndpoint() {
  return window.location.pathname.includes("/pages/")
    ? "../admin_pages/admin-procedures.php"
    : "admin_pages/admin-procedures.php";
}

async function loadProceduresFromDatabase() {
  const formData = new FormData();
  formData.append("action", "fetch_public");

  try {
    const response = await fetch(getProceduresEndpoint(), {
      method: "POST",
      body: formData
    });
    const data = await response.json();

    if (data.status === "ok" && Array.isArray(data.procedures) && data.procedures.length) {
      procedures = data.procedures.map(normalizeDatabaseProcedure);
    }
  } catch (error) {
    procedures = defaultProcedures.slice();
  }
}

function getCurrentRoute() {
  const hash = window.location.hash.slice(1) || "home";
  return hash;
}

function findProcedureById(id) {
  return procedures.find((item) => item.id === id) || null;
}

function render() {
  const route = getCurrentRoute();
  const parts = route.split("/");
  const page = parts[0];
  const arg = parts[1] || null;

  if (page === "procedures") {
    renderProcedures();
  } else if (page === "treatment" && arg) {
    renderTreatment(arg);
  } else if (page === "schedule" && arg) {
    renderSchedule(arg);
  } else {
    renderHome();
  }
}

function renderHome() {
  const featuredProcedures = procedures.slice(0, 6);

  app.innerHTML = `
    <section class="hero home-hero">
      <div class="hero-grid">
        <div class="hero-copy-block">
          <p class="status-badge">Professional Dermatology Platform</p>
          <h1 class="hero-headline">Professional Dermatology Image Analysis</h1>
          <p class="hero-copy">Leverage advanced image processing technology to visualize and analyze skin conditions with precision.</p>
          <p class="hero-copy">DermaView helps clinicians and patients understand treatment outcomes through sophisticated image analysis.</p>
          <div class="cta-row">
            <a href="pages/procedures.html" class="button">Get Started</a>
            <a href="pages/procedures.html" class="button-secondary">Browse Procedures</a>
          </div>
        </div>
        <div class="features-grid">
          <div class="feature-card">
            <h3>Advanced Analysis</h3>
            <p>State-of-the-art image processing algorithms for detailed skin analysis.</p>
          </div>
          <div class="feature-card">
            <h3>Treatment Visualization</h3>
            <p>Visualize potential treatment outcomes with interactive before/after comparisons.</p>
          </div>
          <div class="feature-card">
            <h3>Educational Content</h3>
            <p>Comprehensive information about procedures and treatment options.</p>
          </div>
          <div class="feature-card">
            <h3>Clinical Grade</h3>
            <p>Professional-grade tools designed for medical professionals and clinics.</p>
          </div>
        </div>
      </div>
    </section>
    <section class="home-section">
      <div class="home-section-header">
        <span class="section-kicker">Procedures</span>
        <h2 class="section-heading">Explore treatment previews</h2>
        <p class="section-text">Choose a dermatology procedure and use DermaView to support patient education and treatment planning.</p>
      </div>
      <div class="procedure-preview-grid">
        ${featuredProcedures
          .map(
            (procedure) => `
              <a class="procedure-preview-card" href="pages/treatment.html#${procedure.id}">
                <span>${procedure.category}</span>
                <h3>${procedure.name}</h3>
                <p>${procedure.description}</p>
              </a>
            `,
          )
          .join("")}
      </div>
    </section>
    <section class="home-section">
      <div class="home-section-header">
        <span class="section-kicker">Workflow</span>
        <h2 class="section-heading">How DermaView works</h2>
      </div>
      <div class="home-steps">
        <div class="home-step">
          <span>1</span>
          <h3>Upload a clear image</h3>
          <p>Start with a patient image or treatment-area photo for visualization.</p>
        </div>
        <div class="home-step">
          <span>2</span>
          <h3>Select a procedure</h3>
          <p>Choose from supported dermatology treatments and review procedure details.</p>
        </div>
        <div class="home-step">
          <span>3</span>
          <h3>Review the preview</h3>
          <p>Compare visual output and use it as a guide for consultation discussion.</p>
        </div>
      </div>
    </section>
    <section class="disclaimer-band">
      <strong>Medical disclaimer</strong>
      <p>DermaView is for educational visualization only. It does not diagnose skin conditions or replace advice from a licensed dermatologist.</p>
    </section>
    <section class="final-cta">
      <div>
        <span class="section-kicker">Start</span>
        <h2 class="section-heading">Ready to preview a treatment?</h2>
        <p class="section-text">Browse procedures, upload an image, and review a visual treatment simulation.</p>
      </div>
      <a href="pages/procedures.html" class="button">Browse Procedures</a>
    </section>
  `;
}

function renderProcedures() {
  const activeProcedureId = selectedProcedureId || procedures[0]?.id;
  const selected = findProcedureById(activeProcedureId);

  app.innerHTML = `
    <section class="procedures-page-header">
      <div class="home-section-header">
        <span class="section-kicker">Procedures</span>
        <h2 class="section-heading">Choose a treatment to preview</h2>
        <p class="section-text">Review supported dermatology procedures, compare benefits, and continue into image visualization when you are ready.</p>
      </div>
    </section>
    <div class="procedures-list">
      ${procedures
        .map(
          (procedure) => `
        <button class="procedure-card ${procedure.id === activeProcedureId ? "selected" : ""}" data-procedure="${procedure.id}">
          <span class="procedure-chip">${procedure.category}</span>
          <h3>${procedure.name}</h3>
          <p>${procedure.description}</p>
          <span class="procedure-card-action">${procedure.id === activeProcedureId ? "Selected" : "View details"}</span>
        </button>
      `,
        )
        .join("")}
    </div>
    <div class="panel-card procedure-detail-card">
      ${selected ? renderProcedureDetails(selected) : renderProcedureEmpty()}
    </div>
  `;

  document.querySelectorAll(".procedure-card").forEach((button) => {
  button.addEventListener("click", () => {
    const id = button.getAttribute("data-procedure");

    selectedProcedureId = id;

    renderProcedures();
  });
});
}

function renderProcedureDetails(procedure) {
  const supportsProcessing = procedure.supportsProcessing !== false;

  return `
    <div class="procedure-detail">
      <div class="procedure-detail-summary">
        <span class="procedure-chip">${procedure.category}</span>
        <h3>${procedure.name}</h3>
        <p class="section-text">${procedure.description}</p>
      </div>
      <div class="procedure-benefits">
        <h4>Procedure Benefits</h4>
        <ul class="detail-list">
          ${procedure.details
            .map((detail) => `<li>${detail}</li>`)
            .join("")}
        </ul>
      </div>
      <div class="procedure-info-column">
        <div class="procedure-info-box">
          <h4>About This Procedure</h4>
          <p>${procedure.info}</p>
          ${procedure.preparation ? `<p><strong>Preparation:</strong> ${procedure.preparation}</p>` : ""}
          ${procedure.aftercare ? `<p><strong>Aftercare:</strong> ${procedure.aftercare}</p>` : ""}
        </div>
        <div class="procedure-detail-actions">
          ${supportsProcessing ? `<a href="treatment.html#${procedure.id}" class="button">${procedure.id === "general-skin-assessment" ? "Start Assessment" : "Use Image Processing"}</a>` : ""}
          <a href="schedule.html#${procedure.id}" class="button-secondary">Schedule Appointment</a>
        </div>
      </div>
    </div>
  `;
}

function renderProcedureEmpty() {
  return `
    <div class="empty-state">
      <div>
        <p>Select a procedure to view details</p>
      </div>
    </div>
  `;
}

function renderTreatment(id) {
  const procedure = findProcedureById(id);
  if (!procedure) {
    document.getElementById("treatment-title").textContent = "Procedure not found";
    document.getElementById("treatment-description").textContent = "Please choose a valid treatment from the procedures page.";
    return;
  }

  const isAssessment = procedure.id === "general-skin-assessment";
  const resultsTitle = document.getElementById("results-title");
  const workflowTitle = document.getElementById("workflow-title");
  const workflowList = document.getElementById("workflow-list");

  document.getElementById("treatment-title").textContent = procedure.name;
  document.getElementById("treatment-description").textContent = procedure.description;

  document.title = `${getClinicName()} | ${isAssessment ? "Skin Assessment" : procedure.name}`;

  if (resultsTitle) {
    resultsTitle.textContent = isAssessment ? "Skin Assessment Results" : "Treatment Visualization";
  }

  if (workflowTitle && workflowList) {
    workflowTitle.textContent = isAssessment ? "How Assessment Works" : "How It Works";
    workflowList.innerHTML = isAssessment
      ? `
        <li>Upload a clear, well-lit image of the skin area.</li>
        <li>DermaView checks redness, texture, contrast, and brightness signals.</li>
        <li>Review educational treatment suggestions to discuss with a dermatologist.</li>
        <li>Use the result as guidance only, not as a diagnosis.</li>
      `
      : `
        <li>Upload a clear image of the treatment area.</li>
        <li>DermaView applies a preview effect for visualization.</li>
        <li>Compare the before and after visuals.</li>
        <li>Consult with your dermatologist for next steps.</li>
      `;
  }

  const uploadPreviewContainer = document.getElementById("upload-preview-container");
  if (uploadedImageUrl) {
    uploadPreviewContainer.innerHTML = `
      <div class="upload-preview">
        <img src="${uploadedImageUrl}" alt="Uploaded" />
      </div>
      <button id="process-button" class="button" style="width:100%; margin-top:18px;">${isProcessing ? "Processing Image..." : isAssessment ? "Assess Skin Image" : "Analyze Image"}</button>
      <button id="clear-button" class="button-secondary" style="width:100%; margin-top:12px;">Clear Image</button>
    `;
  } else {
    uploadPreviewContainer.innerHTML = "";
  }

  const resultsContent = document.getElementById("results-content");
  if (showResults && uploadedImageUrl && processedImageUrl) {
    resultsContent.innerHTML = isAssessment ? renderAssessmentResults() : `
      <div class="comparison-grid">
        <div class="image-card">
          <img src="${uploadedImageUrl}" alt="Before Treatment" data-preview-image data-preview-title="Before Treatment" tabindex="0" />
        </div>
        <div class="image-card">
          <img src="${processedImageUrl}" alt="Projected Result" data-preview-image data-preview-title="Projected Result" tabindex="0" />
        </div>
      </div>
      <div class="stat-grid" style="margin-top:24px;">
        <div class="stat-card">
          <strong>92%</strong>
          <span>Analysis Confidence</span>
        </div>
        <div class="stat-card">
          <strong>4 weeks</strong>
          <span>Avg. Recovery Time</span>
        </div>
      </div>
      <div style="margin-top:24px;">
        <h4>Recommended Treatments</h4>
        <ul class="recommendation-list">
          <li><strong>Primary Treatment</strong><br />${procedure.name}</li>
          <li><strong>Recommended Sessions</strong><br />4–6 sessions for optimal results</li>
          <li><strong>Expected Improvement</strong><br />60–85% visible improvement</li>
        </ul>
      </div>
      ${renderAnalysisSaveStatus()}
      <div class="alert-box">Important: These results are for educational purposes only. Consult with a qualified dermatologist for personalized medical advice.</div>
      <a href="schedule.html#${procedure.id}" class="button" style="width:100%; margin-top:20px;">Schedule Consultation</a>
    `;
  } else {
    resultsContent.innerHTML = `
      <div class="empty-state">
        <div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16" />
            <path d="M12 8v12" />
            <path d="M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p>${isAssessment ? "Upload an image to start the skin assessment." : "Upload an image to see treatment visualization."}</p>
        </div>
      </div>
    `;
  }

  bindTreatmentEvents(id);
  bindImagePreviewEvents();
}

function bindTreatmentEvents(id) {
  const uploadInput = document.getElementById("image-upload");
  const processButton = document.getElementById("process-button");
  const clearButton = document.getElementById("clear-button");

  if (uploadInput) {
    uploadInput.addEventListener("change", (event) => {
      const file = event.target.files[0];

      if (!file) return;

      uploadedImageFile = file;
      uploadedImageUrl = URL.createObjectURL(file);
      showResults = false;
      processedImageUrl = null;

      renderTreatment(id);
    });
  }

  if (processButton) {
    processButton.addEventListener("click", async () => {
      if (!uploadedImageFile || isProcessing) return;

      isProcessing = true;
      analysisSaveMessage = "";
      lastSavedRecordId = null;
      renderTreatment(id);

      const formData = new FormData();

      formData.append("image", uploadedImageFile);
      formData.append("procedure", id);

      try {
        const response = await fetch("../process-image.php", {
          method: "POST",
          body: formData
        });

        const result = await response.json();

        console.log("PHP result:", result);
        if (result.success) {
          processedImageUrl = "../" + result.image + "?v=" + Date.now();
          assessmentResult = id === "general-skin-assessment"
            ? await buildAssessmentResult(uploadedImageUrl)
            : null;
          showResults = true;
        } else {
          showResults = false;
          alert(result.message || "Image processing failed");
          console.log(result);
        }

      } catch (error) {
        console.error(error);
        alert("Could not connect to image processing.");
      }

      isProcessing = false;
      showResults = Boolean(processedImageUrl);
      renderTreatment(id);

      try {
        isSavingAnalysis = true;
        analysisSaveMessage = "Saving analyzed image record...";
        renderTreatment(id);

        const saveResult = await saveAnalyzedImages(id);
        lastSavedRecordId = saveResult.id || null;
        analysisSaveMessage = lastSavedRecordId
          ? `Saved to processed images as record #${lastSavedRecordId}.`
          : "Saved to processed images.";
      } catch (error) {
        analysisSaveMessage = `Analysis completed, but the image record could not be saved. ${error.message || ""}`.trim();
      } finally {
        isSavingAnalysis = false;
        renderTreatment(id);
      }
    });
  }

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      uploadedImageFile = null;
      uploadedImageUrl = null;
      processedImageUrl = null;
      showResults = false;
      isProcessing = false;
      assessmentResult = null;
      isSavingAnalysis = false;
      analysisSaveMessage = "";
      lastSavedRecordId = null;
      renderTreatment(id);
    });
  }
}

function renderImageDataUrl(imageUrl, options = {}) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");

      if (ctx) {
        if (options.filter) {
          ctx.filter = options.filter;
        }
        ctx.drawImage(img, 0, 0);

        if (options.analyze) {
          const result = analyzeSkinImage(ctx, canvas.width, canvas.height);
          assessmentResult = result;
          resolve(options.returnAnalysis ? result : canvas.toDataURL("image/png"));
          return;
        }
      }

      resolve(canvas.toDataURL("image/png"));
    };
    img.onerror = () => reject(new Error("Could not load image for analysis."));
    img.src = imageUrl;
  });
}

function processImageWithFilters(imageUrl) {
  return renderImageDataUrl(imageUrl, {
    analyze: true,
    filter: "contrast(1.15) brightness(1.08) saturate(0.85) hue-rotate(5deg)"
  });
}

async function buildAssessmentResult(imageUrl) {
  const result = await renderImageDataUrl(imageUrl, {
    analyze: true,
    returnAnalysis: true
  });

  return result && result.metrics ? result : createFallbackAssessmentResult();
}

function analyzeSkinImage(ctx, width, height) {
  const imageData = ctx.getImageData(0, 0, width, height).data;
  const step = Math.max(4, Math.floor(Math.min(width, height) / 90));
  let count = 0;
  let brightness = 0;
  let brightnessSquared = 0;
  let redness = 0;
  let texture = 0;
  let previousLuminance = null;

  for (let y = 0; y < height; y += step) {
    previousLuminance = null;

    for (let x = 0; x < width; x += step) {
      const index = (y * width + x) * 4;
      const r = imageData[index];
      const g = imageData[index + 1];
      const b = imageData[index + 2];
      const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
      const redDelta = Math.max(0, r - (g + b) / 2) / 255;

      brightness += luminance;
      brightnessSquared += luminance * luminance;
      redness += redDelta;

      if (previousLuminance !== null) {
        texture += Math.abs(luminance - previousLuminance);
      }

      previousLuminance = luminance;
      count += 1;
    }
  }

  const averageBrightness = brightness / count;
  const contrast = Math.sqrt(Math.max(0, brightnessSquared / count - averageBrightness * averageBrightness));
  const averageRedness = redness / count;
  const textureScore = texture / Math.max(1, count);
  const metrics = {
    brightness: averageBrightness,
    contrast,
    redness: averageRedness,
    texture: textureScore
  };

  return {
    metrics,
    recommendations: buildTreatmentRecommendations(metrics)
  };
}

function buildTreatmentRecommendations(metrics) {
  const scored = [
    {
      id: "pico-carbon-laser",
      score: 55 + metrics.redness * 280 + metrics.contrast * 70,
      reason: "Visible redness, blemish-like color variation, or uneven tone may be worth discussing with a dermatologist."
    },
    {
      id: "co2-fractional-laser-dermapen",
      score: 48 + metrics.texture * 420 + metrics.contrast * 95,
      reason: "Texture and contrast patterns may point toward resurfacing or scar-texture consultation."
    },
    {
      id: "diamond-peel-facial",
      score: 45 + (1 - metrics.brightness) * 80 + metrics.contrast * 45,
      reason: "Lower brightness or dull-looking areas may fit gentle exfoliation or brightening consultation."
    },
    {
      id: "undereye-lip-filler",
      score: 32 + metrics.contrast * 60,
      reason: "Facial balance concerns require in-person assessment; filler options should be reviewed carefully."
    }
  ];

  return scored
    .map((item) => ({
      ...item,
      procedure: findProcedureById(item.id),
      score: Math.min(96, Math.max(35, Math.round(item.score)))
    }))
    .filter((item) => item.procedure)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
}

function createFallbackAssessmentResult() {
  const metrics = {
    brightness: 0.5,
    contrast: 0.35,
    redness: 0.18,
    texture: 0.28
  };

  return {
    metrics,
    recommendations: buildTreatmentRecommendations(metrics)
  };
}

function formatMetric(value) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function renderAnalysisSaveStatus() {
  if (!analysisSaveMessage) {
    return "";
  }

  const statusClass = isSavingAnalysis ? "analysis-save-status is-saving" : "analysis-save-status";

  return `
    <div class="${statusClass}">
      ${analysisSaveMessage}
    </div>
  `;
}

function renderAssessmentResults() {
  if (!assessmentResult) {
    assessmentResult = createFallbackAssessmentResult();
  }

  const { metrics, recommendations } = assessmentResult;

  return `
    <div class="comparison-grid">
      <div class="image-card">
        <img src="${uploadedImageUrl}" alt="Uploaded skin image" data-preview-image data-preview-title="Before Analysis" tabindex="0" />
      </div>
      <div class="image-card">
        <img src="${processedImageUrl}" alt="Processed skin image preview" data-preview-image data-preview-title="After Analysis" tabindex="0" />
      </div>
    </div>
    <div class="assessment-metrics">
      <div class="stat-card">
        <strong>${formatMetric(metrics.redness)}</strong>
        <span>Redness signal</span>
      </div>
      <div class="stat-card">
        <strong>${formatMetric(metrics.texture)}</strong>
        <span>Texture signal</span>
      </div>
      <div class="stat-card">
        <strong>${formatMetric(metrics.contrast)}</strong>
        <span>Contrast signal</span>
      </div>
      <div class="stat-card">
        <strong>${formatMetric(metrics.brightness)}</strong>
        <span>Brightness</span>
      </div>
    </div>
    <div class="assessment-recommendations">
      <h4>Suggested treatments to discuss</h4>
      <ul class="recommendation-list">
        ${recommendations
          .map(
            (item) => `
              <li>
                <strong>${item.procedure.name}</strong>
                <span>${item.score}% match strength</span>
                <p>${item.reason}</p>
                <a href="treatment.html#${item.procedure.id}">Preview this treatment</a>
              </li>
            `,
          )
          .join("")}
      </ul>
    </div>
    ${renderAnalysisSaveStatus()}
    <div class="alert-box">Important: This is an educational image-processing guide only. It cannot diagnose skin conditions or determine medical treatment. Please consult a licensed dermatologist.</div>
    <a href="schedule.html#general-skin-assessment" class="button" style="width:100%; margin-top:20px;">Schedule Consultation</a>
  `;
}

function ensureImagePreviewModal() {
  let modal = document.getElementById("imagePreviewModal");

  if (modal) {
    return modal;
  }

  modal = document.createElement("div");
  modal.id = "imagePreviewModal";
  modal.className = "image-preview-modal";
  modal.innerHTML = `
    <div class="image-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="imagePreviewTitle">
      <div class="image-preview-header">
        <h3 id="imagePreviewTitle">Image Preview</h3>
        <button type="button" class="image-preview-close" aria-label="Close image preview">&times;</button>
      </div>
      <img src="" alt="">
    </div>
  `;
  document.body.appendChild(modal);

  modal.querySelector(".image-preview-close").addEventListener("click", closeImagePreview);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeImagePreview();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.classList.contains("active")) {
      closeImagePreview();
    }
  });

  return modal;
}

function openImagePreview(src, title, alt) {
  const modal = ensureImagePreviewModal();
  const image = modal.querySelector("img");
  const heading = modal.querySelector("#imagePreviewTitle");

  image.src = src;
  image.alt = alt || title || "Image preview";
  heading.textContent = title || "Image Preview";
  modal.classList.add("active");
  modal.querySelector(".image-preview-close").focus();
}

function closeImagePreview() {
  const modal = document.getElementById("imagePreviewModal");

  if (!modal) return;

  modal.classList.remove("active");
  modal.querySelector("img").src = "";
}

function bindImagePreviewEvents(root = document) {
  root.querySelectorAll("[data-preview-image]").forEach((image) => {
    if (image.dataset.previewBound === "true") return;

    image.dataset.previewBound = "true";
    image.addEventListener("click", () => {
      openImagePreview(image.src, image.dataset.previewTitle || image.alt, image.alt);
    });
    image.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openImagePreview(image.src, image.dataset.previewTitle || image.alt, image.alt);
      }
    });
  });
}

function getProcessedImagesEndpoint() {
  return window.location.pathname.includes("/pages/")
    ? "../admin_pages/admin-processed-images.php"
    : "admin_pages/admin-processed-images.php";
}

function buildSavedRecommendations() {
  if (!assessmentResult || !assessmentResult.recommendations) {
    return [];
  }

  return assessmentResult.recommendations.map((item) => ({
    procedure_id: item.procedure?.id || item.id || "",
    procedure_name: item.procedure?.name || "",
    score: item.score,
    reason: item.reason
  }));
}

async function saveAnalyzedImages(id) {
  const procedure = findProcedureById(id);

  if (!procedure || !uploadedImageUrl || !processedImageUrl) {
    throw new Error("Missing analysis record details.");
  }

  const beforeImageForSave = await renderImageDataUrl(uploadedImageUrl);
  const afterImageForSave = await renderImageDataUrl(processedImageUrl);
  const formData = new FormData();
  formData.append("action", "add");
  formData.append("procedure_id", procedure.id);
  formData.append("procedure_name", procedure.name);
  formData.append(
    "analysis_type",
    procedure.id === "general-skin-assessment" ? "Skin Assessment" : "Treatment Visualization"
  );
  formData.append("before_image", beforeImageForSave);
  formData.append("after_image", afterImageForSave);
  formData.append("metrics_json", JSON.stringify(assessmentResult?.metrics || {}));
  formData.append("recommendations_json", JSON.stringify(buildSavedRecommendations()));

  const response = await fetch(getProcessedImagesEndpoint(), {
    method: "POST",
    body: formData
  });
  const responseText = await response.text();
  let data = null;

  try {
    data = JSON.parse(responseText);
  } catch (error) {
    throw new Error(responseText || "Invalid response while saving image record.");
  }

  if (!response.ok || data.status !== "ok") {
    throw new Error(data.message || "Failed to save image record.");
  }

  return data;
}

function formatScheduleDateValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getScheduleEndpoint() {
  return window.location.pathname.includes("/pages/")
    ? "../admin_pages/admin-appointments.php"
    : "admin_pages/admin-appointments.php";
}

function getScheduleCalendarDates(cursor) {
  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstOfMonth = new Date(year, month, 1);
  const startDay = firstOfMonth.getDay();
  const firstCell = new Date(year, month, 1 - startDay);

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(firstCell);
    date.setDate(firstCell.getDate() + index);
    return date;
  });
}

function getScheduleTimeSlots() {
  return [
    { value: "09:00:00", label: "9:00 AM" },
    { value: "10:00:00", label: "10:00 AM" },
    { value: "11:00:00", label: "11:00 AM" },
    { value: "13:00:00", label: "1:00 PM" },
    { value: "14:00:00", label: "2:00 PM" },
    { value: "15:00:00", label: "3:00 PM" },
    { value: "16:00:00", label: "4:00 PM" }
  ];
}

function isAppointmentBlocking(appointment) {
  return !["Cancelled", "No Show"].includes(appointment.status);
}

function normalizeScheduleTimeValue(value) {
  return String(value || "").slice(0, 5);
}

function cleanScheduleErrorMessage(message) {
  const text = String(message || "").trim();

  if (!text) {
    return "Please try again or contact the clinic directly.";
  }

  if (/fatal error|stack trace|mysqli|uncaught|xampp|config\.php/i.test(text)) {
    return "The clinic database is currently unavailable. Please try again in a moment.";
  }

  return text.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function renderSchedule(id) {
  const procedure = findProcedureById(id) || procedures[0];
  const today = formatScheduleDateValue(new Date());
  const timeSlots = getScheduleTimeSlots();

  document.title = `${getClinicName()} | Schedule ${procedure.name}`;

  app.innerHTML = `
    <section class="schedule-header">
      <div>
        <a href="procedures.html" class="button-secondary">Back to Procedures</a>
        <span class="section-kicker">Appointment</span>
        <h2 class="section-heading">Clinic Schedule</h2>
        <p class="section-text">Choose an available appointment date and time, then add the patient details for the clinic record.</p>
      </div>
    </section>

    <section class="schedule-layout">
      <form class="panel-card schedule-form" id="schedule-form">
        <input type="hidden" name="action" value="add" />
        <input type="hidden" name="source" value="online" />
        <input type="hidden" id="schedule-procedure-name" name="procedure_name" value="${procedure.name}" />
        <div class="schedule-selector">
          <label class="schedule-procedure-field">
            <span>Selected Procedure</span>
            <select id="schedule-procedure" name="procedure_id">
              ${procedures
                .map(
                  (item) => `<option value="${item.id}" ${item.id === procedure.id ? "selected" : ""}>${item.name}</option>`,
                )
                .join("")}
            </select>
          </label>

          <div class="schedule-picker">
            <div class="schedule-date-field">
              <span>Appointment Date</span>
              <input id="appointmentDateInput" type="hidden" name="appointment_date" value="${today}" required />
              <button type="button" class="schedule-date-button" id="appointmentDateButton"></button>
              <div class="schedule-date-dropdown" id="appointmentDateDropdown" hidden>
                <div class="schedule-date-dropdown-header">
                  <button type="button" id="appointmentDatePrev" aria-label="Previous month">&larr;</button>
                  <strong id="appointmentDateMonth"></strong>
                  <button type="button" id="appointmentDateNext" aria-label="Next month">&rarr;</button>
                </div>
                <div class="schedule-date-dropdown-grid" id="appointmentDateGrid"></div>
              </div>
            </div>

            <div>
              <h3 id="scheduleTimeTitle">Available Time Slots</h3>
              <div class="schedule-time-grid" id="scheduleTimeGrid">
                ${timeSlots
                  .map(
                    (slot, index) => `
                      <label class="schedule-time-slot">
                        <input type="radio" name="appointment_time" value="${slot.value}" ${index === 0 ? "checked" : ""} required />
                        <span>${slot.label}</span>
                      </label>
                    `,
                  )
                  .join("")}
              </div>
            </div>
          </div>
        </div>

        <div class="form-grid">
          <label>
            <span>Full Name</span>
            <input type="text" name="patient_name" autocomplete="name" required />
          </label>

          <label>
            <span>Email Address</span>
            <input type="email" name="email" autocomplete="email" required />
          </label>

          <label>
            <span>Phone Number</span>
            <input type="tel" name="phone" autocomplete="tel" required />
          </label>

          <label class="form-wide">
            <span>Notes or Skin Concern</span>
            <textarea name="notes" rows="5" placeholder="Briefly describe the concern or goal for this appointment."></textarea>
          </label>
        </div>

        <button class="button" type="submit">Schedule Appointment</button>
      </form>

      <aside class="panel-card schedule-summary">
        <span class="procedure-chip">${procedure.category}</span>
        <h3>${procedure.name}</h3>
        <p>${procedure.description}</p>
        <div class="schedule-summary-box">
          <strong>Before your visit</strong>
          <ul class="detail-list">
            <li>Bring a clear photo history if available.</li>
            <li>Avoid editing or filtering reference images.</li>
            <li>Final treatment advice must come from the dermatologist.</li>
          </ul>
        </div>
        <div id="schedule-confirmation" class="schedule-confirmation" hidden></div>
      </aside>
    </section>
  `;

  bindScheduleEvents();
}

function renderAppointmentBookingCalendar(state) {
  const dateInput = document.getElementById("appointmentDateInput");
  const dateButton = document.getElementById("appointmentDateButton");
  const dateDropdown = document.getElementById("appointmentDateDropdown");
  const dateMonth = document.getElementById("appointmentDateMonth");
  const dateGrid = document.getElementById("appointmentDateGrid");
  const timeTitle = document.getElementById("scheduleTimeTitle");
  const timeGrid = document.getElementById("scheduleTimeGrid");

  if (!dateInput || !timeGrid) return;

  state.selectedDateIso = dateInput.value || formatScheduleDateValue(new Date());
  const blockingAppointments = state.appointments.filter(isAppointmentBlocking);
  const bookedTimes = new Set(
    blockingAppointments
      .filter((appointment) => appointment.appointment_date === state.selectedDateIso)
      .map((appointment) => normalizeScheduleTimeValue(appointment.appointment_time))
  );
  const appointmentCounts = new Map();

  blockingAppointments.forEach((appointment) => {
    appointmentCounts.set(
      appointment.appointment_date,
      (appointmentCounts.get(appointment.appointment_date) || 0) + 1
    );
  });

  if (dateButton) {
    const selectedDate = new Date(`${state.selectedDateIso}T00:00:00`);
    dateButton.textContent = selectedDate.toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric"
    });
  }

  if (dateDropdown && dateMonth && dateGrid) {
    const todayIso = formatScheduleDateValue(new Date());
    const currentMonth = state.datePickerCursor.getMonth();
    const dates = getScheduleCalendarDates(state.datePickerCursor);

    dateMonth.textContent = state.datePickerCursor.toLocaleDateString("en-US", {
      month: "long",
      year: "numeric"
    });

    dateGrid.innerHTML = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
      .map((day) => `<span class="schedule-date-weekday">${day}</span>`)
      .join("");

    dates.forEach((date) => {
      const iso = formatScheduleDateValue(date);
      const count = appointmentCounts.get(iso) || 0;
      const button = document.createElement("button");

      button.type = "button";
      button.className = "schedule-date-day" +
        (date.getMonth() !== currentMonth ? " is-outside" : "") +
        (iso === state.selectedDateIso ? " is-selected" : "") +
        (count ? " has-bookings" : "");
      button.disabled = iso < todayIso;
      button.innerHTML = `<span>${date.getDate()}</span>${count ? `<small>${count}</small>` : ""}`;
      button.addEventListener("click", () => {
        state.selectedDateIso = iso;
        state.datePickerCursor = new Date(date.getFullYear(), date.getMonth(), 1);
        dateInput.value = iso;
        dateDropdown.hidden = true;
        renderAppointmentBookingCalendar(state);
      });

      dateGrid.appendChild(button);
    });
  }

  if (timeTitle) {
    const selectedDate = new Date(`${state.selectedDateIso}T00:00:00`);
    const bookedCount = blockingAppointments.filter(
      (appointment) => appointment.appointment_date === state.selectedDateIso
    ).length;

    timeTitle.textContent = `Available Time Slots for ${selectedDate.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric"
    })}${bookedCount ? ` (${bookedCount} booked)` : ""}`;
  }

  timeGrid.querySelectorAll(".schedule-time-slot").forEach((label) => {
    const input = label.querySelector("input");
    const isBooked = input && bookedTimes.has(normalizeScheduleTimeValue(input.value));

    label.classList.toggle("is-booked", Boolean(isBooked));

    if (input) {
      input.disabled = Boolean(isBooked);
      if (isBooked && input.checked) {
        input.checked = false;
      }
    }
  });

  const firstAvailableTime = timeGrid.querySelector("input:not(:disabled)");
  const selectedTime = timeGrid.querySelector("input:checked:not(:disabled)");

  if (!selectedTime && firstAvailableTime) {
    firstAvailableTime.checked = true;
  }
}

function loadAppointmentBookings(state) {
  const formData = new FormData();
  formData.append("action", "fetch_public_json");

  return fetch(getScheduleEndpoint(), {
    method: "POST",
    body: formData
  })
    .then((response) => response.json())
    .then((data) => {
      state.appointments = data.appointments || [];
      renderAppointmentBookingCalendar(state);
    })
    .catch(() => {
      state.appointments = [];
      renderAppointmentBookingCalendar(state);
    });
}

function bindScheduleEvents() {
  const procedureSelect = document.getElementById("schedule-procedure");
  const scheduleForm = document.getElementById("schedule-form");
  const confirmation = document.getElementById("schedule-confirmation");
  const dateInput = document.getElementById("appointmentDateInput");
  const selectedDate = dateInput?.value || formatScheduleDateValue(new Date());
  const state = {
    cursor: new Date(`${selectedDate}T00:00:00`),
    datePickerCursor: new Date(`${selectedDate}T00:00:00`),
    selectedDateIso: selectedDate,
    appointments: []
  };
  state.datePickerCursor = new Date(
    state.datePickerCursor.getFullYear(),
    state.datePickerCursor.getMonth(),
    1
  );
  const dateButton = document.getElementById("appointmentDateButton");
  const dateDropdown = document.getElementById("appointmentDateDropdown");
  const datePrev = document.getElementById("appointmentDatePrev");
  const dateNext = document.getElementById("appointmentDateNext");

  if (procedureSelect) {
    procedureSelect.addEventListener("change", () => {
      const nextId = procedureSelect.value;
      const nextProcedure = findProcedureById(nextId);
      const procedureNameInput = document.getElementById("schedule-procedure-name");
      if (procedureNameInput && nextProcedure) {
        procedureNameInput.value = nextProcedure.name;
      }
      window.location.hash = nextId;
    });
  }

  if (dateInput) {
    dateInput.addEventListener("change", () => {
      state.selectedDateIso = dateInput.value;
      renderAppointmentBookingCalendar(state);
    });
  }

  if (dateButton && dateDropdown) {
    dateButton.addEventListener("click", () => {
      dateDropdown.hidden = !dateDropdown.hidden;
    });

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".schedule-date-field")) {
        dateDropdown.hidden = true;
      }
    });
  }

  if (datePrev) {
    datePrev.addEventListener("click", () => {
      state.datePickerCursor = new Date(
        state.datePickerCursor.getFullYear(),
        state.datePickerCursor.getMonth() - 1,
        1
      );
      renderAppointmentBookingCalendar(state);
    });
  }

  if (dateNext) {
    dateNext.addEventListener("click", () => {
      state.datePickerCursor = new Date(
        state.datePickerCursor.getFullYear(),
        state.datePickerCursor.getMonth() + 1,
        1
      );
      renderAppointmentBookingCalendar(state);
    });
  }

  renderAppointmentBookingCalendar(state);
  loadAppointmentBookings(state);

  if (scheduleForm && confirmation) {
    scheduleForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(scheduleForm);
      const procedure = findProcedureById(formData.get("procedure_id"));
      fetch(getScheduleEndpoint(), {
        method: "POST",
        body: formData
      })
        .then((response) => response.text().then((message) => ({ response, message })))
        .then(({ response, message }) => {
          const cleanMessage = cleanScheduleErrorMessage(message);

          if (!response.ok || cleanMessage !== "Appointment scheduled successfully.") {
            throw new Error(cleanMessage || "Unable to save appointment.");
          }

          alert("Appointment has been scheduled");
          confirmation.hidden = false;
          confirmation.innerHTML = `
            <strong>${cleanMessage}</strong>
            <p>${formData.get("patient_name")}, your appointment for ${procedure ? procedure.name : "this procedure"} has been scheduled.</p>
            <p>A confirmation email has been sent to your email address.</p>
          `;
          scheduleForm.reset();
          if (dateInput) {
            dateInput.value = state.selectedDateIso;
          }
          loadAppointmentBookings(state);
        })
        .catch((error) => {
          confirmation.hidden = false;
          confirmation.innerHTML = `
            <strong>Unable to save request</strong>
            <p>${escapeHtml(cleanScheduleErrorMessage(error.message))}</p>
          `;
        });
    });
  }
}

function renderCurrentPage() {
  const path = window.location.pathname;

  if (path.includes("treatment.html")) {
    const hash = window.location.hash.slice(1);

    if (hash) {
      selectedProcedureId = hash;
      renderTreatment(hash);
    } else {
      selectedProcedureId = "general-skin-assessment";
      renderTreatment("general-skin-assessment");
    }

    return;
  }

  if (path.includes("procedures.html")) {
    renderProcedures();
    return;
  }

  if (path.includes("schedule.html")) {
    const hash = window.location.hash.slice(1) || "general-skin-assessment";
    selectedProcedureId = hash;
    renderSchedule(hash);
    return;
  }

  renderHome();
}

window.addEventListener("hashchange", renderCurrentPage);
window.addEventListener("load", async () => {
  renderCurrentPage();
  await loadProceduresFromDatabase();
  renderCurrentPage();
});
