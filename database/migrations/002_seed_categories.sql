-- Migration 002: Seed categories
-- Date: 2025-01-01

-- Insert expense categories (15 categories)
INSERT INTO categories (name, icon, type) VALUES
('Продукты', '🍔', 'expense'),
('Рестораны и кафе', '🍕', 'expense'),
('Транспорт', '🚗', 'expense'),
('Топливо', '⛽', 'expense'),
('Жилье', '🏠', 'expense'),
('Покупки', '🛒', 'expense'),
('Здоровье и аптека', '💊', 'expense'),
('Образование', '🎓', 'expense'),
('Развлечения', '🎮', 'expense'),
('Связь и интернет', '📱', 'expense'),
('Спорт и фитнес', '🏋️', 'expense'),
('Путешествия', '✈️', 'expense'),
('Подарки', '🎁', 'expense'),
('Красота и уход', '💇', 'expense'),
('Прочее', '❓', 'expense')
ON CONFLICT (name) DO NOTHING;

-- Insert income categories (5 categories)
INSERT INTO categories (name, icon, type) VALUES
('Зарплата', '💰', 'income'),
('Фриланс/Подработка', '💼', 'income'),
('Подарки/Возвраты', '🎁', 'income'),
('Инвестиции', '📈', 'income'),
('Другие доходы', '❓', 'income')
ON CONFLICT (name) DO NOTHING;
