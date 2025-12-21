-- 完整的thinking_together数据库表结构
-- 支持所有系统数据的持久化存储

-- 1. 线程表 (threads)
CREATE TABLE IF NOT EXISTS threads (
    thread_id VARCHAR(32) PRIMARY KEY,
    topic VARCHAR(500) NOT NULL,
    phase ENUM('opening', 'discussion', 'closing') DEFAULT 'opening',
    turn_id INT DEFAULT 0,
    last_speaker VARCHAR(50),
    last_user_interjection TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_topic (topic)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 事件表 (events) - 所有公开发言
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR(32) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    speaker VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    turn_id INT NOT NULL,
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    INDEX idx_thread_turn (thread_id, turn_id),
    INDEX idx_speaker (speaker),
    INDEX idx_created_at (created_at),
    FULLTEXT idx_content (content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 议程表 (agenda)
CREATE TABLE IF NOT EXISTS agenda (
    item_id VARCHAR(16) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    question TEXT NOT NULL,
    priority INT DEFAULT 50,
    status ENUM('open', 'active', 'completed', 'closed') DEFAULT 'open',
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    INDEX idx_thread_status (thread_id, status),
    INDEX idx_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 共识表 (consensus)
CREATE TABLE IF NOT EXISTS consensus (
    consensus_id VARCHAR(32) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    source_event_id VARCHAR(32),  -- 哪个事件产生的共识
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (source_event_id) REFERENCES events(event_id) ON DELETE SET NULL,
    INDEX idx_thread_id (thread_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 分歧表 (disagreements)
CREATE TABLE IF NOT EXISTS disagreements (
    disagreement_id VARCHAR(32) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    source_event_id VARCHAR(32),  -- 哪个事件产生的分歧
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (source_event_id) REFERENCES events(event_id) ON DELETE SET NULL,
    INDEX idx_thread_id (thread_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 开放问题表 (open_questions)
CREATE TABLE IF NOT EXISTS open_questions (
    question_id VARCHAR(32) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    source_event_id VARCHAR(32),  -- 哪个事件产生的问题
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (source_event_id) REFERENCES events(event_id) ON DELETE SET NULL,
    INDEX idx_thread_id (thread_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. 风格健康度表 (style_health)
CREATE TABLE IF NOT EXISTS style_health (
    health_id VARCHAR(32) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    flag_type ENUM('list_like', 'generic', 'repetitive') NOT NULL,
    count INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    UNIQUE KEY unique_thread_flag (thread_id, flag_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. 分析结果表 (analysis_results) - 存储智能分析的结果
CREATE TABLE IF NOT EXISTS analysis_results (
    analysis_id VARCHAR(32) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    event_id VARCHAR(32) NOT NULL,
    analysis_type ENUM('consensus', 'disagreement', 'question', 'key_point', 'emotion') NOT NULL,
    content TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    INDEX idx_thread_type (thread_id, analysis_type),
    INDEX idx_event_id (event_id),
    INDEX idx_confidence (confidence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. 对话统计表 (conversation_stats)
CREATE TABLE IF NOT EXISTS conversation_stats (
    stats_id VARCHAR(32) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    speaker VARCHAR(50) NOT NULL,
    message_count INT DEFAULT 0,
    total_chars INT DEFAULT 0,
    avg_message_length FLOAT DEFAULT 0,
    first_speak_at TIMESTAMP NULL,
    last_speak_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    UNIQUE KEY unique_thread_speaker (thread_id, speaker)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. 关键词索引表 (keywords)
CREATE TABLE IF NOT EXISTS keywords (
    keyword_id VARCHAR(32) PRIMARY KEY,
    thread_id VARCHAR(32) NOT NULL,
    event_id VARCHAR(32) NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    INDEX idx_thread_keyword (thread_id, keyword),
    INDEX idx_weight (weight)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;