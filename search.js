let fuse;
let fullData = [];

function displayResults(results) {
  const tbody = document.querySelector('#resultsTable tbody');
  tbody.innerHTML = '';

  results.forEach(doc => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="font-semibold">${doc.Title}</td>
      <td class="py-2">${doc.Year}</td>
      <td>${doc.Summary.slice(0, 200)}...</td>
      <td>
        ${/^https?:\/\//.test(doc.Source)
          ? `<a href="${doc.Source}" target="_blank" rel="noopener noreferrer" class="text-blue-600 underline">${doc.Source}</a>`
          : doc.Source || ''}
      </td>
      <td>
        <a href="${doc.file_pdf}" target="_blank" rel="noopener noreferrer" class="text-blue-600 underline">PDF</a> |
        <a href="${doc.url_OCR}" target="_blank" rel="noopener noreferrer" class="text-blue-600 underline">OCR</a>
      </td>
    `;
    tbody.appendChild(row);
  });
}

// Load manifest and initialize search
fetch('manifest.json')
  .then(res => res.json())
  .then(data => {
    fullData = data;

    // Show full data by default
    displayResults(fullData);

    // Set up Fuse search
    fuse = new Fuse(fullData, {
      keys: ['Title', 'Summary'],
      threshold: 0.5,
      minMatchCharLength: 2,
    });

    // Wire up search input
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.trim();
      const results = query ? fuse.search(query).map(r => r.item) : fullData;
      displayResults(results);
    });
  })
  .catch(err => {
    console.error('Error loading manifest.json:', err);
    document.querySelector('#resultsTable tbody').innerHTML = '<tr><td colspan="4">Failed to load data.</td></tr>';
  });
