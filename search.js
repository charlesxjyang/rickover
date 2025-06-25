let fuse;
let fullData = [];

function displayResults(results) {
  const tbody = document.querySelector('#resultsTable tbody');
  tbody.innerHTML = '';

  results.forEach(doc => {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td class="w-64 font-semibold py-2">${doc.Title}</td>
        <td class="w-20 py-2">${doc.Year}</td>
        <td class="w-2/5 py-2">${doc.Summary?.slice(0, 200) || ''}...</td>
        <td class="w-32 py-2">
            ${doc.Source && /^https?:\/\//.test(doc.Source)
            ? `<a href="${doc.Source}" target="_blank" rel="noopener noreferrer" class="text-blue-600 underline">Link</a>`
            : (doc.Source || '')}
        </td>
        <td class="w-32 py-2">
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
    fullData = data.sort(() => Math.random() - 0.5);

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
