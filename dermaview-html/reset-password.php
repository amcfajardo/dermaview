<?php

include 'config.php';
require_once 'password_policy.php';

$identifier = trim($_POST['employee_number']);
$plain_password = $_POST['password'] ?? '';
$confirm_password = $_POST['confirm_password'] ?? '';

if ($plain_password !== $confirm_password) {
    echo "Passwords do not match";
    exit;
}

password_policy_require($plain_password);

$password = password_hash(
    $plain_password,
    PASSWORD_DEFAULT
);

$stmt = $conn->prepare(
    "UPDATE users
     SET password = ?
     WHERE employee_number = ? OR email = ?"
);

$stmt->bind_param(
    "sss",
    $password,
    $identifier,
    $identifier
);

if ($stmt->execute()) {

    echo "Password updated";

} else {

    echo "Failed to update password";

}

?>
