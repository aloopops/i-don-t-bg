document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const uploadPreview = document.getElementById('uploadPreview');
    const previewImage = document.getElementById('previewImage');
    const changeImage = document.getElementById('changeImage');
    const processButton = document.getElementById('processButton');
    const processingIndicator = document.getElementById('processingIndicator');
    const processingProgress = document.getElementById('processingProgress');
    const resultsSection = document.getElementById('resultsSection');
    const originalImage = document.getElementById('originalImage');
    const processedImage = document.getElementById('processedImage');
    const downloadLink = document.getElementById('downloadLink');
    const newImageBtn = document.getElementById('newImageBtn');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const apiUrlSection = document.getElementById('apiUrlSection');
    const apiUrlDisplay = document.getElementById('apiUrlDisplay');
    const copyApiUrl = document.getElementById('copyApiUrl');
    
    // File handling variables
    let selectedFile = null;
    
    // Event Listeners for drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('dragover');
    }
    
    function unhighlight() {
        dropArea.classList.remove('dragover');
    }
    
    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            handleFiles(files[0]);
        }
    }
    
    // Handle file input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFiles(this.files[0]);
        }
    });
    
    // Click on drop area to trigger file input
    dropArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    // Handle files
    function handleFiles(file) {
        // Check if file is an image
        if (!file.type.match('image.*')) {
            showError('Please select an image file (PNG, JPG, JPEG, WEBP)');
            return;
        }
        
        // Limit file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            showError('File is too large. Maximum size is 10MB');
            return;
        }
        
        selectedFile = file;
        
        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            uploadPreview.style.display = 'block';
            dropArea.style.display = 'none';
            hideError();
        };
        reader.readAsDataURL(file);
    }
    
    // Change image button
    changeImage.addEventListener('click', function() {
        uploadPreview.style.display = 'none';
        dropArea.style.display = 'block';
        selectedFile = null;
        previewImage.src = '';
    });
    
    // Form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!selectedFile) {
            showError('Please select an image first');
            return;
        }
        
        // Show processing indicator
        uploadPreview.style.display = 'none';
        processingIndicator.style.display = 'block';
        hideError();
        
        // Reset progress animation
        processingProgress.style.width = '0%';
        void processingProgress.offsetWidth; // Trigger reflow to restart animation
        processingProgress.style.width = '90%';
        
        // Create FormData
        const formData = new FormData();
        formData.append('image', selectedFile);
        
        // Send to server
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            // Check if response is ok
            if (!response.ok) {
                // Try to parse as JSON first
                return response.text().then(text => {
                    let errorMsg = 'Unknown error occurred';
                    try {
                        // Try to parse as JSON
                        const data = JSON.parse(text);
                        if (data && data.error) {
                            errorMsg = data.error;
                        }
                    } catch (e) {
                        // If JSON parsing fails, use text as error
                        if (text && text.length < 100) {
                            errorMsg = text;
                        }
                    }
                    throw new Error(errorMsg);
                });
            }
            
            // Parse successful response
            return response.text().then(text => {
                try {
                    return JSON.parse(text);
                } catch (e) {
                    throw new Error('Invalid response from server. Please try again.');
                }
            });
        })
        .then(data => {
            // Complete progress bar
            processingProgress.style.width = '100%';
            
            // Display results after a short delay
            setTimeout(() => {
                processingIndicator.style.display = 'none';
                resultsSection.style.display = 'block';
                
                // Set images
                originalImage.src = data.original;
                processedImage.src = data.processed;
                
                // Set download link
                downloadLink.href = data.download;
                
                // Handle API URL if available
                if (data.api_url) {
                    apiUrlDisplay.value = data.api_url;
                    apiUrlSection.style.display = 'block';
                } else {
                    apiUrlSection.style.display = 'none';
                }
            }, 500);
        })
        .catch(error => {
            console.error('Error:', error);
            processingIndicator.style.display = 'none';
            uploadPreview.style.display = 'block';
            showError(error.message || 'An unexpected error occurred. Please try again.');
        });
    });
    
    // New image button
    newImageBtn.addEventListener('click', function() {
        resetApp();
    });
    
    // Error handling
    function showError(message) {
        errorMessage.textContent = message;
        errorAlert.style.display = 'block';
    }
    
    function hideError() {
        errorAlert.style.display = 'none';
    }
    
    // Copy API URL to clipboard
    copyApiUrl.addEventListener('click', function() {
        apiUrlDisplay.select();
        document.execCommand('copy');
        
        // Show feedback
        const originalText = copyApiUrl.innerHTML;
        copyApiUrl.innerHTML = '<i class="fas fa-check"></i>';
        setTimeout(() => {
            copyApiUrl.innerHTML = originalText;
        }, 1500);
    });
    
    // Reset application state
    function resetApp() {
        resultsSection.style.display = 'none';
        uploadPreview.style.display = 'none';
        dropArea.style.display = 'block';
        apiUrlSection.style.display = 'none';
        hideError();
        selectedFile = null;
        previewImage.src = '';
        originalImage.src = '';
        processedImage.src = '';
        apiUrlDisplay.value = '';
    }
});
