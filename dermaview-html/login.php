<?php

session_start();

include 'config.php';

$username = trim($_POST['username']);
$password = $_POST['password'];

if (
    empty($username) ||
    empty($password)
) {
    echo "Please fill in all fields";
    exit;
}

$stmt = $conn->prepare(
    "SELECT * FROM users
     WHERE username = ?"
);

$stmt->bind_param("s", $username);

$stmt->execute();

$result = $stmt->get_result();

if ($result->num_rows === 0) {
    echo "User not found";
    exit;
}

$user = $result->fetch_assoc();

if (
    password_verify(
        $password,
        $user['password']
    )
) {

    $_SESSION['user_id'] = $user['id'];
    $_SESSION['username'] = $user['username'];
    $_SESSION['role'] = $user['role'];

    echo "Login successful";

} else {
    echo "Incorrect password";
}

?>