// search.js

document.addEventListener('DOMContentLoaded', () => {

    let fuse;
    let fullData = [];
    let displayedData = [];
    let currentRenderedRowCount = 0;
    const rowsPerLoad = 20;
    let observer;

    // --- S3 Base URL (UNCOMMENT AND SET IF YOUR MANIFEST.JSON HAS RELATIVE PATHS) ---
    // const s3BaseUrl = 'https://your-s3-bucket.s3.amazonaws.com/'; // <-- REPLACE WITH YOUR ACTUAL S3 BASE URL
    // --- END S3 Base URL ---

    // --- MODAL ELEMENTS ---
    // These are now guaranteed to exist because we are inside DOMContentLoaded
    const documentModal = document.getElementById('documentModal');
    const closeModalButton = document.getElementById('closeModalButton');
    const modalTitle = document.getElementById('modalTitle');
    const modalIframeContainer = document.getElementById('modalIframeContainer');
    // --- END MODAL ELEMENTS ---

    // Function to open the modal and load content
    function openDocumentModal(s3Url, title) {
        modalTitle.textContent = title || 'Document View'; // Set modal title
        modalIframeContainer.innerHTML = '<p class="text-gray-500">Loading document...</p>'; // Show loading message

        const iframe = document.createElement('iframe');
        iframe.src = s3Url;
        iframe.title = title || "Document Viewer"; // Good for accessibility
        iframe.loading = "lazy"; // Optimize loading
        iframe.allowfullscreen = true; // Allow fullscreen for PDFs if desired

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
            console.log("Debugging Doc:", doc.Title, "file_pdf:", doc.file_pdf, "file_OCR:", doc.file_OCR, "Type of file_OCR:", typeof doc.file_OCR);

            // First 3 columns via innerHTML
            row.innerHTML = `
                <td class="w-64 font-semibold py-2">${doc.Title || ''}</td>
                <td class="w-20 py-2">${doc.Year || ''}</td>
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

            // Links column - THIS IS WHERE DEEP LINKING IS IMPLEMENTED
            const linksCell = document.createElement('td');
            linksCell.className = 'w-32 py-2';
            let linksHtml = [];

            let fullPdfUrl = doc.file_pdf;
            let fullOcrUrl = doc.file_OCR;

            const s3PathEncodedForUrl = encodeURIComponent(fullPdfUrl);
            const titleEncodedForUrl = encodeURIComponent(doc.Title || '');
            linksHtml.push(
                `<a href="?file=${s3PathEncodedForUrl}" class="text-blue-600 underline document-link" data-s3-url="${s3PathEncodedForUrl}" data-document-title="${titleEncodedForUrl}">PDF</a>`
            );
        
            // The OCR (TXT) files will also load in the iframe, just as raw text
            const s3PathEncodedForUrlOCR = encodeURIComponent(fullOcrUrl);
            const titleEncodedForUrlOCR = encodeURIComponent(doc.Title || '');
            if (fullPdfUrl) { // Add a separator if PDF link already exists
                linksHtml.push(' | ');
            }
            linksHtml.push(
                `<a href="?file=${s3PathEncodedForUrlOCR}" class="text-blue-600 underline document-link" data-s3-url="${s3PathEncodedForUrlOCR}" data-document-title="${titleEncodedForUrlOCR}">OCR</a>`
            );
            
            linksCell.innerHTML = linksHtml.join(''); // Removed extra ' | ' join as it's now handled conditionally

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
            root: document.querySelector('.max-h-\\[600px\\]'), // This targets the scrollable div
            rootMargin: '0px 0px 100px 0px',
            threshold: 0.1
        });

        observer.observe(lastRow);
    }

    // --- MODAL EVENT LISTENERS ---

    // Event listener for clicks on document links (using delegation on the table body)
    document.addEventListener('click', (event) => {
        const link = event.target.closest('.document-link');

        if (link) {
            event.preventDefault(); // Prevent browser navigation

            // Decode the URL before using it, as it was encoded when put into data-s3-url
            const s3Url = decodeURIComponent(link.dataset.s3Url);
            const documentTitle = decodeURIComponent(link.dataset.documentTitle); // Decode the title too

            // Update URL in browser history without reloading the page
            // This makes the deep link shareable even if the user clicks a link
            const newUrl = `${window.location.pathname}?file=${encodeURIComponent(s3Url)}`;
            window.history.pushState({ path: newUrl }, '', newUrl);


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

    // --- END MODAL EVENT LISTENERS ---


    // Main execution
    fetch('manifest.json')
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            // Adjust this line if 'data' directly contains the array of documents,
            // or if your JSON has a different key than 'documents'
            fullData = data.documents ? data.documents : data;
            fullData = fullData.filter(d => d.gemini === true); // Only show Gemini-processed posts
            fullData = fullData.sort(() => Math.random() - 0.5); // Random sort
            displayedData = fullData; // Initial display data is all data

            displayResults(displayedData, false); // Populate the table

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

            // --- Handle deep linking on initial page load ---
            handleDeepLink();
            // --- END NEW ---
        })
        .catch(err => {
            console.error('Error loading manifest.json:', err);
            document.querySelector('#resultsBody').innerHTML =
                '<tr><td colspan="5" class="py-4 text-red-600 text-center">Failed to load data. Please check console for details.</td></tr>';
        });

    // --- NEW FUNCTION: handleDeepLink ---
    function handleDeepLink() {
        const urlParams = new URLSearchParams(window.location.search);
        const fileToLoad = urlParams.get('file'); // Get the 'file' parameter

        if (fileToLoad) {
            const decodedFileToLoad = decodeURIComponent(fileToLoad);

            // Find the corresponding document in your fullData array
            const documentToOpen = fullData.find(doc => {
                // --- UNCOMMENT AND MODIFY IF YOUR MANIFEST.JSON HAS RELATIVE PATHS ---
                // const docPdfUrl = doc.file_pdf ? (s3BaseUrl + doc.file_pdf) : null;
                // const docOcrUrl = doc.file_OCR ? (s3BaseUrl + doc.file_OCR) : null;
                // return docPdfUrl === decodedFileToLoad || docOcrUrl === decodedFileToLoad;
                // --- END UNCOMMENT SECTION ---

                // If doc.file_pdf and doc.file_OCR are already full S3 URLs:
                return doc.file_pdf === decodedFileToLoad || doc.file_OCR === decodedFileToLoad;
            });


            if (documentToOpen) {
                // If found, open the modal with the correct document
                openDocumentModal(decodedFileToLoad, documentToOpen.Title);
            } else {
                console.warn(`Deep link: Document with file path "${decodedFileToLoad}" not found in data.`);
                // You might want to display a message to the user here
            }
        }
    }
    // --- END NEW FUNCTION ---

}); // End of DOMContentLoaded listener
