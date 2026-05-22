<?php

include 'config.php';

$identifier = trim($_POST['employee_number']);

$password = password_hash(
    $_POST['password'],
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