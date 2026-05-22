<?php

use PHPMailer\PHPMailer\PHPMailer;

require 'src/PHPMailer.php';
require 'src/SMTP.php';
require 'src/Exception.php';

include 'config.php';

$identifier = trim($_POST['employee_number']);

$stmt = $conn->prepare(
    "SELECT email FROM users WHERE employee_number = ? OR email = ?"
);

$stmt->bind_param("ss", $identifier, $identifier);

$stmt->execute();

$result = $stmt->get_result();

if ($result->num_rows === 0) {

    echo "User not found";
    exit;

}

$user = $result->fetch_assoc();

$email = $user['email'];

$code = rand(1000, 9999);

$insert = $conn->prepare(
    "INSERT INTO password_resets
    (email, reset_code)
    VALUES (?, ?)"
);

$insert->bind_param(
    "ss",
    $email,
    $code
);

$insert->execute();

$mail = new PHPMailer(true);

$mail->isSMTP();

$mail->Host = 'smtp.gmail.com';

$mail->SMTPAuth = true;

$mail->Username = 'dermaview2026@gmail.com';

$mail->Password = 'grqa hghr alxb ltwq';

$mail->SMTPSecure = 'tls';

$mail->Port = 587;

$mail->setFrom(
    'dermaview2026@gmail.com',
    'DermaView'
);

$mail->addAddress($email);

$mail->isHTML(true);

$mail->Subject = 'DermaView Password Reset Code';

$mail->Body = "
    <h2>Password Reset</h2>

    <p>Your 4-digit reset code is:</p>

    <h1>$code</h1>
";

$mail->send();

echo "Code sent";

?>