<?php
require __DIR__ . '/auth_common.php';
session_start();
header('Content-Type: application/json');
if (isset($_SESSION['role'])) {
    echo json_encode([
        'status' => 'ok',
        'role' => $_SESSION['role'],
        'is_admin' => auth_is_admin_role($_SESSION['role']),
        'is_super_admin' => auth_is_super_admin_role($_SESSION['role'])
    ]);
} else {
    echo json_encode(['status' => 'error']);
}
?>
