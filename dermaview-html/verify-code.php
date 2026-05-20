<?php

include 'config.php';

$username = $_POST['username'];
$code = $_POST['code'];

$userQuery = $conn->prepare(
    "SELECT email FROM users
     WHERE username = ?"
);

$userQuery->bind_param(
    "s",
    $username
);

$userQuery->execute();

$userResult =
    $userQuery->get_result();

$user =
    $userResult->fetch_assoc();

$email = $user['email'];

$stmt = $conn->prepare(
    "SELECT * FROM password_resets
     WHERE email = ?
     AND reset_code = ?
     ORDER BY id DESC
     LIMIT 1"
);

$stmt->bind_param(
    "ss",
    $email,
    $code
);

$stmt->execute();

$result = $stmt->get_result();

if ($result->num_rows > 0) {

    echo "Code verified";

} else {

    echo "Invalid code";

}

?>