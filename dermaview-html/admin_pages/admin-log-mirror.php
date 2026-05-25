<?php
// Mirror endpoint for admin activity logs loading.
require __DIR__ . '/../auth_common.php';
require __DIR__ . '/../audit_common.php';
include __DIR__ . '/../config.php';

session_start();
header('Content-Type: application/json; charset=utf-8');

audit_ensure_tables($conn);

if (!isset($_SESSION['user_id'])) {
    echo json_encode(['status' => 'error']);
    exit();
}

if (!auth_is_admin_role($_SESSION['role'] ?? '')) {
    http_response_code(403);
    echo json_encode(['status' => 'error', 'message' => 'Admin access required']);
    exit();
}

$limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
$logs = audit_get_recent_activity($conn, $limit);

function admin_log_table_exists($conn, $table_name) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS table_count
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = ?
    ");
    $stmt->bind_param("s", $table_name);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result ? $result->fetch_assoc() : null;

    return $row && (int) $row['table_count'] > 0;
}

if (admin_log_table_exists($conn, 'appointments')) {
    $appointment_limit = max(1, min($limit, 25));
    $stmt = $conn->prepare("
        SELECT id, patient_name, procedure_name, status, created_at
        FROM appointments
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    ");
    $stmt->bind_param("i", $appointment_limit);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $logs[] = [
                'type' => 'Appointment',
                'title' => trim($row['patient_name'] . ' scheduled ' . $row['procedure_name']),
                'status' => $row['status'] ?: 'Recorded',
                'date' => $row['created_at']
            ];
        }
    }
}

usort($logs, function ($a, $b) {
    return strtotime($b['date'] ?? '') <=> strtotime($a['date'] ?? '');
});

$logs = array_slice($logs, 0, $limit);


echo json_encode(['status' => 'ok', 'recent_activity' => $logs]);

