/**
 * Telegram Web App Integration
 * Handles all Telegram Mini App functionality
 */

class TelegramWebApp {
    constructor() {
        this.tg = null;
        this.user = null;
        this.initData = null;
        this.isReady = false;
        this.init();
    }

    /**
     * Initialize Telegram Web App
     */
    init() {
        try {
            console.log('🔍 ========== TELEGRAM WEBAPP INIT START ==========');
            console.log('🔍 window.Telegram exists:', !!window.Telegram);
            console.log('🔍 window.Telegram.WebApp exists:', !!window.Telegram?.WebApp);

            // Check if Telegram SDK is loaded
            if (!window.Telegram || !window.Telegram.WebApp) {
                console.error('❌ Telegram WebApp SDK not loaded!');
                console.log('🔍 Hostname:', window.location.hostname);
                console.log('🔍 Full URL:', window.location.href);
                
                // Fallback to development mode
                if (this.isDevelopment()) {
                    console.warn('⚠️ Development mode detected - using mock data');
                    this.initDevelopmentMode();
                } else {
                    console.error('❌ Not in Telegram and not in development mode');
                    console.error('❌ WebApp will not function properly');
                    // Still try to initialize with empty data
                    this.initDevelopmentMode();
                }
                return;
            }

            this.tg = window.Telegram.WebApp;

            console.log('🔍 Telegram SDK loaded successfully');
            console.log('🔍 SDK Version:', this.tg.version);
            console.log('🔍 Platform:', this.tg.platform);
            console.log('🔍 Color Scheme:', this.tg.colorScheme);

            // Expand to full height
            this.tg.expand();
            console.log('✅ WebApp expanded');

            // Enable closing confirmation
            this.tg.enableClosingConfirmation();
            console.log('✅ Closing confirmation enabled');

            // Get user data
            console.log('🔍 Checking initDataUnsafe...');
            console.log('🔍 initDataUnsafe object:', this.tg.initDataUnsafe);
            
            this.user = this.tg.initDataUnsafe?.user || null;
            this.initData = this.tg.initData || '';

            console.log('🔍 initData string length:', this.initData?.length || 0);
            console.log('🔍 initData (first 100 chars):', this.initData?.substring(0, 100) || 'empty');
            console.log('🔍 User object:', this.user);
            console.log('🔍 User ID:', this.user?.id);
            console.log('🔍 User first_name:', this.user?.first_name);
            console.log('🔍 User username:', this.user?.username);

            // Check if we have user data
            if (!this.user || !this.user.id) {
                console.error('❌ No user data available!');
                console.error('❌ This usually means:');
                console.error('   1. WebApp opened directly in browser (not through Telegram bot)');
                console.error('   2. WebApp URL not properly configured in bot');
                console.error('   3. Bot button uses wrong URL');
                
                // Fallback for development
                if (this.isDevelopment()) {
                    console.warn('⚠️ Using mock user data for development');
                    this.initDevelopmentMode();
                } else {
                    console.error('❌ Cannot proceed without user data in production');
                    // Still initialize with mock data to prevent crashes
                    this.initDevelopmentMode();
                    this.showAlert('Ошибка: откройте приложение через бота Telegram');
                }
                return;
            }

            console.log('✅ User data loaded successfully');
            console.log('✅ User ID:', this.user.id);

            // Apply theme
            this.applyTheme();
            console.log('✅ Theme applied');

            // Setup main button
            this.setupMainButton();
            console.log('✅ Main button configured');

            // Setup back button
            this.setupBackButton();
            console.log('✅ Back button configured');

            // Mark as ready
            this.isReady = true;
            this.tg.ready();
            console.log('✅ Telegram WebApp ready');

            console.log('🔍 ========== TELEGRAM WEBAPP INIT COMPLETE ==========');

        } catch (error) {
            console.error('❌ Telegram Web App init error:', error);
            console.error('❌ Stack trace:', error.stack);
            
            // Fallback for development
            if (this.isDevelopment()) {
                console.warn('⚠️ Error occurred - falling back to development mode');
                this.initDevelopmentMode();
            } else {
                // Initialize with mock data to prevent app crash
                console.error('❌ Error in production - initializing with mock data');
                this.initDevelopmentMode();
            }
        }
    }

    /**
     * Apply Telegram theme colors
     */
    applyTheme() {
        try {
            if (!this.tg) return;

            const root = document.documentElement;
            const themeParams = this.tg.themeParams;

            // Apply theme if available
            if (themeParams.bg_color) {
                root.style.setProperty('--tg-bg-color', themeParams.bg_color);
            }
            if (themeParams.text_color) {
                root.style.setProperty('--tg-text-color', themeParams.text_color);
            }
            if (themeParams.hint_color) {
                root.style.setProperty('--tg-hint-color', themeParams.hint_color);
            }
            if (themeParams.button_color) {
                root.style.setProperty('--tg-button-color', themeParams.button_color);
            }

            // Set color scheme
            const colorScheme = this.tg.colorScheme || 'dark';
            root.setAttribute('data-theme', colorScheme);

            console.log('✅ Theme applied:', colorScheme);

        } catch (error) {
            console.error('Theme apply error:', error);
        }
    }

