-- Employee number is the user-facing unique employee identifier.
-- The app keeps users.id as the internal primary key because sessions,
-- audit logs, appointments, and processed image records reference it.

ALTER TABLE users_data
  MODIFY employee_number VARCHAR(255) NOT NULL;

SET @employee_number_unique_exists := (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'users_data'
    AND non_unique = 0
    AND column_name = 'employee_number'
);

SET @employee_number_unique_sql := IF(
  @employee_number_unique_exists = 0,
  'ALTER TABLE users_data ADD UNIQUE KEY uniq_users_employee_number (employee_number)',
  'SELECT ''employee_number already has a unique key'' AS message'
);

PREPARE employee_number_unique_stmt FROM @employee_number_unique_sql;
EXECUTE employee_number_unique_stmt;
DEALLOCATE PREPARE employee_number_unique_stmt;
