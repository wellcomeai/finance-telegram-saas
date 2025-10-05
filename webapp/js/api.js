/**
 * API Client for Finance Tracker Backend
 * Handles all HTTP requests to backend
 */

class API {
    constructor() {
        // API Base URL - определяется автоматически
        this.baseURL = this.getBaseURL();
        
        // Default headers
        this.headers = {
            'Content-Type': 'application/json'
        };

        console.log('API initialized with base URL:', this.baseURL);
    }

    /**
     * Get base URL based on environment
     */
    getBaseURL() {
        // В production используем текущий хост
        if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            return window.location.origin;
        }
        
        // В development используем localhost
        return 'http://localhost:8080';
    }

    /**
     * Get authentication headers with Telegram data
     */
    getAuthHeaders() {
        const headers = { ...this.headers };
        
        // Add Telegram init data for authentication
        const initData = window.telegramApp?.getInitData();
        if (initData) {
            headers['X-Telegram-Init-Data'] = initData;
        }

        // Add user ID
        const userId = window.telegramApp?.getUserId();
        if (userId) {
            headers['X-Telegram-User-Id'] = userId.toString();
        }

        return headers;
    }

    /**
     * Make HTTP request
     */
    async request(endpoint, options = {}) {
        try {
            const url = `${this.baseURL}${endpoint}`;
            
            const config = {
                ...options,
                headers: {
                    ...this.getAuthHeaders(),
                    ...options.headers
                }
            };

            console.log('API Request:', {
                method: config.method || 'GET',
                url,
                body: config.body
            });

            const response = await fetch(url, config);

            // Handle HTTP errors
            if (!response.ok) {
                const error = await this.handleError(response);
                throw error;
            }

            // Parse JSON response
            const data = await response.json();
            
            console.log('API Response:', data);
            
            return data;

        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    /**
     * Handle API errors
     */
    async handleError(response) {
        let errorMessage = 'Произошла ошибка при выполнении запроса';
        
        try {
            const errorData = await response.json();
            errorMessage = errorData.message || errorData.error || errorMessage;
        } catch (e) {
            // If can't parse JSON, use status text
            errorMessage = response.statusText || errorMessage;
        }

        const error = new Error(errorMessage);
        error.status = response.status;
        
        return error;
    }

    /**
     * GET request
     */
    async get(endpoint, params = {}) {
        // Add query parameters
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;

        return this.request(url, {
            method: 'GET'
        });
    }

    /**
     * POST request
     */
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT request
     */
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    // ==================== TRANSACTIONS API ====================

    /**
     * Get all transactions with filters
     */
    async getTransactions(filters = {}) {
        return this.get('/api/transactions', filters);
    }

    /**
     * Get transaction by ID
     */
    async getTransaction(id) {
        return this.get(`/api/transactions/${id}`);
    }

    /**
     * Create new transaction
     */
    async createTransaction(data) {
        return this.post('/api/transactions', data);
    }

    /**
     * Update transaction
     */
    async updateTransaction(id, data) {
        return this.put(`/api/transactions/${id}`, data);
    }

    /**
     * Delete transaction
     */
    async deleteTransaction(id) {
        return this.delete(`/api/transactions/${id}`);
    }

    // ==================== STATISTICS API ====================

    /**
     * Get monthly statistics
     */
    async getMonthlyStats(year, month) {
        return this.get('/api/stats/monthly', { year, month });
    }

    /**
     * Get category statistics
     */
    async getCategoryStats(params = {}) {
        return this.get('/api/stats/categories', params);
    }

    /**
     * Get daily totals for chart
     */
    async getDailyTotals(startDate, endDate, type = 'expense') {
        return this.get('/api/stats/daily', {
            start_date: startDate,
            end_date: endDate,
            type
        });
    }

    /**
     * Get dashboard summary
     */
    async getDashboardSummary() {
        return this.get('/api/stats/dashboard');
    }

    // ==================== CATEGORIES API ====================

    /**
     * Get all categories
     */
    async getCategories(type = null) {
        const params = type ? { type } : {};
        return this.get('/api/categories', params);
    }

    /**
     * Get expense categories
     */
    async getExpenseCategories() {
        return this.getCategories('expense');
    }

    /**
     * Get income categories
     */
    async getIncomeCategories() {
        return this.getCategories('income');
    }

    // ==================== USER API ====================

    /**
     * Get current user info
     */
    async getUserInfo() {
        return this.get('/api/user');
    }

    /**
     * Update user settings
     */
    async updateUserSettings(settings) {
        return this.put('/api/user/settings', settings);
    }

    // ==================== AI CHAT API ====================

    /**
     * Send message to AI chat
     */
    async sendAIMessage(message, newConversation = false) {
        return this.post('/api/ai/chat', {
            message,
            new_conversation: newConversation
        });
    }

    /**
     * Reset AI conversation
     */
    async resetAIConversation() {
        return this.post('/api/ai/reset');
    }

    // ==================== HELPER METHODS ====================

    /**
     * Format date for API - ИСПРАВЛЕНО: используем локальную дату без UTC конвертации
     */
    formatDate(date) {
        if (typeof date === 'string') {
            return date;
        }
        
        if (date instanceof Date) {
            // Используем локальную дату БЕЗ конвертации в UTC
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }

        // Fallback - текущая дата
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    /**
     * Parse date from API
     */
    parseDate(dateString) {
        return new Date(dateString);
    }

    /**
     * Format amount for display
     */
    formatAmount(amount) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }).format(amount);
    }

    /**
     * Format number with spaces
     */
    formatNumber(number) {
        return new Intl.NumberFormat('ru-RU').format(number);
    }

    /**
     * Get current month start and end dates
     */
    getCurrentMonthDates() {
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        
        return {
            start: this.formatDate(start),
            end: this.formatDate(end)
        };
    }

    /**
     * Get date range for period
     */
    getDateRange(period = 'month') {
        const now = new Date();
        let start, end;

        switch (period) {
            case 'week':
                start = new Date(now);
                start.setDate(now.getDate() - 7);
                end = now;
                break;

            case 'month':
                start = new Date(now.getFullYear(), now.getMonth(), 1);
                end = now;
                break;

            case 'year':
                start = new Date(now.getFullYear(), 0, 1);
                end = now;
                break;

            default:
                start = new Date(now.getFullYear(), now.getMonth(), 1);
                end = now;
        }

        return {
            start: this.formatDate(start),
            end: this.formatDate(end)
        };
    }

    /**
     * Validate transaction data
     */
    validateTransaction(data) {
        const errors = [];

        // Validate type
        if (!data.type || !['income', 'expense'].includes(data.type)) {
            errors.push('Неверный тип транзакции');
        }

        // Validate amount
        if (!data.amount || data.amount <= 0) {
            errors.push('Сумма должна быть больше нуля');
        }

        // Validate category
        if (!data.category_id) {
            errors.push('Выберите категорию');
        }

        // Validate date
        if (!data.date) {
            errors.push('Укажите дату');
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }

    /**
     * Retry request with exponential backoff
     */
    async retryRequest(requestFn, maxRetries = 3, delay = 1000) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await requestFn();
            } catch (error) {
                if (i === maxRetries - 1) throw error;
                
                console.log(`Retry ${i + 1}/${maxRetries} after ${delay}ms`);
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2; // Exponential backoff
            }
        }
    }

    /**
     * Check if online
     */
    isOnline() {
        return navigator.onLine;
    }

    /**
     * Show offline message
     */
    showOfflineMessage() {
        if (window.telegramApp) {
            window.telegramApp.showAlert('Нет подключения к интернету. Проверьте соединение.');
        } else {
            alert('Нет подключения к интернету');
        }
    }

    /**
     * Handle network error
     */
    handleNetworkError(error) {
        console.error('Network error:', error);
        
        if (!this.isOnline()) {
            this.showOfflineMessage();
            return;
        }

        // Show generic error
        if (window.telegramApp) {
            window.telegramApp.showAlert('Ошибка подключения к серверу. Попробуйте позже.');
        } else {
            alert('Ошибка подключения к серверу');
        }
    }
}

// Initialize API client
const api = new API();

// Export for use in other files
window.api = api;

// Add event listeners for online/offline
window.addEventListener('online', () => {
    console.log('Connection restored');
    if (window.telegramApp) {
        window.telegramApp.showAlert('Подключение восстановлено');
    }
});

window.addEventListener('offline', () => {
    console.log('Connection lost');
    if (window.telegramApp) {
        window.telegramApp.showAlert('Нет подключения к интернету');
    }
});

console.log('API client loaded');
