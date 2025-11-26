/**
 * Product Importer - Frontend Application
 * ----------------------------------------
 * Handles UI interactions for product import, management, and webhooks.
 */

// ========== API Utilities ==========

const API = {
    async request(url, options = {}) {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || 'Request failed');
        }
        
        return response.json();
    },
    
    get(url) {
        return this.request(url);
    },
    
    post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
    
    put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },
    
    delete(url) {
        return this.request(url, { method: 'DELETE' });
    },
};

// ========== Toast Notifications ==========

const Toast = {
    container: null,
    
    init() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    },
    
    show(message, type = 'success', duration = 4000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        this.container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
    
    success(message) { this.show(message, 'success'); },
    error(message) { this.show(message, 'error'); },
};

// ========== Modal Management ==========

const Modal = {
    show(id) {
        document.getElementById(id).classList.add('active');
    },
    
    hide(id) {
        document.getElementById(id).classList.remove('active');
    },
    
    hideAll() {
        document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
    },
};

// ========== Tab Navigation ==========

function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    const panels = document.querySelectorAll('.tab-panel');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;
            
            tabs.forEach(t => t.classList.remove('active'));
            panels.forEach(p => p.classList.remove('active'));
            
            tab.classList.add('active');
            document.getElementById(target).classList.add('active');
            
            // Load data for the tab
            if (target === 'products-panel') loadProducts();
            if (target === 'webhooks-panel') loadWebhooks();
        });
    });
}

// ========== File Upload ==========

let uploadInProgress = false;

function initUpload() {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('file-input');
    
    // Click to select file
    zone.addEventListener('click', () => {
        if (!uploadInProgress) input.click();
    });
    
    // Drag and drop
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });
    
    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });
    
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        
        const file = e.dataTransfer.files[0];
        if (file && file.name.endsWith('.csv')) {
            handleFileUpload(file);
        } else {
            Toast.error('Please upload a CSV file');
        }
    });
    
    // File input change
    input.addEventListener('change', () => {
        if (input.files[0]) {
            handleFileUpload(input.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    if (uploadInProgress) return;
    
    uploadInProgress = true;
    const progressSection = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const progressStatus = document.getElementById('progress-status');
    const uploadBtn = document.querySelector('.upload-zone');
    
    // Show progress section
    progressSection.classList.remove('hidden');
    uploadBtn.style.opacity = '0.5';
    uploadBtn.style.pointerEvents = 'none';
    
    // Reset progress
    progressFill.style.width = '0%';
    progressPercent.textContent = '0%';
    progressStatus.textContent = 'Uploading file...';
    
    try {
        // Upload file
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/uploads', {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const result = await response.json();
        
        // Start SSE for progress updates
        streamProgress(result.task_id);
        
    } catch (error) {
        progressStatus.textContent = `Error: ${error.message}`;
        progressStatus.classList.add('text-error');
        uploadInProgress = false;
        resetUploadUI();
        Toast.error(error.message);
    }
}

function streamProgress(taskId) {
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const progressStatus = document.getElementById('progress-status');
    const progressRows = document.getElementById('progress-rows');
    
    const eventSource = new EventSource(`/api/uploads/${taskId}/stream`);
    
    eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data);
        updateProgress(data);
    });
    
    eventSource.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data);
        updateProgress(data);
        eventSource.close();
        uploadInProgress = false;
        
        if (data.status === 'completed') {
            Toast.success(data.message);
        } else {
            Toast.error(data.message || 'Import failed');
        }
        
        // Reset UI after delay
        setTimeout(resetUploadUI, 3000);
    });
    
    eventSource.addEventListener('error', () => {
        eventSource.close();
        uploadInProgress = false;
        progressStatus.textContent = 'Connection lost. Checking status...';
        
        // Fallback to polling
        pollProgress(taskId);
    });
}

