<?php
require __DIR__ . '/auth_common.php';
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/maintenance_common.php';
session_start();
header('Content-Type: application/json');

if (isset($_SESSION['role']) && maintenance_requires_logout($conn, $_SESSION['role'])) {
    maintenance_destroy_current_session();
    echo json_encode([
        'status' => 'maintenance',
        'message' => 'Maintenance mode is active. Please log in again when maintenance is complete.'
    ]);
    exit;
}

if (isset($_SESSION['role'])) {
    echo json_encode([
        'status' => 'ok',
        'user_id' => $_SESSION['user_id'] ?? null,
        'employee_number' => $_SESSION['employee_number'] ?? null,
        'user_name' => $_SESSION['user_name'] ?? null,
        'role' => $_SESSION['role'],
        'is_admin' => auth_is_admin_role($_SESSION['role']),
        'is_super_admin' => auth_is_super_admin_role($_SESSION['role'])
    ]);
} else {
    echo json_encode(['status' => 'error']);
}
?>
