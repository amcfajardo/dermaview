<?php

session_start();

include 'config.php';

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

$user = $result->fetch_assoc();

if (password_verify($password, $user['password'])) {
    $_SESSION['user_id'] = $user['id'];
    $_SESSION['employee_number'] = $user['employee_number'] ?? null;
    $_SESSION['role'] = $user['role'];

if ($user['must_change_password'] == 1) {
    $_SESSION['user_id'] = $user['id'];
    header("Location: change-password-first.php");
    exit();
}

    echo json_encode(['status' => 'ok', 'role' => $user['role']]);
} else {
    echo json_encode(['status' => 'error', 'message' => 'Incorrect password']);
}

?>