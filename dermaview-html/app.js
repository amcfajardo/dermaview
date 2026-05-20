const procedures = [
  {
    id: "acne-treatment",
    name: "Acne Treatment",
    description: "Advanced laser and light-based treatments for acne-prone skin",
    category: "Treatment",
    details: [
      "Targets acne-causing bacteria",
      "Reduces sebum production",
      "Minimizes scarring",
      "Safe for all skin types",
    ],
  },
  {
    id: "skin-rejuvenation",
    name: "Skin Rejuvenation",
    description: "Comprehensive anti-aging and texture improvement procedures",
    category: "Rejuvenation",
    details: [
      "Improves skin texture",
      "Reduces fine lines and wrinkles",
      "Enhances skin tone",
      "Promotes collagen production",
    ],
  },
  {
    id: "scar-reduction",
    name: "Scar Reduction",
    description: "Specialized treatments to minimize the appearance of scars",
    category: "Treatment",
    details: [
      "Reduces scar depth",
      "Improves skin appearance",
      "Multiple treatment options",
      "Personalized approach",
    ],
  },
  {
    id: "pigmentation-correction",
    name: "Pigmentation Correction",
    description: "Treatment for hyperpigmentation, melasma, and sun damage",
    category: "Correction",
    details: [
      "Targets excess pigmentation",
      "Even skin tone",
      "Prevents recurrence",
      "Gentle on sensitive skin",
    ],
  },
  {
    id: "hair-removal",
    name: "Hair Removal",
    description: "Permanent and semi-permanent hair removal solutions",
    category: "Hair",
    details: [
      "Long-lasting results",
      "Minimal discomfort",
      "Various skin types",
      "Cost-effective",
    ],
  },
  {
    id: "wrinkle-reduction",
    name: "Wrinkle Reduction",
    description: "Advanced treatments to smooth lines and wrinkles",
    category: "Rejuvenation",
    details: [
      "Natural-looking results",
      "Immediate effects",
      "Preventative option",
      "Customizable intensity",
    ],
  },
];

const app = document.getElementById("app");
let selectedProcedureId = null;
let uploadedImageUrl = null;
let processedImageUrl = null;
let isProcessing = false;
let showResults = false;

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
  } else {
    renderHome();
  }
}

function renderHome() {
  app.innerHTML = `
    <section class="hero">
      <div class="hero-grid">
        <div>
          <p class="status-badge">Professional Dermatology Platform</p>
          <h1 class="hero-headline">Professional Dermatology Image Analysis</h1>
          <p class="hero-copy">Leverage advanced image processing technology to visualize and analyze skin conditions with precision.</p>
          <p class="hero-copy">DermaView helps clinicians and patients understand treatment outcomes through sophisticated image analysis.</p>
          <div class="cta-row">
            <a href="#procedures" class="button">Get Started</a>
            <a href="#procedures" class="button-secondary">Browse Procedures</a>
          </div>
        </div>
        <div class="features-grid">
          <div class="feature-card">
            <h3>🔍 Advanced Analysis</h3>
            <p>State-of-the-art image processing algorithms for detailed skin analysis.</p>
          </div>
          <div class="feature-card">
            <h3>📊 Treatment Visualization</h3>
            <p>Visualize potential treatment outcomes with interactive before/after comparisons.</p>
          </div>
          <div class="feature-card">
            <h3>📚 Educational Content</h3>
            <p>Comprehensive information about procedures and treatment options.</p>
          </div>
          <div class="feature-card">
            <h3>💼 Clinical Grade</h3>
            <p>Professional-grade tools designed for medical professionals and clinics.</p>
          </div>
        </div>
      </div>
    </section>
    <section class="section-grid">
      <div class="panel-card">
        <h3 class="section-heading">Ready to explore treatment options?</h3>
        <p class="section-text">Browse our available procedures and learn how DermaView can help you visualize your treatment journey.</p>
        <a href="#procedures" class="button" style="margin-top: 24px;">Browse Procedures</a>
      </div>
    </section>
  `;
}

