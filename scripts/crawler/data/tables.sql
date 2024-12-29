CREATE TABLE IF NOT EXISTS calls_basic_information (
    call_code varchar(150) NOT NULL,
    call_title varchar(300) NOT NULL,
    call_href varchar(250) NOT NULL,
    funding_mechanism varchar(250) DEFAULT NULL,
    opening_date date DEFAULT NULL,
    next_deadline_date date DEFAULT NULL,
    submission_type varchar(250) DEFAULT NULL,
    call_state varchar(100) DEFAULT NULL,
    programme varchar(250) DEFAULT NULL,
    type_of_action varchar(250) DEFAULT NULL,
    budget_total float DEFAULT NULL,
    eligibility_region varchar(100) NOT NULL,
    type_company VARCHAR(100) DEFAULT NULL,
    extra_information longtext NOT NULL,
    PRIMARY KEY (call_code, call_title) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Calls basic information';

CREATE TABLE IF NOT EXISTS calls_description_information (
    call_code varchar(150) NOT NULL,
    call_title varchar(300) NOT NULL,
    topic_description text NOT NULL,
    topic_destination text NOT NULL,
    topic_conditions_and_documents text NOT NULL,
    budget_overview text NOT NULL,
    partner_search_announcements text NOT NULL,
    start_submission text NOT NULL,
    get_support text NOT NULL,
    extra_information text NOT NULL,
    PRIMARY KEY (call_code, call_title) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Calls description information';

CREATE TABLE IF NOT EXISTS calls_budget_information (
    call_code varchar(150) NOT NULL,
    call_title varchar(300) NOT NULL,
    budget_topic varchar(250) NOT NULL,
    budget_amount varchar(250) NOT NULL,
    budget_stages varchar(250) NOT NULL,
    budget_opening_date varchar(250) NOT NULL,
    budget_deadline varchar(250) NOT NULL,
    budget_contributions varchar(250) NOT NULL,
    budget_indicative_number_of_grants varchar(250) NOT NULL,
    PRIMARY KEY (call_code, call_title, budget_topic) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Calls budget information';

CREATE TABLE IF NOT EXISTS calls_files_information (
    id BIGINT NOT NULL AUTO_INCREMENT,
    file_url VARCHAR(250) NOT NULL,
    file_text mediumtext NOT NULL,
    file_summary text NOT NULL,
    file_similarity float DEFAULT NULL,
    file_error_description VARCHAR(250),
    file_error_code VARCHAR(100),
    PRIMARY KEY (id) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Calls files information';

CREATE TABLE IF NOT EXISTS calls_urls (
    call_code varchar(150) NOT NULL,
    call_title varchar(300) NOT NULL,
    file_id BIGINT NOT NULL,
    file_title varchar(150) NOT NULL,
    PRIMARY KEY (call_code, call_title, file_id, file_title) USING BTREE,
    CONSTRAINT fk_file_id FOREIGN KEY (file_id) REFERENCES calls_files_information(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Calls urls relationship';

CREATE TABLE IF NOT EXISTS calls_logs (
    id BIGINT NOT NULL AUTO_INCREMENT,
    root_id INT DEFAULT NULL,
    crawler_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('STARTED', 'WEB CRAWL', 'WEB CRAWL EXTENDED', 'CLOSING CALLS', 'NLP SUMMARY', 'NLP TYPE COMPANY', 'DB VECTORIAL', 'FINISHED', 'ERROR') NOT NULL,
    message TEXT,
    PRIMARY KEY (id) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Calls logs';
