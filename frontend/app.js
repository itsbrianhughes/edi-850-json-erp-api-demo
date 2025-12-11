/**
 * Frontend Logic for EDI 850 Integration Demo
 * Handles file upload and displays processing results
 */

const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');
const parsedJsonElement = document.getElementById('parsedJson');
const transformedJsonElement = document.getElementById('transformedJson');
const apiResponseElement = document.getElementById('apiResponse');
const jobInfoElement = document.getElementById('jobInfo');
const stepStatusElement = document.getElementById('stepStatus');

// Event Listeners
uploadBtn.addEventListener('click', handleFileUpload);

// Allow drag and drop
const uploadSection = document.querySelector('.upload-section');
uploadSection.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadSection.classList.add('drag-over');
});

uploadSection.addEventListener('dragleave', () => {
    uploadSection.classList.remove('drag-over');
});

uploadSection.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadSection.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        showStatus(`File loaded: ${files[0].name}`, 'success');
    }
});

/**
 * Handle file upload and processing
 */
async function handleFileUpload() {
    const file = fileInput.files[0];

    if (!file) {
        showStatus('Please select a file first', 'error');
        return;
    }

    // Clear previous results
    clearResults();

    // Disable button during processing
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Processing...';
    uploadBtn.classList.add('processing');

    try {
        // Read file content
        const fileContent = await readFileContent(file);

        showStatus('Sending to orchestrator...', 'processing');

        // Call orchestrator endpoint
        const result = await orchestrateEDI(fileContent);

        // Display results
        displayResults(result);

        if (result.success) {
            showStatus(`✓ Processing complete! Job ID: ${result.job_id}`, 'success');
        } else {
            showStatus(`✗ Processing failed. Check details below.`, 'error');
        }

    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        console.error('Upload error:', error);

        // Display error in all panels
        const errorMsg = `Error: ${error.message}\n\nPlease check that:\n- The backend server is running (port 8000)\n- The EDI file is valid\n- CORS is properly configured`;
        parsedJsonElement.textContent = errorMsg;
        transformedJsonElement.textContent = errorMsg;
        apiResponseElement.textContent = errorMsg;
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Process EDI File';
        uploadBtn.classList.remove('processing');
    }
}

/**
 * Clear previous results
 */
function clearResults() {
    parsedJsonElement.textContent = 'Processing...';
    transformedJsonElement.textContent = 'Processing...';
    apiResponseElement.textContent = 'Processing...';
    if (jobInfoElement) jobInfoElement.textContent = '';
    if (stepStatusElement) stepStatusElement.innerHTML = '';
}

/**
 * Call orchestrator endpoint
 */
async function orchestrateEDI(ediContent) {
    const response = await fetch(`${API_BASE_URL}/api/orchestrate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ edi_content: ediContent })
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error (${response.status}): ${errorText}`);
    }

    return await response.json();
}

/**
 * Display orchestration results
 */
function displayResults(result) {
    // Display job info
    if (jobInfoElement) {
        const jobInfo = `
Job ID: ${result.job_id}
Status: ${result.success ? '✓ Success' : '✗ Failed'}
Duration: ${result.duration_seconds}s
Started: ${new Date(result.started_at).toLocaleString()}
        `.trim();
        jobInfoElement.textContent = jobInfo;
    }

    // Display step status
    if (stepStatusElement) {
        const steps = result.steps;
        let stepHtml = '<h3>Pipeline Steps:</h3><ul>';

        for (const [stepName, stepData] of Object.entries(steps)) {
            const statusEmoji = stepData.status === 'success' ? '✅' :
                               stepData.status === 'failed' ? '❌' : '⏸️';
            const stepTitle = stepName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            stepHtml += `<li><strong>${statusEmoji} ${stepTitle}</strong>: ${stepData.status}`;

            if (stepData.error) {
                stepHtml += `<br><span class="error-text">Error: ${stepData.error}</span>`;
            }

            if (stepName === 'post_to_erp' && stepData.attempts) {
                stepHtml += `<br><span class="info-text">Attempts: ${stepData.attempts}</span>`;
            }

            if (stepName === 'validate' && stepData.errors && stepData.errors.length > 0) {
                stepHtml += `<br><span class="error-text">Validation errors:</span><ul>`;
                stepData.errors.forEach(err => {
                    stepHtml += `<li class="error-text">${err}</li>`;
                });
                stepHtml += '</ul>';
            }

            stepHtml += '</li>';
        }

        stepHtml += '</ul>';
        stepStatusElement.innerHTML = stepHtml;
    }

    // Display parsed EDI data
    if (result.steps.parse && result.steps.parse.data) {
        displayJSON(parsedJsonElement, result.steps.parse.data);
    } else if (result.steps.parse && result.steps.parse.error) {
        parsedJsonElement.textContent = `❌ Parsing Error:\n${result.steps.parse.error}`;
    } else {
        parsedJsonElement.textContent = 'No parsed data available';
    }

    // Display transformed ERP payload
    if (result.steps.transform && result.steps.transform.data) {
        displayJSON(transformedJsonElement, result.steps.transform.data);
    } else if (result.steps.transform && result.steps.transform.error) {
        transformedJsonElement.textContent = `❌ Transformation Error:\n${result.steps.transform.error}`;
    } else {
        transformedJsonElement.textContent = 'No transformed data available';
    }

    // Display ERP API response
    if (result.final_result) {
        if (result.success) {
            // Success - show ERP response
            displayJSON(apiResponseElement, result.final_result);
        } else {
            // Failed - show error
            apiResponseElement.textContent = `❌ ${JSON.stringify(result.final_result, null, 2)}`;
        }
    } else if (result.steps.post_to_erp && result.steps.post_to_erp.error) {
        apiResponseElement.textContent = `❌ ERP API Error:\n${result.steps.post_to_erp.error}`;
    } else {
        apiResponseElement.textContent = 'No ERP response available';
    }
}

/**
 * Read file content as text
 */
function readFileContent(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(new Error('Failed to read file'));
        reader.readAsText(file);
    });
}

/**
 * Display formatted JSON in output panel
 */
function displayJSON(element, data) {
    element.textContent = JSON.stringify(data, null, 2);
    element.classList.remove('error');
    element.classList.add('success');
}

/**
 * Show status message
 */
function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = type;
}
