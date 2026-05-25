<?php
require __DIR__ . '/audit_common.php';

include __DIR__ . '/config.php';

session_start();
header('Content-Type: application/json; charset=utf-8');

audit_ensure_tables($conn);

// Only authenticated users can set presence
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['status' => 'error', 'message' => 'Not authenticated']);
    exit();
}

presence_touch($conn);

echo json_encode(['status' => 'ok']);
?>

