<?php

include 'config.php';

$identifier = $_POST['employee_number'];
$code = $_POST['code'];

$userQuery = $conn->prepare(
    "SELECT email FROM users
     WHERE employee_number = ? OR email = ?"
);

$userQuery->bind_param(
    "ss",
    $identifier,
    $identifier
);

$userQuery->execute();

$userResult =
    $userQuery->get_result();

if ($userResult->num_rows === 0) {
    // if identifier is an email, allow using it directly
    if (filter_var($identifier, FILTER_VALIDATE_EMAIL)) {
        $email = $identifier;
    } else {
        echo "Invalid code";
        exit;
    }
} else {
    $user = $userResult->fetch_assoc();
    $email = $user['email'];
}

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