// Dashboard JavaScript for LinkedIn Management System

class LinkedInDashboard {
    constructor() {
        this.baseUrl = '';
        this.refreshInterval = null;
        this.workflowStatus = 'idle';
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
    }

    bindEvents() {
        // Automation control buttons
        document.getElementById('start-automation')?.addEventListener('click', () => this.startAutomation());
        document.getElementById('stop-automation')?.addEventListener('click', () => this.stopAutomation());
        document.getElementById('run-now')?.addEventListener('click', () => this.runWorkflowNow());

        // Refresh buttons
        document.querySelector('[onclick="refreshTrends()"]')?.addEventListener('click', () => this.loadTrends());
        document.querySelector('[onclick="refreshContent()"]')?.addEventListener('click', () => this.loadContent());
    }

    async loadInitialData() {
        await Promise.all([
            this.loadAutomationStatus(),
            this.loadMetrics(),
            this.loadTrends(),
            this.loadContent(),
            this.loadActivity()
        ]);
    }

    async makeRequest(endpoint, options = {}) {
        try {
            const response = await fetch(this.baseUrl + endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            this.showNotification(`Error: ${error.message}`, 'error');
            return null;
        }
    }

    async loadAutomationStatus() {
        const data = await this.makeRequest('/api/v1/automation/status');
        if (data) {
            this.updateAutomationStatus(data.data);
        }
    }

    async loadMetrics() {
        const data = await this.makeRequest('/api/v1/automation/metrics');
        if (data) {
            this.updateMetrics(data.data);
        }
    }

    async loadTrends() {
        const data = await this.makeRequest('/api/v1/trends?limit=10');
        if (data) {
            this.updateTrends(data.data);
        }
    }

    async loadContent() {
        const data = await this.makeRequest('/api/v1/posts?limit=10');
        if (data) {
            this.updateContent(data.data);
        }
    }

    async loadActivity() {
        const data = await this.makeRequest('/api/v1/analytics/dashboard');
        if (data) {
            this.updateActivity(data.data.recent_activities || []);
        }
    }

    updateAutomationStatus(statusData) {
        const statusElement = document.getElementById('automation-status');
        const isRunning = statusData.is_running;
        
        if (statusElement) {
            statusElement.innerHTML = isRunning 
                ? '<span class="badge bg-success">Running</span>'
                : '<span class="badge bg-secondary">Stopped</span>';
        }

        // Update system status indicator
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('system-status');
        
        if (indicator && statusText) {
            if (isRunning) {
                indicator.className = 'fas fa-circle text-success me-1';
                statusText.textContent = 'Online';
            } else {
                indicator.className = 'fas fa-circle text-secondary me-1';
                statusText.textContent = 'Stopped';
            }
        }

        // Update button states
        this.updateButtonStates(isRunning);
    }

    updateButtonStates(isRunning) {
        const startBtn = document.getElementById('start-automation');
        const stopBtn = document.getElementById('stop-automation');
        
        if (startBtn && stopBtn) {
            startBtn.disabled = isRunning;
            stopBtn.disabled = !isRunning;
        }
    }

    updateMetrics(metricsData) {
        const metrics = metricsData.metrics || {};
        
        this.updateCounter('trends-count', metrics.trends_analyzed || 0);
        this.updateCounter('content-count', metrics.content_pieces_generated || 0);
        this.updateCounter('scheduled-count', metrics.posts_by_status?.scheduled || 0);
    }

    updateCounter(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            const span = element.querySelector('span');
            if (span) {
                // Animate the number change
                this.animateCounter(span, parseInt(span.textContent) || 0, value);
            }
        }
    }

    animateCounter(element, start, end) {
        const duration = 1000; // 1 second
        const range = end - start;
        const stepTime = Math.abs(Math.floor(duration / range));
        
        if (range === 0) return;
        
        let current = start;
        const timer = setInterval(() => {
            current += range > 0 ? 1 : -1;
            element.textContent = current;
            
            if (current === end) {
                clearInterval(timer);
            }
        }, stepTime);
    }

