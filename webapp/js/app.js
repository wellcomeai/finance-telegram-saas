/**
 * Finance Tracker Main Application
 * Core logic and UI management
 */

class FinanceApp {
    constructor() {
        this.currentSection = 'dashboard';
        this.transactions = [];
        this.categories = [];
        this.stats = {};
        this.charts = {};
        this.currentTransaction = null;
        this.filters = {
            type: null,
            category: null,
            dateFrom: null,
            dateTo: null
        };

        this.init();
    }

    /**
     * Initialize application
     */
    async init() {
        try {
            console.log('Initializing Finance Tracker...');

            // Load categories first
            await this.loadCategories();

            // Setup event listeners
            this.setupEventListeners();

            // Initialize UI
            this.initializeUI();

            // Setup charts BEFORE loading data
            this.setupCharts();

            // Load initial data AFTER charts are ready
            await this.loadDashboard();

            console.log('Finance Tracker initialized successfully');

        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Ошибка инициализации приложения');
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Set today's date as default
        const dateInput = document.getElementById('transactionDate');
        if (dateInput) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }

        // Listen for visibility change
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.refreshCurrentSection();
            }
        });
    }

    /**
     * Initialize UI components
     */
    initializeUI() {
        // Set initial section
        this.switchSection('dashboard');
    }

    // ==================== NAVIGATION ====================

    /**
     * Switch between sections
     */
    switchSection(sectionName) {
        try {
            // Haptic feedback
            if (window.telegramApp) {
                window.telegramApp.hapticSelection();
            }

            // Hide all sections
            document.querySelectorAll('.section').forEach(section => {
                section.classList.remove('active');
            });

            // Show selected section
            const section = document.getElementById(sectionName);
            if (section) {
                section.classList.add('active');
            }

            // Update navigation
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });

            const navItem = document.querySelector(`.nav-item[onclick*="${sectionName}"]`);
            if (navItem) {
                navItem.classList.add('active');
            }

            // Update current section
            this.currentSection = sectionName;

            // Load section data
            this.loadSectionData(sectionName);

        } catch (error) {
            console.error('Switch section error:', error);
        }
    }

    /**
     * Load data for specific section
     */
    async loadSectionData(sectionName) {
        switch (sectionName) {
            case 'dashboard':
                await this.loadDashboard();
                break;
            case 'transactions':
                await this.loadAllTransactions();
                break;
            case 'stats':
                await this.loadStatistics();
                break;
        }
    }

    /**
     * Refresh current section
     */
    async refreshCurrentSection() {
        await this.loadSectionData(this.currentSection);
    }

    // ==================== DATE FILTER ====================

    /**
     * Get date filter parameters based on current filter
     */
    getDateFilterParams() {
        const now = new Date();
        let startDate, endDate;

        // Get current filter from global function
        const currentFilter = window.getCurrentDateFilter ? window.getCurrentDateFilter() : 'today';

        switch (currentFilter) {
            case 'today':
                startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
                break;

            case 'week':
                startDate = new Date(now);
                startDate.setDate(now.getDate() - 7);
                endDate = now;
                break;

            case 'month':
                startDate = new Date(now.getFullYear(), now.getMonth(), 1);
                endDate = now;
                break;

            case 'year':
                startDate = new Date(now.getFullYear(), 0, 1);
                endDate = now;
                break;

            case 'all':
                // Don't apply date filter for "all"
                return {};

            default:
                startDate = new Date(now.getFullYear(), now.getMonth(), 1);
                endDate = now;
        }

        return {
            start_date: window.api.formatDate(startDate),
            end_date: window.api.formatDate(endDate)
        };
    }

    // ==================== DATA LOADING ====================

    /**
     * Load categories
     */
    async loadCategories() {
        try {
            const response = await window.api.getCategories();
            this.categories = response.categories || response || [];
            console.log('Categories loaded:', this.categories.length);
        } catch (error) {
            console.error('Load categories error:', error);
            // Use fallback categories from constants
            this.categories = this.getFallbackCategories();
        }
    }

    /**
     * Get fallback categories if API fails
     */
    getFallbackCategories() {
        return [
            // Expense categories
            { id: 1, name: 'Продукты', icon: '🍔', type: 'expense' },
            { id: 2, name: 'Рестораны и кафе', icon: '🍕', type: 'expense' },
            { id: 3, name: 'Транспорт', icon: '🚗', type: 'expense' },
            { id: 4, name: 'Топливо', icon: '⛽', type: 'expense' },
            { id: 5, name: 'Жилье', icon: '🏠', type: 'expense' },
            { id: 6, name: 'Покупки', icon: '🛒', type: 'expense' },
            { id: 7, name: 'Здоровье и аптека', icon: '💊', type: 'expense' },
            { id: 8, name: 'Образование', icon: '🎓', type: 'expense' },
            { id: 9, name: 'Развлечения', icon: '🎮', type: 'expense' },
            { id: 10, name: 'Связь и интернет', icon: '📱', type: 'expense' },
            { id: 11, name: 'Спорт и фитнес', icon: '🏋️', type: 'expense' },
            { id: 12, name: 'Путешествия', icon: '✈️', type: 'expense' },
            { id: 13, name: 'Подарки', icon: '🎁', type: 'expense' },
            { id: 14, name: 'Красота и уход', icon: '💇', type: 'expense' },
            { id: 15, name: 'Прочее', icon: '❓', type: 'expense' },
            // Income categories
            { id: 16, name: 'Зарплата', icon: '💰', type: 'income' },
            { id: 17, name: 'Фриланс/Подработка', icon: '💼', type: 'income' },
            { id: 18, name: 'Подарки/Возвраты', icon: '🎁', type: 'income' },
            { id: 19, name: 'Инвестиции', icon: '📈', type: 'income' },
            { id: 20, name: 'Другие доходы', icon: '❓', type: 'income' }
        ];
    }

    /**
     * Load dashboard data
     */
    async loadDashboard() {
        try {
            // Clear container first
            const container = document.getElementById('recentTransactions');
            if (container) container.innerHTML = '';
            
            this.showLoading('recentTransactions');

            // Get date filter params
            const dateParams = this.getDateFilterParams();
            
            // Load transactions with date filter
            const response = await window.api.getTransactions({
                ...dateParams,
                limit: 100
            });

            this.transactions = response.transactions || response || [];

            // Calculate stats
            this.calculateStats();

            // Update UI
            this.updateBalanceCard();
            this.updateQuickStats();
            this.renderRecentTransactions();
            this.updateExpenseChart();

            this.hideLoading('recentTransactions');

        } catch (error) {
            console.error('Load dashboard error:', error);
            this.hideLoading('recentTransactions');
            this.showEmptyState('recentTransactions', 'Ошибка загрузки данных');
        }
    }

    /**
     * Load all transactions
     */
    async loadAllTransactions() {
        try {
            // Clear container first to remove skeleton loaders
            const container = document.getElementById('allTransactions');
            if (container) container.innerHTML = '';
            
            this.showLoading('allTransactions');

            // Get date filter params
            const dateParams = this.getDateFilterParams();

            // Build filters object - only add non-null values
            const filters = {};
            if (this.filters.type) filters.type = this.filters.type;
            if (this.filters.category) filters.category_id = this.filters.category;
            if (this.filters.dateFrom) filters.start_date = this.filters.dateFrom;
            if (this.filters.dateTo) filters.end_date = this.filters.dateTo;

            const response = await window.api.getTransactions({
                ...dateParams,
                limit: 100,
                ...filters
            });

            this.transactions = response.transactions || response || [];

            this.renderAllTransactions();
            this.hideLoading('allTransactions');

        } catch (error) {
            console.error('Load transactions error:', error);
            this.hideLoading('allTransactions');
            this.showEmptyState('allTransactions', 'Ошибка загрузки транзакций');
        }
    }

    /**
     * Load transactions (called from date filter)
     */
    async loadTransactions() {
        // Reload current section data
        await this.loadSectionData(this.currentSection);
    }

    /**
     * Update dashboard (called from date filter)
     */
    async updateDashboard() {
        if (this.currentSection === 'dashboard') {
            await this.loadDashboard();
        }
    }

    /**
     * Load statistics
     */
    async loadStatistics() {
        try {
            // Get date filter params
            const dateParams = this.getDateFilterParams();

            // Use current date range if no filter applied
            const startDate = dateParams.start_date || window.api.getDateRange('month').start;
            const endDate = dateParams.end_date || window.api.getDateRange('month').end;

            // Load category stats
            const categoryStats = await window.api.getCategoryStats({
                start_date: startDate,
                end_date: endDate,
                type: 'expense'
            });

            // Load daily totals
            const dailyTotals = await window.api.getDailyTotals(
                startDate,
                endDate,
                'expense'
            );

            // Update charts
            this.updateCategoryChart(categoryStats);
            this.updateTrendChart(dailyTotals);
            this.renderTopCategories(categoryStats);

        } catch (error) {
            console.error('Load statistics error:', error);
            this.showError('Ошибка загрузки статистики');
        }
    }

    /**
     * Calculate statistics from transactions
     */
    calculateStats() {
        this.stats = {
            totalIncome: 0,
            totalExpense: 0,
            balance: 0,
            count: this.transactions.length,
            avgExpense: 0,
            topCategory: '—'
        };

        const categoryTotals = {};

        this.transactions.forEach(transaction => {
            const amount = parseFloat(transaction.amount);

            if (transaction.type === 'income') {
                this.stats.totalIncome += amount;
            } else {
                this.stats.totalExpense += amount;
                
                // Track category totals
                const categoryName = transaction.category_name || 'Прочее';
                categoryTotals[categoryName] = (categoryTotals[categoryName] || 0) + amount;
            }
        });

        this.stats.balance = this.stats.totalIncome - this.stats.totalExpense;

        // Calculate average expense
        const expenseCount = this.transactions.filter(t => t.type === 'expense').length;
        if (expenseCount > 0) {
            this.stats.avgExpense = this.stats.totalExpense / expenseCount;
        }

        // Find top category
        let maxAmount = 0;
        Object.keys(categoryTotals).forEach(category => {
            if (categoryTotals[category] > maxAmount) {
                maxAmount = categoryTotals[category];
                this.stats.topCategory = category;
            }
        });
    }

    // ==================== UI UPDATES ====================

    /**
     * Update balance card
     */
    updateBalanceCard() {
        const balanceElement = document.getElementById('totalBalance');
        const incomeElement = document.getElementById('totalIncome');
        const expenseElement = document.getElementById('totalExpense');

        if (balanceElement) {
            balanceElement.textContent = this.formatAmount(this.stats.balance);
        }

        if (incomeElement) {
            incomeElement.textContent = this.formatAmount(this.stats.totalIncome);
        }

        if (expenseElement) {
            expenseElement.textContent = this.formatAmount(this.stats.totalExpense);
        }
    }

    /**
     * Update quick stats
     */
    updateQuickStats() {
        const countElement = document.getElementById('transactionCount');
        const avgElement = document.getElementById('avgExpense');
        const topElement = document.getElementById('topCategory');

        if (countElement) {
            countElement.textContent = this.stats.count;
        }

        if (avgElement) {
            avgElement.textContent = this.formatAmount(this.stats.avgExpense);
        }

        if (topElement) {
            topElement.textContent = this.stats.topCategory;
        }
    }

    /**
     * Render recent transactions
     */
    renderRecentTransactions() {
        const container = document.getElementById('recentTransactions');
        if (!container) return;

        if (this.transactions.length === 0) {
            this.showEmptyState('recentTransactions', 'Нет транзакций за выбранный период');
            return;
        }

        const html = this.transactions.slice(0, 10).map(transaction => 
            this.renderTransactionItem(transaction)
        ).join('');

        container.innerHTML = html;
    }

    /**
     * Render all transactions
     */
    renderAllTransactions() {
        const container = document.getElementById('allTransactions');
        if (!container) return;

        if (this.transactions.length === 0) {
            this.showEmptyState('allTransactions', 'Нет транзакций за выбранный период');
            return;
        }

        const html = this.transactions.map(transaction => 
            this.renderTransactionItem(transaction)
        ).join('');

        container.innerHTML = html;
    }

    /**
     * Render single transaction item
     */
    renderTransactionItem(transaction) {
        const amount = parseFloat(transaction.amount);
        const amountClass = transaction.type === 'income' ? 'income' : 'expense';
        const amountSign = transaction.type === 'income' ? '+' : '−';
        const icon = transaction.category_icon || '❓';
        const categoryName = transaction.category_name || 'Без категории';
        const description = transaction.description || categoryName;
        const date = this.formatDate(transaction.transaction_date || transaction.date);

        return `
            <div class="transaction-item" onclick="app.editTransaction(${transaction.id})">
                <div class="transaction-left">
                    <div class="transaction-icon ${amountClass}">${icon}</div>
                    <div class="transaction-info">
                        <h4>${categoryName}</h4>
                        <p>${description}</p>
                    </div>
                </div>
                <div class="transaction-amount">
                    <div class="amount ${amountClass}">${amountSign}${this.formatAmount(amount)}</div>
                    <div class="date">${date}</div>
                </div>
            </div>
        `;
    }

    /**
     * Render top categories
     */
    renderTopCategories(categoryStats) {
        const container = document.getElementById('topCategories');
        if (!container) return;

        if (!categoryStats || categoryStats.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>Нет данных за выбранный период</p></div>';
            return;
        }

        // Get max amount for percentage calculation
        const maxAmount = Math.max(...categoryStats.map(c => c.total));

        const html = categoryStats.slice(0, 10).map(stat => {
            const percentage = (stat.total / maxAmount * 100).toFixed(0);
            
            return `
                <div class="category-stat-item">
                    <div class="category-stat-header">
                        <div class="category-stat-left">
                            <div class="category-stat-icon">${stat.category_icon}</div>
                            <div class="category-stat-info">
                                <h4>${stat.category_name}</h4>
                                <p>${stat.count} транзакций</p>
                            </div>
                        </div>
                        <div class="category-stat-amount">${this.formatAmount(stat.total)}</div>
                    </div>
                    <div class="category-stat-bar">
                        <div class="category-stat-bar-fill" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    // ==================== CHARTS ====================

    /**
     * Setup all charts
     */
    setupCharts() {
        this.setupExpenseChart();
        this.setupCategoryChart();
        this.setupTrendChart();
    }

    /**
     * Setup expense chart
     */
    setupExpenseChart() {
        const canvas = document.getElementById('expenseChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        this.charts.expense = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#4facfe',
                        '#43e97b', '#fa709a', '#fee140', '#30cfd0'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: '#94a3b8',
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = this.formatAmount(context.parsed);
                                return `${label}: ${value}`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Setup category chart
     */
    setupCategoryChart() {
        const canvas = document.getElementById('categoryChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        this.charts.category = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Расходы',
                    data: [],
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return this.formatAmount(context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#94a3b8',
                            callback: (value) => this.formatAmount(value)
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    /**
     * Setup trend chart
     */
    setupTrendChart() {
        const canvas = document.getElementById('trendChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Расходы',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return this.formatAmount(context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#94a3b8',
                            callback: (value) => this.formatAmount(value)
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    /**
     * Update expense chart
     */
    updateExpenseChart() {
        if (!this.charts.expense) {
            console.warn('Expense chart not initialized yet');
            return;
        }

        // Group by category
        const categoryData = {};
        
        this.transactions
            .filter(t => t.type === 'expense')
            .forEach(transaction => {
                const category = transaction.category_name || 'Прочее';
                const amount = parseFloat(transaction.amount);
                categoryData[category] = (categoryData[category] || 0) + amount;
            });

        // Get top 8 categories
        const sorted = Object.entries(categoryData)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8);

        this.charts.expense.data.labels = sorted.map(item => item[0]);
        this.charts.expense.data.datasets[0].data = sorted.map(item => item[1]);
        this.charts.expense.update();

        console.log('Expense chart updated with', sorted.length, 'categories');
    }

    /**
     * Update category chart
     */
    updateCategoryChart(categoryStats) {
        if (!this.charts.category || !categoryStats) return;

        const top10 = categoryStats.slice(0, 10);

        this.charts.category.data.labels = top10.map(stat => stat.category_name);
        this.charts.category.data.datasets[0].data = top10.map(stat => stat.total);
        this.charts.category.update();
    }

    /**
     * Update trend chart
     */
    updateTrendChart(dailyTotals) {
        if (!this.charts.trend || !dailyTotals) return;

        this.charts.trend.data.labels = dailyTotals.map(item => {
            const date = new Date(item.date);
            return `${date.getDate()}.${date.getMonth() + 1}`;
        });
        this.charts.trend.data.datasets[0].data = dailyTotals.map(item => item.total);
        this.charts.trend.update();
    }

    // ==================== MODAL ====================

    /**
     * Open add transaction modal
     */
    openAddModal() {
        if (window.telegramApp) {
            window.telegramApp.hapticImpact('medium');
        }

        this.currentTransaction = null;
        
        // Reset form
        document.getElementById('transactionForm').reset();
        document.getElementById('transactionId').value = '';
        document.getElementById('modalTitle').textContent = 'Новая транзакция';
        document.getElementById('deleteBtn').style.display = 'none';

        // Set default values
        document.getElementById('transactionType').value = 'expense';
        document.getElementById('transactionDate').value = new Date().toISOString().split('T')[0];
        
        // Select expense type
        this.selectType('expense');

        // Show modal
        this.showModal();
    }

    /**
     * Edit transaction
     */
    async editTransaction(transactionId) {
        try {
            if (window.telegramApp) {
                window.telegramApp.hapticImpact('light');
            }

            // Find transaction
            const transaction = this.transactions.find(t => t.id === transactionId);
            if (!transaction) {
                console.error('Transaction not found:', transactionId);
                return;
            }

            this.currentTransaction = transaction;

            // Fill form
            document.getElementById('transactionId').value = transaction.id;
            document.getElementById('amount').value = transaction.amount;
            document.getElementById('categoryId').value = transaction.category_id;
            document.getElementById('description').value = transaction.description || '';
            document.getElementById('transactionDate').value = transaction.transaction_date || transaction.date;
            document.getElementById('transactionType').value = transaction.type;

            // Update modal title
            document.getElementById('modalTitle').textContent = 'Редактировать транзакцию';
            document.getElementById('deleteBtn').style.display = 'block';

            // Select type
            this.selectType(transaction.type);

            // Select category
            setTimeout(() => {
                this.selectCategory(transaction.category_id);
            }, 100);

            // Show modal
            this.showModal();

        } catch (error) {
            console.error('Edit transaction error:', error);
            this.showError('Ошибка при загрузке транзакции');
        }
    }

    /**
     * Show modal
     */
    showModal() {
        const modal = document.getElementById('transactionModal');
        if (modal) {
            modal.classList.add('active');
            document.body.classList.add('modal-open');
        }
    }

    /**
     * Close modal
     */
    closeModal() {
        if (window.telegramApp) {
            window.telegramApp.hapticImpact('light');
        }

        const modal = document.getElementById('transactionModal');
        if (modal) {
            modal.classList.add('closing');
            
            setTimeout(() => {
                modal.classList.remove('active', 'closing');
                document.body.classList.remove('modal-open');
            }, 300);
        }

        this.currentTransaction = null;
    }

    /**
     * Select transaction type
     */
    selectType(type) {
        if (window.telegramApp) {
            window.telegramApp.hapticSelection();
        }

        // Update buttons
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        const selectedBtn = document.querySelector(`.type-btn.${type}`);
        if (selectedBtn) {
            selectedBtn.classList.add('active');
        }

        // Update hidden input
        document.getElementById('transactionType').value = type;

        // Render categories for selected type
        this.renderCategoryGrid(type);
    }

    /**
     * Render category grid
     */
    renderCategoryGrid(type) {
        const grid = document.getElementById('categoryGrid');
        if (!grid) return;

        const categories = this.categories.filter(cat => cat.type === type);

        const html = categories.map(category => `
            <div class="category-item" onclick="app.selectCategory(${category.id})">
                <div class="icon">${category.icon}</div>
                <div class="name">${category.name}</div>
            </div>
        `).join('');

        grid.innerHTML = html;
    }

    /**
     * Select category
     */
    selectCategory(categoryId) {
        if (window.telegramApp) {
            window.telegramApp.hapticSelection();
        }

        // Update selected state
        document.querySelectorAll('.category-item').forEach(item => {
            item.classList.remove('selected');
        });

        const selectedItem = document.querySelector(`.category-item[onclick*="${categoryId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }

        // Update hidden input
        document.getElementById('categoryId').value = categoryId;
    }

    /**
     * Save transaction
     */
    async saveTransaction(event) {
        event.preventDefault();

        try {
            if (window.telegramApp) {
                window.telegramApp.hapticImpact('medium');
            }

            // Get form data
            const formData = {
                type: document.getElementById('transactionType').value,
                amount: parseFloat(document.getElementById('amount').value),
                category_id: parseInt(document.getElementById('categoryId').value),
                description: document.getElementById('description').value.trim(),
                date: document.getElementById('transactionDate').value
            };

            // Validate
            const validation = window.api.validateTransaction(formData);
            if (!validation.valid) {
                this.showError(validation.errors.join('\n'));
                return;
            }

            const transactionId = document.getElementById('transactionId').value;

            // Create or update
            if (transactionId) {
                await window.api.updateTransaction(transactionId, formData);
                this.showSuccess('Транзакция обновлена');
            } else {
                await window.api.createTransaction(formData);
                this.showSuccess('Транзакция создана');
            }

            // Close modal
            this.closeModal();

            // Refresh data
            await this.refreshCurrentSection();

            if (window.telegramApp) {
                window.telegramApp.hapticNotification('success');
            }

        } catch (error) {
            console.error('Save transaction error:', error);
            this.showError(error.message || 'Ошибка при сохранении транзакции');
            
            if (window.telegramApp) {
                window.telegramApp.hapticNotification('error');
            }
        }
    }

    /**
     * Delete transaction
     */
    async deleteTransaction() {
        try {
            const transactionId = document.getElementById('transactionId').value;
            if (!transactionId) return;

            // Confirm
            const confirmed = await this.showConfirm('Удалить транзакцию?');
            if (!confirmed) return;

            if (window.telegramApp) {
                window.telegramApp.hapticImpact('heavy');
            }

            // Delete
            await window.api.deleteTransaction(transactionId);

            this.showSuccess('Транзакция удалена');

            // Close modal
            this.closeModal();

            // Refresh data
            await this.refreshCurrentSection();

            if (window.telegramApp) {
                window.telegramApp.hapticNotification('success');
            }

        } catch (error) {
            console.error('Delete transaction error:', error);
            this.showError('Ошибка при удалении транзакции');
            
            if (window.telegramApp) {
                window.telegramApp.hapticNotification('error');
            }
        }
    }

    /**
     * Delete transaction by ID (called from swipe)
     */
    async deleteTransactionById(transactionId) {
        try {
            if (window.telegramApp) {
                window.telegramApp.hapticImpact('heavy');
            }

            // Delete
            await window.api.deleteTransaction(transactionId);

            this.showSuccess('Транзакция удалена');

            // Refresh data
            await this.refreshCurrentSection();

            if (window.telegramApp) {
                window.telegramApp.hapticNotification('success');
            }

        } catch (error) {
            console.error('Delete transaction error:', error);
            this.showError('Ошибка при удалении транзакции');
            
            if (window.telegramApp) {
                window.telegramApp.hapticNotification('error');
            }
        }
    }

    // ==================== HELPERS ====================

    /**
     * Show loading
     */
    showLoading(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="loading active">
                <div class="spinner"></div>
                <p style="margin-top: 15px;">Загрузка...</p>
            </div>
        `;
    }

    /**
     * Hide loading
     */
    hideLoading(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const loading = container.querySelector('.loading');
        if (loading) {
            loading.remove();
        }
    }

    /**
     * Show empty state
     */
    showEmptyState(containerId, message) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <h3>Пусто</h3>
                <p>${message}</p>
            </div>
        `;
    }

    /**
     * Show error
     */
    showError(message) {
        if (window.telegramApp) {
            window.telegramApp.showAlert(message);
        } else {
            alert(message);
        }
    }

    /**
     * Show success
     */
    showSuccess(message) {
        if (window.telegramApp) {
            window.telegramApp.showAlert(message);
        } else {
            alert(message);
        }
    }

    /**
     * Show confirmation
     */
    async showConfirm(message) {
        return new Promise((resolve) => {
            if (window.telegramApp) {
                window.telegramApp.showConfirm(message, resolve);
            } else {
                resolve(confirm(message));
            }
        });
    }

    /**
     * Format amount
     */
    formatAmount(amount) {
        if (!amount && amount !== 0) return '0 ₽';
        
        return new Intl.NumberFormat('ru-RU', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount) + ' ₽';
    }

    /**
     * Format date
     */
    formatDate(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        // Check if today
        if (date.toDateString() === today.toDateString()) {
            return 'Сегодня';
        }

        // Check if yesterday
        if (date.toDateString() === yesterday.toDateString()) {
            return 'Вчера';
        }

        // Format as DD.MM.YYYY
        return date.toLocaleDateString('ru-RU');
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.app = new FinanceApp();
    });
} else {
    window.app = new FinanceApp();
}

// Global functions for onclick handlers
function switchSection(section) {
    window.app.switchSection(section);
}

function openAddModal() {
    window.app.openAddModal();
}

function closeModal() {
    window.app.closeModal();
}

function selectType(type) {
    window.app.selectType(type);
}

function selectCategory(id) {
    window.app.selectCategory(id);
}

function saveTransaction(event) {
    window.app.saveTransaction(event);
}

function deleteTransaction() {
    window.app.deleteTransaction();
}

console.log('App.js loaded');