function updateProgress(data) {
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const progressStatus = document.getElementById('progress-status');
    const progressRows = document.getElementById('progress-rows');
    
    progressFill.style.width = `${data.progress}%`;
    progressPercent.textContent = `${data.progress}%`;
    progressStatus.textContent = data.message;
    
    if (data.total_rows > 0) {
        progressRows.textContent = `${data.processed_rows.toLocaleString()} / ${data.total_rows.toLocaleString()} rows`;
    }
    
    // Update status class
    progressStatus.className = 'progress-status';
    if (data.status === 'completed') {
        progressStatus.classList.add('text-success');
    } else if (data.status === 'failed') {
        progressStatus.classList.add('text-error');
    }
}

async function pollProgress(taskId) {
    try {
        const data = await API.get(`/api/uploads/${taskId}`);
        updateProgress(data);
        
        if (data.status !== 'completed' && data.status !== 'failed') {
            setTimeout(() => pollProgress(taskId), 500);
        } else {
            uploadInProgress = false;
            setTimeout(resetUploadUI, 3000);
        }
    } catch (error) {
        console.error('Poll error:', error);
        uploadInProgress = false;
        resetUploadUI();
    }
}

function resetUploadUI() {
    const uploadBtn = document.querySelector('.upload-zone');
    uploadBtn.style.opacity = '1';
    uploadBtn.style.pointerEvents = 'auto';
    document.getElementById('file-input').value = '';
}

// ========== Products Management ==========

let currentPage = 1;
let currentSearch = '';
let currentActiveFilter = null;

