CREATE TABLE IF NOT EXISTS procedures (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  procedure_name VARCHAR(180) NOT NULL,
  category VARCHAR(80) NOT NULL,
  short_description TEXT NOT NULL,
  full_description TEXT NULL,
  benefits TEXT NULL,
  preparation_guidelines TEXT NULL,
  aftercare_instructions TEXT NULL,
  session_duration VARCHAR(80) NULL,
  recommended_sessions VARCHAR(80) NULL,
  status ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
  procedure_image VARCHAR(255) NULL,
  sort_order INT UNSIGNED NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_procedures_status (status),
  INDEX idx_procedures_category (category),
  INDEX idx_procedures_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE procedures
  ADD COLUMN IF NOT EXISTS sort_order INT UNSIGNED NOT NULL DEFAULT 0 AFTER procedure_image;

UPDATE procedures SET sort_order = id WHERE sort_order = 0;

CREATE TABLE IF NOT EXISTS consultation_image_records (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  procedure_id VARCHAR(120) NULL,
  procedure_name VARCHAR(180) NOT NULL,
  original_image_path VARCHAR(255) NULL,
  processed_image_path VARCHAR(255) NULL,
  processing_status ENUM('Completed','Failed','Pending','Deleted') NOT NULL DEFAULT 'Completed',
  handled_by VARCHAR(120) NULL,
  notes TEXT NULL,
  date_processed TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_records_procedure (procedure_name),
  INDEX idx_records_status (processing_status),
  INDEX idx_records_date (date_processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