    /**
     * Setup main button
     */
    setupMainButton() {
        try {
            if (!this.tg?.MainButton) return;

            // Hide by default
            this.tg.MainButton.hide();

            // Setup click handler
            this.tg.MainButton.onClick(() => {
                this.onMainButtonClick();
            });

        } catch (error) {
            console.error('Main button setup error:', error);
        }
    }

    /**
     * Setup back button
     */
    setupBackButton() {
        try {
            if (!this.tg?.BackButton) return;

            // Hide by default
            this.tg.BackButton.hide();

            // Setup click handler
            this.tg.BackButton.onClick(() => {
                this.onBackButtonClick();
            });

        } catch (error) {
            console.error('Back button setup error:', error);
        }
    }

    /**
     * Show main button
     */
    showMainButton(text, callback) {
        try {
            if (!this.tg?.MainButton) return;

            this.tg.MainButton.setText(text);
            this.tg.MainButton.show();
            
            if (callback) {
                this.mainButtonCallback = callback;
            }
        } catch (error) {
            console.error('Show main button error:', error);
        }
    }

    /**
     * Hide main button
     */
    hideMainButton() {
        try {
            if (!this.tg?.MainButton) return;

            this.tg.MainButton.hide();
            this.mainButtonCallback = null;
        } catch (error) {
            console.error('Hide main button error:', error);
        }
    }

    /**
     * Show back button
     */
    showBackButton(callback) {
        try {
            if (!this.tg?.BackButton) return;

            this.tg.BackButton.show();
            
            if (callback) {
                this.backButtonCallback = callback;
            }
        } catch (error) {
            console.error('Show back button error:', error);
        }
    }

    /**
     * Hide back button
     */
    hideBackButton() {
        try {
            if (!this.tg?.BackButton) return;

            this.tg.BackButton.hide();
            this.backButtonCallback = null;
        } catch (error) {
            console.error('Hide back button error:', error);
        }
    }

    /**
     * Main button click handler
     */
    onMainButtonClick() {
        if (this.mainButtonCallback) {
            this.mainButtonCallback();
        }
    }

    /**
     * Back button click handler
     */
    onBackButtonClick() {
        if (this.backButtonCallback) {
            this.backButtonCallback();
        } else {
            // Default: close modal or go back
            window.history.back();
        }
    }

    /**
     * Show popup alert
     */
    showAlert(message, callback) {
        try {
            if (this.tg?.showAlert) {
                this.tg.showAlert(message, callback);
            } else {
                alert(message);
                if (callback) callback();
            }
        } catch (error) {
            console.error('Show alert error:', error);
            alert(message);
            if (callback) callback();
        }
    }

    /**
     * Show confirmation popup
     */
    showConfirm(message, callback) {
        try {
            if (this.tg?.showConfirm) {
                this.tg.showConfirm(message, callback);
            } else {
                const result = confirm(message);
                if (callback) callback(result);
            }
        } catch (error) {
            console.error('Show confirm error:', error);
            const result = confirm(message);
            if (callback) callback(result);
        }
    }

    /**
     * Show popup with buttons
     */
    showPopup(params, callback) {
        try {
            if (this.tg?.showPopup) {
                this.tg.showPopup(params, callback);
            } else {
                this.showAlert(params.message, callback);
            }
        } catch (error) {
            console.error('Show popup error:', error);
            this.showAlert(params.message, callback);
        }
    }

    /**
     * Haptic feedback - impact
     */
    hapticImpact(style = 'medium') {
        try {
            if (this.tg?.HapticFeedback?.impactOccurred) {
                this.tg.HapticFeedback.impactOccurred(style);
            }
        } catch (error) {
            // Silently fail
        }
    }

    /**
     * Haptic feedback - notification
     */
    hapticNotification(type = 'success') {
        try {
            if (this.tg?.HapticFeedback?.notificationOccurred) {
                this.tg.HapticFeedback.notificationOccurred(type);
            }
        } catch (error) {
            // Silently fail
        }
    }

    /**
     * Haptic feedback - selection changed
     */
    hapticSelection() {
        try {
            if (this.tg?.HapticFeedback?.selectionChanged) {
                this.tg.HapticFeedback.selectionChanged();
            }
        } catch (error) {
            // Silently fail
        }
    }

    /**
     * Open external link
     */
    openLink(url, options = {}) {
        try {
            if (this.tg?.openLink) {
                this.tg.openLink(url, options);
            } else {
                window.open(url, '_blank');
            }
        } catch (error) {
            console.error('Open link error:', error);
            window.open(url, '_blank');
        }
    }