async function loadProducts() {
    const container = document.getElementById('products-table-body');
    const pagination = document.getElementById('products-pagination');
    
    container.innerHTML = '<tr><td colspan="7" class="text-center"><div class="spinner" style="margin: 20px auto;"></div></td></tr>';
    
    try {
        let url = `/api/products?page=${currentPage}&page_size=20`;
        if (currentSearch) url += `&search=${encodeURIComponent(currentSearch)}`;
        if (currentActiveFilter !== null) url += `&active=${currentActiveFilter}`;
        
        const data = await API.get(url);
        
        if (data.items.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="7">
                        <div class="empty-state">
                            <div class="empty-state-icon">📦</div>
                            <h3>No products found</h3>
                            <p>Upload a CSV file or create a product to get started.</p>
                        </div>
                    </td>
                </tr>
            `;
            pagination.innerHTML = '';
            return;
        }
        
        // Render products
        container.innerHTML = data.items.map(product => `
            <tr>
                <td><strong>${escapeHtml(product.sku)}</strong></td>
                <td>${escapeHtml(product.name)}</td>
                <td class="text-muted">${escapeHtml(product.description || '—')}</td>
                <td>$${(product.price || 0).toFixed(2)}</td>
                <td>${product.quantity || 0}</td>
                <td>
                    <span class="badge ${product.active ? 'badge-active' : 'badge-inactive'}">
                        ${product.active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    <div class="table-actions">
                        <button class="btn btn-secondary btn-sm" onclick="editProduct(${product.id})">Edit</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteProduct(${product.id})">Delete</button>
                    </div>
                </td>
            </tr>
        `).join('');
        
        // Render pagination
        renderPagination(data, pagination);
        
    } catch (error) {
        container.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-error">
                    Error loading products: ${error.message}
                </td>
            </tr>
        `;
        Toast.error('Failed to load products');
    }
}

function renderPagination(data, container) {
    if (data.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = `
        <button class="pagination-btn" onclick="goToPage(1)" ${currentPage === 1 ? 'disabled' : ''}>«</button>
        <button class="pagination-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>‹</button>
    `;
    
    // Page numbers
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(data.total_pages, currentPage + 2);
    
    for (let i = start; i <= end; i++) {
        html += `
            <button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>
        `;
    }
    
    html += `
        <button class="pagination-btn" onclick="goToPage(${currentPage + 1})" ${currentPage >= data.total_pages ? 'disabled' : ''}>›</button>
        <button class="pagination-btn" onclick="goToPage(${data.total_pages})" ${currentPage >= data.total_pages ? 'disabled' : ''}>»</button>
    `;
    
    container.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    loadProducts();
}

function searchProducts() {
    const input = document.getElementById('product-search');
    currentSearch = input.value.trim();
    currentPage = 1;
    loadProducts();
}

function filterByActive(value) {
    currentActiveFilter = value === '' ? null : value === 'true';
    currentPage = 1;
    loadProducts();
}

// Product CRUD
function showCreateProductModal() {
    document.getElementById('product-form').reset();
    document.getElementById('product-id').value = '';
    document.getElementById('product-modal-title').textContent = 'Create Product';
    Modal.show('product-modal');
}

async function editProduct(id) {
    try {
        const product = await API.get(`/api/products/${id}`);
        
        document.getElementById('product-id').value = product.id;
        document.getElementById('product-sku').value = product.sku;
        document.getElementById('product-name').value = product.name;
        document.getElementById('product-description').value = product.description || '';
        document.getElementById('product-price').value = product.price || 0;
        document.getElementById('product-quantity').value = product.quantity || 0;
        document.getElementById('product-active').checked = product.active;
        
        // Disable SKU editing for existing products
        document.getElementById('product-sku').disabled = true;
        
        document.getElementById('product-modal-title').textContent = 'Edit Product';
        Modal.show('product-modal');
        
    } catch (error) {
        Toast.error('Failed to load product');
    }
}

async function saveProduct() {
    const id = document.getElementById('product-id').value;
    const data = {
        sku: document.getElementById('product-sku').value,
        name: document.getElementById('product-name').value,
        description: document.getElementById('product-description').value,
        price: parseFloat(document.getElementById('product-price').value) || 0,
        quantity: parseInt(document.getElementById('product-quantity').value) || 0,
        active: document.getElementById('product-active').checked,
    };
    
    try {
        if (id) {
            // Update existing
            await API.put(`/api/products/${id}`, data);
            Toast.success('Product updated successfully');
        } else {
            // Create new
            await API.post('/api/products', data);
            Toast.success('Product created successfully');
        }
        
        Modal.hide('product-modal');
        document.getElementById('product-sku').disabled = false;
        loadProducts();
        
    } catch (error) {
        Toast.error(error.message);
    }
}

async function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) return;
    
    try {
        await API.delete(`/api/products/${id}`);
        Toast.success('Product deleted');
        loadProducts();
    } catch (error) {
        Toast.error(error.message);
    }
}

function showBulkDeleteModal() {
    Modal.show('bulk-delete-modal');
}

async function confirmBulkDelete() {
    try {
        const result = await API.delete('/api/products?confirm=true');
        Toast.success(result.message);
        Modal.hide('bulk-delete-modal');
        loadProducts();
    } catch (error) {
        Toast.error(error.message);
    }
}

// ========== Webhooks Management ==========

let availableEvents = [];

async function loadWebhooks() {
    const container = document.getElementById('webhooks-list');
    
    container.innerHTML = '<div class="text-center"><div class="spinner" style="margin: 20px auto;"></div></div>';
    
    try {
        // Load available events
        availableEvents = await API.get('/api/webhooks/events');
        
        // Load webhooks
        const webhooks = await API.get('/api/webhooks');
        
        if (webhooks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔗</div>
                    <h3>No webhooks configured</h3>
                    <p>Create a webhook to receive notifications.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = webhooks.map(webhook => `
            <div class="card" style="padding: var(--space-lg);">
                <div class="flex-between">
                    <div>
                        <h3 style="margin-bottom: var(--space-xs);">
                            ${escapeHtml(webhook.url)}
                            <span class="badge ${webhook.enabled ? 'badge-enabled' : 'badge-disabled'}">
                                ${webhook.enabled ? 'Enabled' : 'Disabled'}
                            </span>
                        </h3>
                        <p class="text-muted mb-0" style="font-size: 0.9rem;">
                            Events: ${webhook.events.length > 0 ? webhook.events.join(', ') : 'None'}
                        </p>
                    </div>
                    <div class="table-actions">
                        <button class="btn btn-gold btn-sm" onclick="testWebhook(${webhook.id})">Test</button>
                        <button class="btn btn-secondary btn-sm" onclick="editWebhook(${webhook.id})">Edit</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteWebhook(${webhook.id})">Delete</button>
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        container.innerHTML = `<div class="text-center text-error">Error loading webhooks: ${error.message}</div>`;
        Toast.error('Failed to load webhooks');
    }
}

function showCreateWebhookModal() {
    document.getElementById('webhook-form').reset();
    document.getElementById('webhook-id').value = '';
    document.getElementById('webhook-modal-title').textContent = 'Create Webhook';
    
    // Render event checkboxes
    const eventsContainer = document.getElementById('webhook-events');
    eventsContainer.innerHTML = availableEvents.map(event => `
        <label class="checkbox-wrapper">
            <input type="checkbox" class="checkbox" name="events" value="${event}">
            <span>${event}</span>
        </label>
    `).join('');
    
    Modal.show('webhook-modal');
}

async function editWebhook(id) {
    try {
        const webhook = await API.get(`/api/webhooks/${id}`);
        
        document.getElementById('webhook-id').value = webhook.id;
        document.getElementById('webhook-url').value = webhook.url;
        document.getElementById('webhook-enabled').checked = webhook.enabled;
        
        // Render event checkboxes
        const eventsContainer = document.getElementById('webhook-events');
        eventsContainer.innerHTML = availableEvents.map(event => `
            <label class="checkbox-wrapper">
                <input type="checkbox" class="checkbox" name="events" value="${event}"
                    ${webhook.events.includes(event) ? 'checked' : ''}>
                <span>${event}</span>
            </label>
        `).join('');
        
        document.getElementById('webhook-modal-title').textContent = 'Edit Webhook';
        Modal.show('webhook-modal');
        
    } catch (error) {
        Toast.error('Failed to load webhook');
    }
}

async function saveWebhook() {
    const id = document.getElementById('webhook-id').value;
    const events = Array.from(document.querySelectorAll('input[name="events"]:checked'))
        .map(cb => cb.value);
    
    const data = {
        url: document.getElementById('webhook-url').value,
        events: events,
        enabled: document.getElementById('webhook-enabled').checked,
    };
    
    try {
        if (id) {
            await API.put(`/api/webhooks/${id}`, data);
            Toast.success('Webhook updated successfully');
        } else {
            await API.post('/api/webhooks', data);
            Toast.success('Webhook created successfully');
        }
        
        Modal.hide('webhook-modal');
        loadWebhooks();
        
    } catch (error) {
        Toast.error(error.message);
    }
}

async function deleteWebhook(id) {
    if (!confirm('Are you sure you want to delete this webhook?')) return;
    
    try {
        await API.delete(`/api/webhooks/${id}`);
        Toast.success('Webhook deleted');
        loadWebhooks();
    } catch (error) {
        Toast.error(error.message);
    }
}

async function testWebhook(id) {
    Toast.show('Testing webhook...', 'success', 2000);
    
    try {
        const result = await API.post(`/api/webhooks/${id}/test`, {});
        
        if (result.success) {
            Toast.success(`Success! Status: ${result.status_code}, Time: ${result.response_time_ms}ms`);
        } else {
            Toast.error(`Failed: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        Toast.error(error.message);
    }
}

// ========== Utilities ==========

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Debounce for search
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ========== Initialization ==========

document.addEventListener('DOMContentLoaded', () => {
    Toast.init();
    initTabs();
    initUpload();
    
    // Close modals on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) Modal.hideAll();
        });
    });
    
    // Close modals on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') Modal.hideAll();
    });
    
    // Debounced search
    const searchInput = document.getElementById('product-search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(searchProducts, 300));
    }
    
    // Re-enable SKU field when modal closes
    document.getElementById('product-modal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-overlay')) {
            document.getElementById('product-sku').disabled = false;
        }
    });
});