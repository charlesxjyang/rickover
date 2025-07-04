let fuse;
let fullData = [];
let displayedData = [];
let currentRenderedRowCount = 0;
const rowsPerLoad = 20;
let observer;

function displayResults(dataToDisplay, append = false) {
  const tbody = document.querySelector('#resultsBody');

  if (!append) {
    tbody.innerHTML = '';
    currentRenderedRowCount = 0;
    if (observer) {
      observer.disconnect();
      observer = null;
    }
  }

  const startIndex = currentRenderedRowCount;
  const endIndex = Math.min(startIndex + rowsPerLoad, dataToDisplay.length);
  if (startIndex >= endIndex) {
    if (observer) {
      observer.disconnect();
      observer = null;
    }
    return;
  }

  const fragment = document.createDocumentFragment();

  for (let i = startIndex; i < endIndex; i++) {
    const doc = dataToDisplay[i];
    const row = document.createElement('tr');

    // First 3 columns via innerHTML
    row.innerHTML = `
      <td class="w-64 font-semibold py-2">${doc.Title}</td>
      <td class="w-20 py-2">${doc.Year}</td>
      <td class="w-2/5 py-2">
        ${doc.Summary?.slice(0, 200) || ''}
        ${doc.Summary && doc.Summary.length > 200 ? '...' : ''}
      </td>
    `;

    // Source column
    const sourceCell = document.createElement('td');
    sourceCell.className = 'w-32 py-2';
    if (doc.Source && /^https?:\/\//.test(doc.Source)) {
      sourceCell.innerHTML = `<a href="${doc.Source}" target="_blank" rel="noopener noreferrer" class="text-blue-600 underline">Link</a>`;
    } else {
      sourceCell.textContent = doc.Source || '';
    }

    // Links column
    const linksCell = document.createElement('td');
    linksCell.className = 'w-32 py-2';
    const pdfLink = doc.file_pdf
      ? `<a href="/viewer.html?doc=${encodeURIComponent(doc.file_pdf)}" class="text-blue-600 underline">PDF</a>`
      : '';
    const ocrLink = doc.url_OCR
      ? `<a href="/viewer.html?doc=${encodeURIComponent(doc.url_OCR)}" class="text-blue-600 underline">OCR</a>`
      : '';
    linksCell.innerHTML = [pdfLink, ocrLink].filter(Boolean).join(' | ');

    row.appendChild(sourceCell);
    row.appendChild(linksCell);
    fragment.appendChild(row);
  }

  tbody.appendChild(fragment);
  currentRenderedRowCount = endIndex;

  if (currentRenderedRowCount < dataToDisplay.length) {
    setupIntersectionObserver(dataToDisplay);
  } else {
    if (observer) {
      observer.disconnect();
      observer = null;
    }
  }
}

function setupIntersectionObserver(dataToObserve) {
  const tbody = document.querySelector('#resultsBody');
  if (tbody.children.length === 0) return;

  const lastRow = tbody.lastElementChild;

  if (observer) {
    observer.disconnect();
  }

  observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && currentRenderedRowCount < dataToObserve.length) {
        observer.disconnect();
        displayResults(dataToObserve, true);
      }
    });
  }, {
    root: document.querySelector('.max-h-\\[600px\\]'),
    rootMargin: '0px 0px 100px 0px',
    threshold: 0.1
  });

  observer.observe(lastRow);
}

// Main execution
fetch('manifest.json')
  .then(res => {
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return res.json();
  })
  .then(data => {
    fullData = data.sort(() => Math.random() - 0.5);
    displayedData = fullData;

    displayResults(displayedData, false);

    fuse = new Fuse(fullData, {
      keys: ['Title', 'Summary'],
      threshold: 0.5,
      minMatchCharLength: 2,
    });

    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.trim();
      displayedData = query
        ? fuse.search(query).map(r => r.item)
        : fullData;
      displayResults(displayedData, false);
    });
  })
  .catch(err => {
    console.error('Error loading manifest.json:', err);
    document.querySelector('#resultsBody').innerHTML =
      '<tr><td colspan="5" class="py-4 text-red-600 text-center">Failed to load data. Please check console for details.</td></tr>';
  });
