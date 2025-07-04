document.addEventListener('DOMContentLoaded', () => { // <--- START OF DOMContentLoaded WRAPPER
let fuse;
let fullData = [];
let displayedData = [];
let currentRenderedRowCount = 0;
const rowsPerLoad = 20;
let observer;

// --- NEW MODAL ELEMENTS ---
const documentModal = document.getElementById('documentModal');
const closeModalButton = document.getElementById('closeModalButton');
const modalTitle = document.getElementById('modalTitle');
const modalIframeContainer = document.getElementById('modalIframeContainer');
// --- END NEW MODAL ELEMENTS ---

// Function to open the modal and load content
function openDocumentModal(s3Url, title) {
    modalTitle.textContent = title || 'Document View'; // Set modal title
    modalIframeContainer.innerHTML = '<p class="text-gray-500">Loading document...</p>'; // Show loading message

    const iframe = document.createElement('iframe');
    iframe.src = s3Url;
    iframe.title = title || "Document Viewer"; // Good for accessibility
    iframe.loading = "lazy"; // Optimize loading
    iframe.allowfullscreen = true; // Allow fullscreen for PDFs if desired

    iframe.onload = () => {
        // Optional: you can add a class to the iframe or container if you need to style it specifically
        // after content has loaded, e.g., if you have a spinner overlay.
        // For this setup, the iframe loading will simply replace the "Loading document..." text.
    };
    iframe.onerror = () => {
        modalIframeContainer.innerHTML = '<p class="text-red-500">Error loading document. Please try again.</p>';
        console.error("Error loading iframe content from:", s3Url);
    };

    modalIframeContainer.innerHTML = ''; // Clear loading message before appending iframe
    modalIframeContainer.appendChild(iframe);

    documentModal.classList.add('active'); // Show the modal
    document.body.style.overflow = 'hidden'; // Prevent scrolling of the main page
}

// Function to close the modal
function closeDocumentModal() {
    documentModal.classList.remove('active'); // Hide the modal
    document.body.style.overflow = ''; // Restore scrolling of the main page
    modalIframeContainer.innerHTML = ''; // Clear iframe content when closing
}


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

        // Links column - THIS IS THE MAJOR CHANGE FOR YOUR MODAL
        const linksCell = document.createElement('td');
        linksCell.className = 'w-32 py-2';
        let linksHtml = [];

        if (doc.file_pdf) {
            // Using data-s3-url to store the actual S3 path
            // Using data-document-title to pass the title to the modal
            linksHtml.push(
                `<a href="#" class="text-blue-600 underline document-link" data-s3-url="${encodeURIComponent(doc.file_pdf)}" data-document-title="${encodeURIComponent(doc.Title)}">PDF</a>`
            );
        }
        if (doc.url_OCR) {
            // Using data-s3-url to store the actual S3 path
            // Using data-document-title to pass the title to the modal
            linksHtml.push(
                `<a href="#" class="text-blue-600 underline document-link" data-s3-url="${encodeURIComponent(doc.url_OCR)}" data-document-title="${encodeURIComponent(doc.Title)}">OCR</a>`
            );
        }
        linksCell.innerHTML = linksHtml.join(' | ');

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

// --- NEW MODAL EVENT LISTENERS ---

// Event listener for clicks on document links (using delegation on the table body)
document.addEventListener('click', (event) => { // Using document for event listener
    const link = event.target.closest('.document-link');

    if (link) {
        event.preventDefault(); // Prevent browser navigation

        // Decode the URL before using it, as it was encoded when put into data-s3-url
        const s3Url = decodeURIComponent(link.dataset.s3Url);
        const documentTitle = decodeURIComponent(link.dataset.documentTitle); // Decode the title too

        if (s3Url) {
            openDocumentModal(s3Url, documentTitle);
        } else {
            console.error("No s3Url found on the clicked link:", link);
        }
    }
});

// Event listener for the close button
closeModalButton.addEventListener('click', closeDocumentModal);

// Optional: Close modal when clicking outside content (on the overlay)
documentModal.addEventListener('click', (event) => {
    // Check if the click was directly on the modal overlay itself, not its children
    if (event.target === documentModal) {
        closeDocumentModal();
    }
});

// Optional: Close modal with Escape key
document.addEventListener('keydown', (event) => {
    // Check if the modal is currently active
    if (event.key === 'Escape' && documentModal.classList.contains('active')) {
        closeDocumentModal();
    }
});

// --- END NEW MODAL EVENT LISTENERS ---


// Main execution
fetch('manifest.json')
    .then(res => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
    })
    .then(data => {
        // Assuming your JSON structure has a 'documents' array or similar
        // Adjust this line if 'data' directly contains the array of documents
        fullData = data.documents ? data.documents : data; // Fallback if no 'documents' key
        fullData = fullData.sort(() => Math.random() - 0.5);
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
}); // <--- END OF DOMContentLoaded WRAPPER
