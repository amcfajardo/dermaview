<?php

session_start();

include 'config.php';
require_once __DIR__ . '/auth_common.php';

$identifier = trim($_POST['employee_number'] ?? '');
$password = $_POST['password'] ?? '';

header('Content-Type: application/json');

if (empty($identifier) || empty($password)) {
    echo json_encode(['status' => 'error', 'message' => 'Please fill in all fields']);
    exit;
}

$stmt = $conn->prepare(
    "SELECT * FROM users
     WHERE employee_number = ? OR email = ?"
);

$stmt->bind_param("ss", $identifier, $identifier);

$stmt->execute();

$result = $stmt->get_result();

if ($result->num_rows === 0) {
    echo json_encode(['status' => 'error', 'message' => 'User not found']);
    exit;
}

$account = $result->fetch_assoc();

if (($account['status'] ?? '') === 'Inactive') {
    echo json_encode(['status' => 'error', 'message' => 'This account has been deactivated']);
    exit;
}

$account_role = $account['role'];

if (($account['status'] ?? '') === 'Pending' || strtolower((string) $account_role) === 'pending') {
    echo json_encode(['status' => 'error', 'message' => 'Your registration is pending admin role assignment.']);
    exit;
}

if (password_verify($password, $account['password'])) {
    if (maintenance_requires_logout($conn, $account_role)) {
        echo json_encode([
            'status' => 'error',
            'message' => 'Maintenance mode is active. Only Super Admin can log in.'
        ]);
        exit;
    }

    $_SESSION['user_id'] = $account['id'];
    $_SESSION['employee_number'] = $account['employee_number'] ?? null;
    $_SESSION['role'] = $account_role;
    $_SESSION['user_name'] = trim(($account['first_name'] ?? '') . ' ' . ($account['last_name'] ?? ''));
    $_SESSION['login_at'] = time();
    $_SESSION['last_activity_at'] = time();
    auth_create_active_session((int)$account['id']);

    // Presence: touch immediately on successful login
    try {
        require_once __DIR__ . '/audit_common.php';
        presence_touch($conn);
    } catch (Throwable $e) {}


    if ((int) ($account['must_change_password'] ?? 0) === 1) {
        echo json_encode([
            'status' => 'ok',
            'role' => $account_role,
            'redirect' => 'create-password-first.php'
        ]);
        exit;
    }

    echo json_encode(['status' => 'ok', 'role' => $account_role]);
} else {
    echo json_encode(['status' => 'error', 'message' => 'Incorrect password']);
}

?>
