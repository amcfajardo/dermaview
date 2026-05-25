<?php
require __DIR__ . '/auth_common.php';
require __DIR__ . '/audit_common.php';

include __DIR__ . '/config.php';

session_start();
header('Content-Type: application/json; charset=utf-8');

audit_ensure_tables($conn);

if (!isset($_SESSION['user_id'])) {
    echo json_encode(['status' => 'error', 'message' => 'Not authenticated']);
    exit();
}

if (!auth_is_admin_role($_SESSION['role'] ?? '')) {
    http_response_code(403);
    echo json_encode(['status' => 'error', 'message' => 'Admin access required']);
    exit();
}

$within = isset($_GET['within']) ? (int)$_GET['within'] : 90;
$within = max(10, $within);

$users = presence_get_online_users($conn, $within);

echo json_encode(['status' => 'ok', 'online_users' => $users]);

