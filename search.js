let fuse;
let fullData = [];
let displayedData = []; // Data currently filtered by search (either all data or search results)
let currentRenderedRowCount = 0; // Tracks how many rows are actually in the DOM
const rowsPerLoad = 20; // Number of rows to add each time the user scrolls to the bottom

// Store the observer instance
let observer;

/**
 * Displays a subset of the data in the table.
 * @param {Array} dataToDisplay - The array of data objects to potentially display.
 * @param {boolean} [append=false] - True to append new rows, false to clear and re-render from the start.
 */
function displayResults(dataToDisplay, append = false) {
    const tbody = document.querySelector('#resultsBody');

    // If not appending, clear the table and reset the rendered count
    if (!append) {
        tbody.innerHTML = '';
        currentRenderedRowCount = 0;
        // Disconnect previous observer if it exists, as the content is changing
        if (observer) {
            observer.disconnect();
            observer = null; // Clear the observer instance
        }
    }

    const startIndex = currentRenderedRowCount;
    const endIndex = Math.min(startIndex + rowsPerLoad, dataToDisplay.length);

    // If there are no new rows to add, or we've already displayed all data, just return
    if (startIndex >= endIndex) {
        // If no new rows to load but we are at the end, ensure observer is disconnected
        if (observer) {
            observer.disconnect();
            observer = null;
        }
        return;
    }

    // Use a DocumentFragment for efficient DOM manipulation when appending multiple rows
    const fragment = document.createDocumentFragment();

    for (let i = startIndex; i < endIndex; i++) {
        const doc = dataToDisplay[i];
        const row = document.createElement('tr');
        // Use proper template literals for the innerHTML
        row.innerHTML = `
            <td class="w-64 font-semibold py-2">${doc.Title}</td>
            <td class="w-20 py-2">${doc.Year}</td>
            <td class="w-2/5 py-2">${doc.Summary?.slice(0, 200) || ''}${doc.Summary && doc.Summary.length > 200 ? '...' : ''}</td>
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
        fragment.appendChild(row);
    }

    tbody.appendChild(fragment);
    currentRenderedRowCount = endIndex; // Update the count of rows currently in the DOM

    // Set up or reset Intersection Observer to load more data if not all data is displayed
    if (currentRenderedRowCount < dataToDisplay.length) {
        setupIntersectionObserver(dataToDisplay);
    } else {
        // If all data is displayed, ensure observer is disconnected
        if (observer) {
            observer.disconnect();
            observer = null;
        }
    }
}

/**
 * Sets up an Intersection Observer to detect when the user scrolls near the bottom
 * of the table, triggering the loading of more rows.
 * @param {Array} dataToObserve - The array of data being currently observed for loading more.
 */
function setupIntersectionObserver(dataToObserve) {
    const tbody = document.querySelector('#resultsBody');
    // Ensure there's at least one row in the tbody to observe
    if (tbody.children.length === 0) return;

    const lastRow = tbody.lastElementChild;

    // Disconnect previous observer if exists to avoid multiple observers
    if (observer) {
        observer.disconnect();
    }

    observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            // If the last row is visible and there's more data to load
            if (entry.isIntersecting && currentRenderedRowCount < dataToObserve.length) {
                // Disconnect observer temporarily to prevent multiple calls while loading
                observer.disconnect();
                // Load the next batch of results
                displayResults(dataToObserve, true); // Append true
            }
        });
    }, {
        // THE FIX IS HERE: Escape the square brackets for document.querySelector
        root: document.querySelector('.max-h-\\[600px\\]'),
        // Trigger when 100px from the bottom of the root element
        rootMargin: '0px 0px 100px 0px',
        // Trigger when 10% of the target element is visible
        threshold: 0.1
    });

    // Start observing the last row
    observer.observe(lastRow);
}


// --- Main Execution Logic ---
// Load manifest and initialize Fuse
fetch('manifest.json')
    .then(res => {
        // Check if the response was successful
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
    })
    .then(data => {
        // Store all fetched data and randomize its order
        fullData = data.sort(() => Math.random() - 0.5);
        displayedData = fullData; // Initially, displayedData is all data

        // Display the first batch of rows
        displayResults(displayedData, false);

        // Initialize Fuse.js for fuzzy searching
        fuse = new Fuse(fullData, {
            keys: ['Title', 'Summary'], // Keys to search within
            threshold: 0.5,             // Fuzziness of the match (0 = exact, 1 = very loose)
            minMatchCharLength: 2,      // Minimum length of the search query to trigger a match
        });

        // Get the search input element
        const searchInput = document.getElementById('searchInput');
        // Add an event listener for input changes
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim(); // Get the trimmed search query

            if (query) {
                // If there's a query, perform a search and map results to original items
                displayedData = fuse.search(query).map(r => r.item);
            } else {
                // If the query is empty, show all original data
                displayedData = fullData;
            }
            // Re-render the table with the first batch of new results (or all original data)
            displayResults(displayedData, false);
        });
    })
    .catch(err => {
        console.error('Error loading manifest.json:', err);
        // Display an error message in the table body if data loading fails
        document.querySelector('#resultsBody').innerHTML =
            '<tr><td colspan="5" class="py-4 text-red-600 text-center">Failed to load data. Please check console for details.</td></tr>';
    });
