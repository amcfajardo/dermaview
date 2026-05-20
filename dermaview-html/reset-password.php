<?php

include 'config.php';

$username = $_POST['username'];

$password = password_hash(
    $_POST['password'],
    PASSWORD_DEFAULT
);

$stmt = $conn->prepare(
    "UPDATE users
     SET password = ?
     WHERE username = ?"
);

$stmt->bind_param(
    "ss",
    $password,
    $username
);

if ($stmt->execute()) {

    echo "Password updated";

} else {

    echo "Failed to update password";

}

?>