<?php

require_once '../auth_common.php';
include '../config.php';

header('Content-Type: application/json; charset=utf-8');

auth_require_admin(true);

function table_exists($conn, $table_name) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = ?
    ");
    $stmt->bind_param("s", $table_name);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result ? $result->fetch_assoc() : null;

    return $row && (int) $row['total'] > 0;
}

function ensure_consultation_records_table($conn) {
    $conn->query("
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");
}

function ensure_table_column($conn, $table_name, $column_name, $alter_sql) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS total
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = ?
          AND column_name = ?
    ");

    if (!$stmt) {
        return;
    }

    $stmt->bind_param("ss", $table_name, $column_name);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result ? $result->fetch_assoc() : null;

    if (!$row || (int) $row['total'] === 0) {
        $conn->query($alter_sql);
    }
}

function staff_display_name_from_row($row) {
    $role = strtolower(str_replace([' ', '-'], '_', trim((string) ($row['staff_role'] ?? ''))));
    $is_staff = $role === 'staff';

    if (!$is_staff) {
        return 'Not recorded';
    }

    $name = trim((string) (($row['staff_first_name'] ?? '') . ' ' . ($row['staff_last_name'] ?? '')));

    if ($name !== '') {
        return $name;
    }

    $fallback = trim((string) ($row['staff_email'] ?? $row['staff_employee_number'] ?? ''));

    if ($fallback !== '') {
        return $fallback;
    }

    $handled_by = trim((string) ($row['handled_by'] ?? ''));

    if ($handled_by !== '' && strcasecmp($handled_by, 'System') !== 0) {
        return $handled_by;
    }

    return 'Not recorded';
}

ensure_consultation_records_table($conn);
ensure_table_column($conn, 'consultation_image_records', 'archived_at', "ALTER TABLE consultation_image_records ADD COLUMN archived_at TIMESTAMP NULL AFTER date_processed");

$action = $_POST['action'] ?? 'fetch';

if ($action === 'delete') {
    $id = (int) ($_POST['id'] ?? 0);
    $source = $_POST['source'] ?? 'records';

    if ($source === 'processed_images' && table_exists($conn, 'processed_images')) {
        $stmt = $conn->prepare("DELETE FROM processed_images WHERE id = ?");
    } else {
        $stmt = $conn->prepare("UPDATE consultation_image_records SET processing_status = 'Deleted' WHERE id = ?");
    }

    $stmt->bind_param("i", $id);
    $stmt->execute();
    echo json_encode(['status' => 'ok', 'message' => 'Record updated.']);
    exit();
}

if ($action === 'clear_old') {
    $conn->query("UPDATE consultation_image_records SET processing_status = 'Deleted' WHERE date_processed < DATE_SUB(NOW(), INTERVAL 90 DAY)");

    if (table_exists($conn, 'processed_images')) {
        $conn->query("DELETE FROM processed_images WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)");
    }

    echo json_encode(['status' => 'ok', 'message' => 'Old records cleared.']);
    exit();
}

$records = [];

$result = $conn->query("
    SELECT id, procedure_id, procedure_name, original_image_path, processed_image_path,
           processing_status, handled_by, notes, date_processed
    FROM consultation_image_records
    WHERE archived_at IS NULL
    ORDER BY date_processed DESC, id DESC
");

if ($result) {
    while ($row = $result->fetch_assoc()) {
        $row['source'] = 'records';
        $records[] = $row;
    }
}

if (table_exists($conn, 'processed_images')) {
    ensure_table_column($conn, 'processed_images', 'handled_by', "ALTER TABLE processed_images ADD COLUMN handled_by VARCHAR(160) NULL AFTER recommendations_json");
    ensure_table_column($conn, 'processed_images', 'handled_by_user_id', "ALTER TABLE processed_images ADD COLUMN handled_by_user_id INT NULL AFTER handled_by");
    ensure_table_column($conn, 'processed_images', 'archived_at', "ALTER TABLE processed_images ADD COLUMN archived_at TIMESTAMP NULL AFTER created_at");

    $result = $conn->query("
        SELECT pi.id, pi.procedure_id, pi.procedure_name, pi.before_image_path, pi.after_image_path,
               pi.analysis_type, pi.handled_by, pi.handled_by_user_id, pi.created_at,
               u.first_name AS staff_first_name, u.last_name AS staff_last_name,
               u.email AS staff_email, u.employee_number AS staff_employee_number,
               u.role AS staff_role
        FROM processed_images pi
        LEFT JOIN users u ON u.id = pi.handled_by_user_id
        WHERE pi.archived_at IS NULL
        ORDER BY pi.created_at DESC, pi.id DESC
        LIMIT 200
    ");

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $records[] = [
                'id' => (int) $row['id'],
                'procedure_id' => $row['procedure_id'],
                'procedure_name' => $row['procedure_name'],
                'original_image_path' => $row['before_image_path'],
                'processed_image_path' => $row['after_image_path'],
                'processing_status' => 'Completed',
                'handled_by' => staff_display_name_from_row($row),
                'notes' => $row['analysis_type'],
                'date_processed' => $row['created_at'],
                'source' => 'processed_images'
            ];
        }
    }
}

usort($records, function ($a, $b) {
    return strtotime($b['date_processed']) <=> strtotime($a['date_processed']);
});

echo json_encode([
    'status' => 'ok',
    'records' => array_slice($records, 0, 250)
]);

?>
