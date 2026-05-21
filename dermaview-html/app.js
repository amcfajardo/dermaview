const procedures = [
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
    id: "face-slimming",
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

const app = document.getElementById("app");
let selectedProcedureId = null;
let uploadedImageUrl = null;
let uploadedImageFile = null;
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
            <a href="pages/procedures.html" class="button">Get Started</a>
<a href="pages/procedures.html" class="button-secondary">Browse Procedures</a>
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
        <a href="pages/procedures.html" class="button" style="margin-top: 24px;">Browse Procedures</a>
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

    renderProcedures();
  });
});
}

function renderProcedureDetails(procedure) {
  return `
    <div>

      <h3>${procedure.name}</h3>

      <p class="section-text">
        ${procedure.description}
      </p>

      <div style="margin: 24px 0;">

        <h4>Procedure Benefits</h4>

        <ul class="detail-list">
          ${procedure.details
            .map((detail) => `<li>${detail}</li>`)
            .join("")}
        </ul>

      </div>

      <div
        style="
          margin-top:20px;
          padding:18px;
          border-radius:18px;
          background:#f8fafc;
          border:1px solid #e5e7eb;
        "
      >

        <h4 style="margin-bottom:10px;">
          About This Procedure
        </h4>

        <p class="section-text" style="font-size:.98rem;">
          ${procedure.info}
        </p>

      </div>

      <a
        href="treatment.html#${procedure.id}"
        class="button"
        style="margin-top:24px;"
      >
        Use Image Processing
      </a>

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
          showResults = true;
        } else {
          alert(result.message || "Image processing failed");
          console.log(result);
        }

      } catch (error) {
        console.error(error);
        alert("Could not connect to image processing.");
      }

      isProcessing = false;
      renderTreatment(id);
    });
  }

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      uploadedImageFile = null;
      uploadedImageUrl = null;
      processedImageUrl = null;
      showResults = false;
      isProcessing = false;
      renderTreatment(id);
    });
  }
}



window.addEventListener("hashchange", render);
window.addEventListener("load", () => {
  const path = window.location.pathname;

  if (path.includes("treatment.html")) {
    const hash = window.location.hash.slice(1);

    if (hash) {
      selectedProcedureId = hash;
      renderTreatment(hash);
    }

    return;
  }

  if (path.includes("procedures.html")) {
    renderProcedures();
    return;
  }

  renderHome();
});