function renderProcedures() {
  const selected = findProcedureById(selectedProcedureId);

  app.innerHTML = `
    <section class="section-grid">
      <div>
        <h2 class="section-heading">Available Procedures</h2>
        <p class="section-text">Explore our comprehensive selection of dermatological treatments and procedures.</p>
      </div>
    </section>
    <div class="grid-2">
      <div>
        ${procedures
          .map(
            (procedure) => `
          <button class="procedure-card ${procedure.id === selectedProcedureId ? "selected" : ""}" data-procedure="${procedure.id}">
            <div>
              <h3>${procedure.name}</h3>
              <p>${procedure.description}</p>
            </div>
            <span class="procedure-chip">${procedure.category}</span>
          </button>
        `,
          )
          .join("")}
      </div>
      <div class="panel-card">
        ${selected ? renderProcedureDetails(selected) : renderProcedureEmpty()}
      </div>
    </div>
  `;

  document.querySelectorAll(".procedure-card").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.getAttribute("data-procedure");
      selectedProcedureId = id;
      window.location.href = `pages/treatment.html#${id}`;
    });
  });
}

function renderProcedureDetails(procedure) {
  return `
    <div>
      <h3>${procedure.name}</h3>
      <p class="section-text">${procedure.description}</p>
      <div style="margin: 24px 0;">
        <h4>Key Benefits</h4>
        <ul class="detail-list">
          ${procedure.details.map((detail) => `<li>${detail}</li>`).join("")}
        </ul>
      </div>
      <a href="#treatment/${procedure.id}" class="button">View Treatment Options</a>
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

  document.getElementById("treatment-title").textContent = procedure.name;
  document.getElementById("treatment-description").textContent = procedure.description;

  const uploadPreviewContainer = document.getElementById("upload-preview-container");
  if (uploadedImageUrl) {
    uploadPreviewContainer.innerHTML = `
      <div class="upload-preview">
        <img src="${uploadedImageUrl}" alt="Uploaded" />
      </div>
      <button id="process-button" class="button" style="width:100%; margin-top:18px;">${isProcessing ? "Processing Image..." : "Analyze Image"}</button>
      <button id="clear-button" class="button-secondary" style="width:100%; margin-top:12px;">Clear Image</button>
    `;
  } else {
    uploadPreviewContainer.innerHTML = "";
  }

  const resultsContent = document.getElementById("results-content");
  if (showResults && uploadedImageUrl && processedImageUrl) {
    resultsContent.innerHTML = `
      <div class="comparison-grid">
        <div class="image-card">
          <img src="${uploadedImageUrl}" alt="Before Treatment" />
        </div>
        <div class="image-card">
          <img src="${processedImageUrl}" alt="Projected Result" />
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
      <div class="alert-box">Important: These results are for educational purposes only. Consult with a qualified dermatologist for personalized medical advice.</div>
      <button class="button" style="width:100%; margin-top:20px;">Schedule Consultation</button>
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
          <p>Upload an image to see treatment visualization.</p>
        </div>
      </div>
    `;
  }

  bindTreatmentEvents(id);
}

function bindTreatmentEvents(id) {
  const uploadInput = document.getElementById("image-upload");
  const processButton = document.getElementById("process-button");
  const clearButton = document.getElementById("clear-button");

  if (uploadInput) {
    uploadInput.addEventListener("change", (event) => {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        uploadedImageUrl = reader.result;
        showResults = false;
        processedImageUrl = null;
        renderTreatment(id);
      };
      reader.readAsDataURL(file);
    });
  }

  if (processButton) {
    processButton.addEventListener("click", async () => {
      if (!uploadedImageUrl || isProcessing) return;
      isProcessing = true;
      renderTreatment(id);
      await new Promise((resolve) => setTimeout(resolve, 1200));
      processedImageUrl = await processImageWithFilters(uploadedImageUrl);
      isProcessing = false;
      showResults = true;
      renderTreatment(id);
    });
  }

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      uploadedImageUrl = null;
      processedImageUrl = null;
      showResults = false;
      isProcessing = false;
      renderTreatment(id);
    });
  }
}

function processImageWithFilters(imageUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");

      if (ctx) {
        ctx.filter = "contrast(1.15) brightness(1.08) saturate(0.85) hue-rotate(5deg)";
        ctx.drawImage(img, 0, 0);
      }

      resolve(canvas.toDataURL("image/png"));
    };
    img.src = imageUrl;
  });
}

window.addEventListener("hashchange", render);
window.addEventListener("load", () => {
  if (window.location.pathname.includes("treatment.html")) {
    const hash = window.location.hash.slice(1);
    if (hash) {
      selectedProcedureId = hash;
      renderTreatment(hash);
    }
  } else {
    if (!window.location.hash) {
      window.location.hash = "home.html";
    }
    render();
  }
});
