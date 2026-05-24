(function () {
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  function formatDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return '';
    }

    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function metricsSummary(metrics) {
    if (!metrics) return '';

    return Object.entries(metrics)
      .map(([key, value]) => {
        const label = key.charAt(0).toUpperCase() + key.slice(1);
        const percent = Math.round(Math.max(0, Math.min(1, Number(value))) * 100);
        return `<span>${escapeHtml(label)}: ${percent}%</span>`;
      })
      .join('');
  }

  function displayPath(src) {
    if (!src) return '';
    if (/^(https?:|data:|blob:|\/|\.{1,2}\/)/i.test(src)) return src;
    return `../${src}`;
  }

  window.initProcessedImages = function () {
    const list = document.getElementById('processedImagesList');
    const search = document.getElementById('processedImagesSearch');
    const refresh = document.getElementById('refreshProcessedImages');

    if (!list) return;

    let records = [];

    function render() {
      const query = search ? search.value.trim().toLowerCase() : '';
      const filtered = query
        ? records.filter(record => {
            const haystack = `${record.procedure_name} ${record.analysis_type} ${record.created_at}`.toLowerCase();
            return haystack.includes(query);
          })
        : records;

      if (!filtered.length) {
        list.innerHTML = '<p class="accounts-empty-cell">No processed images found.</p>';
        return;
      }

      list.innerHTML = filtered.map(record => `
        <article class="processed-image-card">
          <div class="processed-image-card-header">
            <div>
              <span class="procedure-chip">${escapeHtml(record.analysis_type)}</span>
              <h4>${escapeHtml(record.procedure_name)}</h4>
              <p>${escapeHtml(formatDate(record.created_at))}</p>
            </div>
            <span class="processed-image-id">#${record.id}</span>
          </div>

          <div class="processed-image-compare">
            <figure>
              <img src="${escapeHtml(displayPath(record.before_image_path))}" alt="Before analysis" data-preview-image data-preview-title="Before Analysis" tabindex="0">
              <figcaption>Before</figcaption>
            </figure>
            <figure>
              <img src="${escapeHtml(displayPath(record.after_image_path))}" alt="After analysis" data-preview-image data-preview-title="After Analysis" tabindex="0">
              <figcaption>After</figcaption>
            </figure>
          </div>

          <div class="processed-image-metrics">
            ${metricsSummary(record.metrics)}
          </div>
        </article>
      `).join('');
      bindPreviewEvents(list);
    }

    function ensurePreviewModal() {
      let modal = document.getElementById('processedImagePreviewModal');

      if (modal) {
        return modal;
      }

      modal = document.createElement('div');
      modal.id = 'processedImagePreviewModal';
      modal.className = 'image-preview-modal';
      modal.innerHTML = `
        <div class="image-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="processedImagePreviewTitle">
          <div class="image-preview-header">
            <h3 id="processedImagePreviewTitle">Image Preview</h3>
            <button type="button" class="image-preview-close" aria-label="Close image preview">&times;</button>
          </div>
          <img src="" alt="">
        </div>
      `;
      document.body.appendChild(modal);

      modal.querySelector('.image-preview-close').addEventListener('click', closePreview);
      modal.addEventListener('click', (event) => {
        if (event.target === modal) closePreview();
      });
      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && modal.classList.contains('active')) {
          closePreview();
        }
      });

      return modal;
    }

    function openPreview(src, title, alt) {
      const modal = ensurePreviewModal();
      const image = modal.querySelector('img');
      const heading = modal.querySelector('#processedImagePreviewTitle');

      image.src = src;
      image.alt = alt || title || 'Image preview';
      heading.textContent = title || 'Image Preview';
      modal.classList.add('active');
      modal.querySelector('.image-preview-close').focus();
    }

    function closePreview() {
      const modal = document.getElementById('processedImagePreviewModal');
      if (!modal) return;

      modal.classList.remove('active');
      modal.querySelector('img').src = '';
    }

    function bindPreviewEvents(root) {
      root.querySelectorAll('[data-preview-image]').forEach(image => {
        if (image.dataset.previewBound === 'true') return;

        image.dataset.previewBound = 'true';
        image.addEventListener('click', () => {
          openPreview(image.src, image.dataset.previewTitle || image.alt, image.alt);
        });
        image.addEventListener('keydown', event => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openPreview(image.src, image.dataset.previewTitle || image.alt, image.alt);
          }
        });
      });
    }

    function loadRecords() {
      const formData = new FormData();
      formData.append('action', 'fetch_json');

      fetch('admin-processed-images.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.json())
        .then(data => {
          records = data.images || [];
          render();
        })
        .catch(() => {
          list.innerHTML = '<p class="accounts-empty-cell">Failed to load processed images.</p>';
        });
    }

    if (search) {
      search.addEventListener('input', render);
    }

    if (refresh) {
      refresh.addEventListener('click', loadRecords);
    }

    loadRecords();
  };
})();
