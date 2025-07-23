// Document Analyzer JavaScript - Enhanced met Markdown & Export
document.addEventListener('DOMContentLoaded', function() {
    console.log('ActiZ Document Analyzer - Enhanced Version loaded');
    
    const uploadForm = document.getElementById('uploadForm');
    const fileInput1 = document.getElementById('fileInput1');
    const fileInput2 = document.getElementById('fileInput2');
    const uploadButton = uploadForm.querySelector('button[type="submit"]');
    const uploadText = document.getElementById('uploadText');
    const uploadSpinner = document.getElementById('uploadSpinner');
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');
    const resetBtn = document.getElementById('resetBtn');
    
    // Export dropdown functionality
    let currentAnalysisData = null;
    
    // Form submission handler voor twee documenten
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Validation voor beide bestanden
        if (!fileInput1.files[0]) {
            showAlert('Selecteer eerst het originele document (Document 1)', 'warning');
            return;
        }
        
        if (!fileInput2.files[0]) {
            showAlert('Selecteer eerst het bijgewerkte document (Document 2)', 'warning');
            return;
        }
        
        // UI feedback met enhanced loading
        setUploadingState(true);
        showLoadingState();
        
        try {
            // Create form data voor beide bestanden
            const formData = new FormData();
            formData.append('file1', fileInput1.files[0]);
            formData.append('file2', fileInput2.files[0]);
            formData.append('analysis_type', 'version_compare');
            
            // Send to backend
            const response = await fetch('/compare', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                currentAnalysisData = result; // Store voor export
                showComparisonResults(result);
                showAlert('✅ Versie vergelijking succesvol uitgevoerd!', 'success');
            } else {
                showAlert(result.error || 'Er is een fout opgetreden', 'danger');
                hideResults();
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            showAlert('Verbindingsfout. Probeer het opnieuw.', 'danger');
            hideResults();
        } finally {
            setUploadingState(false);
        }
    });
    
    // File change handlers voor beide inputs met drag & drop
    setupFileInput(fileInput1, 'Document 1 (Originele versie)');
    setupFileInput(fileInput2, 'Document 2 (Bijgewerkte versie)');
    
    // Reset button handler
    resetBtn.addEventListener('click', function() {
        // Reset form
        uploadForm.reset();
        
        // Hide results
        hideResults();
        
        // Clear current data
        currentAnalysisData = null;
        
        // Show confirmation
        showAlert('🔄 Formulier gereset - klaar voor nieuwe analyse', 'info');
    });
    
    // Export functionality
    document.addEventListener('click', function(e) {
        if (e.target.id === 'exportBtn') {
            toggleExportDropdown();
        } else if (e.target.closest('.export-option')) {
            handleExportOption(e.target.closest('.export-option').dataset.type);
        } else {
            // Close dropdown when clicking elsewhere
            const dropdown = document.querySelector('.export-dropdown');
            if (dropdown) {
                dropdown.classList.remove('show');
            }
        }
    });
    
    function setupFileInput(input, label) {
        const container = input.parentElement;
        
        // File change handler
        input.addEventListener('change', function() {
            validateFile(this, label);
        });
        
        // Drag & drop functionality
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            container.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            container.addEventListener(eventName, () => container.classList.add('drag-over'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            container.addEventListener(eventName, () => container.classList.remove('drag-over'), false);
        });
        
        container.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                input.files = files;
                validateFile(input, label);
            }
        });
    }
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Helper function voor file validatie
    function validateFile(input, label) {
        const file = input.files[0];
        if (file) {
            // Validate file size (16MB limit)
            if (file.size > 16 * 1024 * 1024) {
                showAlert(`${label} is te groot (maximum 16MB)`, 'warning');
                input.value = '';
                return;
            }
            
            // Visual feedback
            const container = input.parentElement;
            container.classList.add('file-selected');
            
            console.log(`${label} selected: ${file.name} (${formatFileSize(file.size)})`);
        }
    }
    
    function setUploadingState(isUploading) {
        uploadForm.classList.toggle('uploading', isUploading);
        uploadButton.disabled = isUploading;
        
        if (isUploading) {
            uploadText.innerHTML = '<i class="fas fa-sync-alt fa-spin me-2"></i>Vergelijken...';
            uploadSpinner.classList.remove('d-none');
        } else {
            uploadText.innerHTML = '<i class="fas fa-search me-2"></i>Versies Vergelijken';
            uploadSpinner.classList.add('d-none');
        }
    }
    
    function showLoadingState() {
        resultsContent.innerHTML = `
            <div class="analysis-loading">
                <div class="loading-spinner"></div>
                <h5>🤖 AI aan het werk...</h5>
                <p class="text-muted">Documenten worden vergeleken met Azure OpenAI</p>
            </div>
        `;
        resultsSection.classList.remove('d-none');
    }
    
    // Enhanced comparison results met markdown rendering
    function showComparisonResults(result) {
        const analysisData = result.analysis_result;
        
        let resultHtml = `
            <div class="analysis-result">
                <!-- Document Stats met Progress Bars -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="doc-stats">
                            <h6><i class="fas fa-file-alt text-primary me-2"></i>${result.filename1}</h6>
                            <div class="d-flex justify-content-between small text-muted mb-1">
                                <span>Woorden: ${result.stats1?.word_count || 0}</span>
                                <span>Karakters: ${result.stats1?.char_count || 0}</span>
                            </div>
                            <div class="progress progress-custom mb-2">
                                <div class="progress-bar bg-secondary" style="width: ${Math.min((result.stats1?.word_count || 0) / 1000 * 100, 100)}%"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="doc-stats">
                            <h6><i class="fas fa-file-alt text-success me-2"></i>${result.filename2}</h6>
                            <div class="d-flex justify-content-between small text-muted mb-1">
                                <span>Woorden: ${result.stats2?.word_count || 0}</span>
                                <span>Karakters: ${result.stats2?.char_count || 0}</span>
                            </div>
                            <div class="progress progress-custom mb-2">
                                <div class="progress-bar bg-success" style="width: ${Math.min((result.stats2?.word_count || 0) / 1000 * 100, 100)}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Analysis Status -->
                <div class="mb-3">
                    ${analysisData.demo_mode ? 
                        '<div class="alert alert-info"><i class="fas fa-flask me-2"></i><small>🧪 Demo modus actief</small></div>' : 
                        '<div class="alert alert-success"><i class="fas fa-robot me-2"></i><small>🤖 Azure OpenAI versievergelijking</small></div>'
                    }
                </div>
                
                <!-- Rendered Markdown Content -->
                <div class="mt-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6><i class="fas fa-chart-line me-2"></i>Vergelijkingsresultaat</h6>
                        <div class="export-group">
                            <button class="btn btn-sm btn-outline-primary" id="exportBtn">
                                <i class="fas fa-download me-1"></i>Export
                            </button>
                            <div class="export-dropdown">
                                <button class="export-option" data-type="copy">
                                    <i class="fas fa-copy me-2"></i>Kopieer naar Klembord
                                </button>
                                <button class="export-option" data-type="pdf">
                                    <i class="fas fa-file-pdf me-2"></i>Download als PDF
                                </button>
                                <button class="export-option" data-type="print">
                                    <i class="fas fa-print me-2"></i>Printen
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="analysis-content markdown-content" style="background: #f8f9fa; padding: 1.5rem; border-radius: 8px; line-height: 1.6;">
                        ${marked.parse(analysisData.result)}
                    </div>
                </div>
                
                <!-- Document Previews - Collapsible -->
                ${result.text_preview1 || result.text_preview2 ? `
                    <div class="mt-4">
                        <div class="row">
                            ${result.text_preview1 ? `
                                <div class="col-md-6">
                                    <div class="card">
                                        <div class="card-header py-2">
                                            <button class="btn btn-sm btn-link p-0 text-decoration-none" type="button" data-bs-toggle="collapse" data-bs-target="#preview1">
                                                <i class="fas fa-file-alt me-1"></i>Preview Document 1
                                                <i class="fas fa-chevron-down ms-1"></i>
                                            </button>
                                        </div>
                                        <div class="collapse" id="preview1">
                                            <div class="card-body">
                                                <div class="text-muted small" style="white-space: pre-line; max-height: 200px; overflow-y: auto; font-family: monospace;">
                                                    ${result.text_preview1}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                            ${result.text_preview2 ? `
                                <div class="col-md-6">
                                    <div class="card">
                                        <div class="card-header py-2">
                                            <button class="btn btn-sm btn-link p-0 text-decoration-none" type="button" data-bs-toggle="collapse" data-bs-target="#preview2">
                                                <i class="fas fa-file-alt me-1"></i>Preview Document 2
                                                <i class="fas fa-chevron-down ms-1"></i>
                                            </button>
                                        </div>
                                        <div class="collapse" id="preview2">
                                            <div class="card-body">
                                                <div class="text-muted small" style="white-space: pre-line; max-height: 200px; overflow-y: auto; font-family: monospace;">
                                                    ${result.text_preview2}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
        
        resultsContent.innerHTML = resultHtml;
        resultsSection.classList.remove('d-none');
        
        // Scroll to results with smooth animation
        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        }, 100);
    }
    
    function toggleExportDropdown() {
        const dropdown = document.querySelector('.export-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('show');
        }
    }
    
    function handleExportOption(type) {
        if (!currentAnalysisData) {
            showAlert('❌ Geen analyse data beschikbaar voor export', 'error');
            return;
        }
        
        const title = `Versie Vergelijking - ${currentAnalysisData.filename1} vs ${currentAnalysisData.filename2}`;
        const content = currentAnalysisData.analysis_result.result;
        
        switch (type) {
            case 'copy':
                window.exportFunctions.copyToClipboard(content);
                break;
            case 'pdf':
                window.exportFunctions.exportToPDF(title, content);
                break;
            case 'print':
                window.exportFunctions.printAnalysis();
                break;
        }
        
        // Close dropdown
        document.querySelector('.export-dropdown').classList.remove('show');
    }
    
    // Backward compatibility - oude showResults functie voor fallback
    function showResults(result) {
        // Fallback naar nieuwe functie
        if (result.filename1 && result.filename2) {
            showComparisonResults(result);
            return;
        }
        
        // Oude single document flow
        const analysisData = result.analysis_result;
    
        let resultHtml = '';
    
        if (analysisData && analysisData.result) {
            resultHtml = `
                <div class="analysis-result">
                    <h6><i class="fas fa-file-alt me-2"></i>Bestand: ${result.filename}</h6>
                    <p><strong>📊 Analyse Type:</strong> ${result.analysis_type}</p>
                    <p><strong>📈 Statistieken:</strong> ${analysisData.word_count} woorden, ${analysisData.char_count} karakters</p>
                
                    ${analysisData.demo_mode ? 
                        '<div class="alert alert-info"><small>🧪 Demo modus actief</small></div>' : 
                        '<div class="alert alert-success"><small>🤖 Azure OpenAI analyse</small></div>'
                    }
                
                    <div class="mt-3">
                        <h6>🔍 Analyse Resultaat:</h6>
                        <div class="analysis-content markdown-content" style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">
                            ${marked.parse(analysisData.result)}
                        </div>
                    </div>
                
                    ${result.text_preview ? `
                        <details class="mt-3">
                            <summary>📝 Document Preview</summary>
                            <div class="text-muted small mt-2" style="white-space: pre-line;">
                                ${result.text_preview}
                            </div>
                        </details>
                    ` : ''}
                </div>
            `;
        } else {
            resultHtml = `
                <div class="analysis-result">
                    <h6><i class="fas fa-file-alt me-2"></i>Bestand: ${result.filename}</h6>
                    <p><strong>Status:</strong> ${result.message || 'Verwerkt'}</p>
                    <div class="mt-3">
                        <small class="text-muted">
                            ⚠️ Onverwacht response format - check server logs
                        </small>
                    </div>
                </div>
            `;
        }
    
        resultsContent.innerHTML = resultHtml;
        resultsSection.classList.remove('d-none');
    
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
    
    function hideResults() {
        resultsSection.classList.add('d-none');
    }
    
    function showAlert(message, type = 'info') {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of main content
        const main = document.querySelector('main');
        main.insertBefore(alertDiv, main.firstChild);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
});