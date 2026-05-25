<?php
// Super Admin module: full-system control copy.
require_once '../auth_common.php';
include '../config.php';

header('Content-Type: application/json; charset=utf-8');

auth_require_super_admin(true);

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

ensure_consultation_records_table($conn);

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
    ORDER BY date_processed DESC, id DESC
");

if ($result) {
    while ($row = $result->fetch_assoc()) {
        $row['source'] = 'records';
        $records[] = $row;
    }
}

if (table_exists($conn, 'processed_images')) {
    $result = $conn->query("
        SELECT id, procedure_id, procedure_name, before_image_path, after_image_path,
               analysis_type, created_at
        FROM processed_images
        ORDER BY created_at DESC, id DESC
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
                'handled_by' => 'System',
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