    /**
     * Open Telegram link
     */
    openTelegramLink(url) {
        try {
            if (this.tg?.openTelegramLink) {
                this.tg.openTelegramLink(url);
            } else {
                this.openLink(url);
            }
        } catch (error) {
            console.error('Open Telegram link error:', error);
            this.openLink(url);
        }
    }

    /**
     * Close Web App
     */
    close() {
        try {
            if (this.tg?.close) {
                this.tg.close();
            } else {
                window.close();
            }
        } catch (error) {
            console.error('Close error:', error);
            window.close();
        }
    }

    /**
     * Get user ID
     */
    getUserId() {
        const userId = this.user?.id || null;
        console.log('🔍 getUserId() called, returning:', userId);
        
        if (!userId) {
            console.warn('⚠️ getUserId() returning null - user not authenticated');
            console.warn('⚠️ This will cause API requests to fail with 401');
        }
        
        return userId;
    }

    /**
     * Get user data
     */
    getUser() {
        return this.user;
    }

    /**
     * Get init data for backend authentication
     */
    getInitData() {
        return this.initData;
    }

    /**
     * Check if running in Telegram
     */
    isInTelegram() {
        const inTelegram = !!(this.tg?.initData && this.tg.initData.length > 0);
        console.log('🔍 isInTelegram():', inTelegram);
        return inTelegram;
    }

    /**
     * Check if development mode
     */
    isDevelopment() {
        return window.location.hostname === 'localhost' || 
               window.location.hostname === '127.0.0.1';
    }

    /**
     * Initialize development mode with mock data
     */
    initDevelopmentMode() {
        console.warn('⚠️ ========== DEVELOPMENT MODE ==========');
        console.warn('⚠️ Running with MOCK data');
        console.warn('⚠️ This should NOT happen in production!');
        
        // Mock user data
        this.user = {
            id: 123456789,
            first_name: 'Test',
            last_name: 'User',
            username: 'testuser',
            language_code: 'ru',
            is_premium: false
        };

        // Mock init data
        this.initData = 'mock_init_data_for_development';

        // Mark as ready
        this.isReady = true;

        console.warn('⚠️ Mock user created:', this.user);
        console.warn('⚠️ Mock user ID:', this.user.id);
        console.warn('⚠️ ======================================');
    }

    /**
     * Send data to bot
     */
    sendData(data) {
        try {
            if (this.tg?.sendData) {
                const jsonData = typeof data === 'string' ? data : JSON.stringify(data);
                this.tg.sendData(jsonData);
            } else {
                console.warn('sendData not available');
            }
        } catch (error) {
            console.error('Send data error:', error);
        }
    }

    /**
     * Check if feature is available
     */
    isVersionAtLeast(version) {
        try {
            return this.tg?.isVersionAtLeast?.(version) || false;
        } catch (error) {
            return false;
        }
    }

    /**
     * Get platform
     */
    getPlatform() {
        try {
            return this.tg?.platform || 'unknown';
        } catch (error) {
            return 'unknown';
        }
    }

    /**
     * Get viewport height
     */
    getViewportHeight() {
        try {
            return this.tg?.viewportHeight || window.innerHeight;
        } catch (error) {
            return window.innerHeight;
        }
    }

    /**
     * Get viewport stable height
     */
    getViewportStableHeight() {
        try {
            return this.tg?.viewportStableHeight || window.innerHeight;
        } catch (error) {
            return window.innerHeight;
        }
    }

    /**
     * Request write access
     */
    requestWriteAccess(callback) {
        try {
            if (this.tg?.requestWriteAccess) {
                this.tg.requestWriteAccess(callback);
            } else {
                console.warn('requestWriteAccess not available');
                if (callback) callback(false);
            }
        } catch (error) {
            console.error('Request write access error:', error);
            if (callback) callback(false);
        }
    }

    /**
     * Request contact
     */
    requestContact(callback) {
        try {
            if (this.tg?.requestContact) {
                this.tg.requestContact(callback);
            } else {
                console.warn('requestContact not available');
                if (callback) callback(false);
            }
        } catch (error) {
            console.error('Request contact error:', error);
            if (callback) callback(false);
        }
    }

    /**
     * Check if ready
     */
    isAppReady() {
        return this.isReady && this.user && this.user.id;
    }
}

// Wait for DOM to be ready before initializing
function initTelegramApp() {
    console.log('🔍 Initializing Telegram Web App...');
    const telegramApp = new TelegramWebApp();
    
    // Export for use in other files
    window.telegramApp = telegramApp;
    
    // Expose to console for debugging
    window.tg = telegramApp;
    
    console.log('✅ Telegram integration loaded');
    console.log('🔍 App ready:', telegramApp.isAppReady());
    
    return telegramApp;
}

// Initialize immediately if DOM is ready, otherwise wait
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTelegramApp);
} else {
    initTelegramApp();
}
