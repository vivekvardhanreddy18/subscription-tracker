CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category_id INT NULL,
    cost DECIMAL(10,2) NOT NULL,
    billing_cycle ENUM('weekly','monthly','quarterly','yearly') NOT NULL DEFAULT 'monthly',
    start_date DATE NOT NULL,
    status ENUM('active','paused','cancelled') NOT NULL DEFAULT 'active',
    notes VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    CONSTRAINT fk_sub_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS usage_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subscription_id INT NOT NULL,
    used_on DATE NOT NULL,
    INDEX idx_sub_date (subscription_id, used_on),
    CONSTRAINT fk_usage_sub FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE
);

INSERT IGNORE INTO categories (name) VALUES
('Entertainment'), ('Music'), ('Productivity'), ('Fitness'), ('Education'), ('Cloud Storage'), ('News'), ('Other');