    updateTrends(trends) {
        const container = document.getElementById('trends-list');
        if (!container) return;

        if (trends.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-search fa-2x mb-2"></i>
                    <p>No trends found yet</p>
                    <button class="btn btn-sm btn-primary" onclick="dashboard.runWorkflowNow()">
                        <i class="fas fa-bolt me-1"></i>Analyze Trends
                    </button>
                </div>
            `;
            return;
        }

        const trendsHtml = trends.map(trend => {
            const score = trend.relevance_score || 0;
            const scoreClass = score > 0.7 ? 'high' : score > 0.4 ? 'medium' : 'low';
            const hashtags = trend.hashtags || [];
            
            return `
                <div class="trend-item fade-in">
                    <div class="trend-topic">${trend.topic}</div>
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="trend-score ${scoreClass}">
                            Score: ${(score * 100).toFixed(0)}%
                        </span>
                        <small class="text-muted">${this.formatDate(trend.detected_at)}</small>
                    </div>
                    ${hashtags.length > 0 ? `
                        <div class="trend-hashtags">
                            ${hashtags.slice(0, 5).map(tag => `<span class="hashtag">#${tag}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        container.innerHTML = trendsHtml;
    }

    updateContent(posts) {
        const container = document.getElementById('content-list');
        if (!container) return;

        if (posts.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-edit fa-2x mb-2"></i>
                    <p>No content generated yet</p>
                    <button class="btn btn-sm btn-success" onclick="dashboard.runWorkflowNow()">
                        <i class="fas fa-magic me-1"></i>Generate Content
                    </button>
                </div>
            `;
            return;
        }

        const contentHtml = posts.map(post => {
            const preview = post.content.length > 150 
                ? post.content.substring(0, 150) + '...' 
                : post.content;
            
            return `
                <div class="content-item fade-in">
                    <div class="content-preview" style="cursor: pointer;" 
                        onclick="showFullContent(${post.id})">
                        ${preview}
                        ${post.content.length > 150 ? '<br><small class="text-primary"><i class="fas fa-expand me-1"></i>Click to view full content</small>' : ''}
                    </div>  
                    <div class="content-meta">
                        <div>
                            <span class="content-status ${post.status}">${post.status}</span>
                            ${post.hashtags && post.hashtags.length > 0 ? `
                                <div class="mt-1">
                                    ${post.hashtags.slice(0, 3).map(tag => `<span class="hashtag">#${tag}</span>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                        <div class="text-end">
                            ${post.readability_score ? `
                                <div class="quality-score text-muted">
                                    Quality: ${Math.round(post.readability_score)}%
                                </div>
                            ` : ''}
                            <small class="text-muted">${this.formatDate(post.created_at)}</small>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = contentHtml;
    }

    updateActivity(activities) {
        const container = document.getElementById('activity-log');
        if (!container) return;

        if (activities.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-clock fa-2x mb-2"></i>
                    <p>No recent activity</p>
                </div>
            `;
            return;
        }

        const activityHtml = activities.map(activity => {
            const iconClass = activity.status === 'success' ? 'success' : 
                            activity.status === 'error' ? 'error' : 'info';
            const icon = activity.status === 'success' ? 'check' : 
                        activity.status === 'error' ? 'times' : 'info';
            
            return `
                <div class="activity-item">
                    <div class="activity-icon ${iconClass}">
                        <i class="fas fa-${icon}"></i>
                    </div>
                    <div class="activity-content">
                        <p class="activity-title">${activity.agent} - ${activity.activity}</p>
                        <p class="activity-time">${this.formatDate(activity.timestamp)}</p>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = activityHtml;
    }

    async startAutomation() {
        this.showLoading('start-automation');
        const data = await this.makeRequest('/api/v1/automation/start', { method: 'POST' });
        this.hideLoading('start-automation');
        
        if (data) {
            this.showNotification('Automation started successfully!', 'success');
            await this.loadAutomationStatus();
        }
    }

    async stopAutomation() {
        this.showLoading('stop-automation');
        const data = await this.makeRequest('/api/v1/automation/stop', { method: 'POST' });
        this.hideLoading('stop-automation');
        
        if (data) {
            this.showNotification('Automation stopped successfully!', 'warning');
            await this.loadAutomationStatus();
        }
    }

    async runWorkflowNow() {
        this.showLoading('run-now');
        this.updateWorkflowProgress('running');
        
        const data = await this.makeRequest('/api/v1/automation/run-now', { method: 'POST' });
        this.hideLoading('run-now');
        
        if (data) {
            this.showNotification('Workflow started! Results will appear shortly.', 'info');
            
            // Simulate workflow progress
            this.simulateWorkflowProgress();
            
            // Refresh data after workflow completes
            setTimeout(() => {
                this.loadInitialData();
                this.updateWorkflowProgress('completed');
            }, 5000);
        } else {
            this.updateWorkflowProgress('error');
        }
    }

    simulateWorkflowProgress() {
        const steps = ['trends', 'filter', 'content', 'review', 'schedule'];
        let currentStep = 0;

        const progressInterval = setInterval(() => {
            if (currentStep < steps.length) {
                this.updateStepStatus(steps[currentStep], 'active');
                
                if (currentStep > 0) {
                    this.updateStepStatus(steps[currentStep - 1], 'completed');
                }
                
                currentStep++;
            } else {
                clearInterval(progressInterval);
                steps.forEach(step => this.updateStepStatus(step, 'completed'));
            }
        }, 1000);
    }

    updateWorkflowProgress(status) {
        const steps = ['trends', 'filter', 'content', 'review', 'schedule'];
        
        steps.forEach(step => {
            this.updateStepStatus(step, status === 'running' ? 'pending' : 
                                       status === 'completed' ? 'completed' : 
                                       status === 'error' ? 'error' : 'pending');
        });
    }

    updateStepStatus(stepId, status) {
        const stepElement = document.getElementById(`step-${stepId}`);
        if (!stepElement) return;

        // Remove all status classes
        stepElement.classList.remove('active', 'completed', 'error', 'pending');
        
        // Add new status class
        stepElement.classList.add(status);
    }

    showLoading(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = true;
            const originalText = button.innerHTML;
            button.setAttribute('data-original-text', originalText);
            button.innerHTML = '<span class="loading"></span> Processing...';
        }
    }

    hideLoading(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = false;
            const originalText = button.getAttribute('data-original-text');
            if (originalText) {
                button.innerHTML = originalText;
            }
        }
    }

    showNotification(message, type = 'info') {
        const toast = document.getElementById('notification-toast');
        const messageElement = document.getElementById('toast-message');
        
        if (toast && messageElement) {
            messageElement.textContent = message;
            
            // Update toast styling based on type
            toast.className = `toast ${type === 'error' ? 'bg-danger text-white' : 
                                     type === 'success' ? 'bg-success text-white' : 
                                     type === 'warning' ? 'bg-warning text-dark' : 'bg-info text-white'}`;
            
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
        }
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }

    refreshDashboard() {
        this.loadInitialData();
    }
}

// Global functions for HTML onclick events
function refreshTrends() {
    dashboard.loadTrends();
}

function refreshContent() {
    dashboard.loadContent();
}

function initializeDashboard() {
    window.dashboard = new LinkedInDashboard();
}

// Auto-refresh every 30 seconds
function refreshDashboard() {
    if (window.dashboard) {
        window.dashboard.refreshDashboard();
    }
}

// REPLACE the showFullContent function with:
async function showFullContent(postId) {
    try {
        // Fetch the full post data
        const response = await fetch(`/api/v1/posts/${postId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            const post = data.data;
            const modal = document.getElementById('contentModal');
            const contentText = document.getElementById('full-content-text');
            const contentHashtags = document.getElementById('content-hashtags');
            
            if (contentText && contentHashtags) {
                contentText.innerHTML = `<p style="white-space: pre-wrap; line-height: 1.6;">${post.content}</p>`;
                
                if (post.hashtags && post.hashtags.length > 0) {
                    contentHashtags.innerHTML = `
                        <strong>Hashtags:</strong><br>
                        ${post.hashtags.map(tag => `<span class="hashtag">#${tag}</span>`).join(' ')}
                    `;
                } else {
                    contentHashtags.innerHTML = '';
                }
                
                const bsModal = new bootstrap.Modal(modal);
                bsModal.show();
            }
        }
    } catch (error) {
        console.error('Error loading full content:', error);
        dashboard.showNotification('Error loading content', 'error');
    }
}
window.showFullContent = showFullContent;