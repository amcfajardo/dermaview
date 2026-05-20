<?php

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

require 'src/Exception.php';
require 'src/PHPMailer.php';
require 'src/SMTP.php';

include 'config.php';

/*
|--------------------------------------------------------------------------
| GET FORM DATA
|--------------------------------------------------------------------------
*/

$email = trim($_POST['email'] ?? '');
$firstName = trim($_POST['first_name'] ?? '');
$lastName = trim($_POST['last_name'] ?? '');
$role = trim($_POST['role'] ?? '');
$username = trim($_POST['username'] ?? '');
$password = $_POST['password'] ?? '';

/*
|--------------------------------------------------------------------------
| VALIDATION
|--------------------------------------------------------------------------
*/

if (
    empty($email) ||
    empty($firstName) ||
    empty($lastName) ||
    empty($role) ||
    empty($username) ||
    empty($password)
) {
    echo "Please fill in all fields";
    exit;
}

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    echo "Invalid email address";
    exit;
}

/*
|--------------------------------------------------------------------------
| CHECK EXISTING USER
|--------------------------------------------------------------------------
*/

$checkUser = $conn->prepare(
    "SELECT id FROM users WHERE email = ? OR username = ?"
);

$checkUser->bind_param("ss", $email, $username);

$checkUser->execute();

$result = $checkUser->get_result();

if ($result->num_rows > 0) {
    echo "Email or username already exists";
    exit;
}

/*
|--------------------------------------------------------------------------
| HASH PASSWORD
|--------------------------------------------------------------------------
*/

$hashedPassword = password_hash(
    $password,
    PASSWORD_DEFAULT
);

/*
|--------------------------------------------------------------------------
| INSERT USER
|--------------------------------------------------------------------------
*/

$stmt = $conn->prepare(
    "INSERT INTO users
    (
        email,
        first_name,
        last_name,
        role,
        username,
        password
    )
    VALUES (?, ?, ?, ?, ?, ?)"
);

$stmt->bind_param(
    "ssssss",
    $email,
    $firstName,
    $lastName,
    $role,
    $username,
    $hashedPassword
);

/*
|--------------------------------------------------------------------------
| SAVE USER
|--------------------------------------------------------------------------
*/

if ($stmt->execute()) {

    /*
    |--------------------------------------------------------------------------
    | SEND EMAIL
    |--------------------------------------------------------------------------
    */

    $mail = new PHPMailer(true);

    try {

        $mail->isSMTP();

        $mail->Host = 'smtp.gmail.com';

        $mail->SMTPAuth = true;

        /*
        |--------------------------------------------------------------------------
        | YOUR GMAIL
        |--------------------------------------------------------------------------
        */

        $mail->Username = 'dermaview2026@gmail.com';

        /*
        |--------------------------------------------------------------------------
        | GOOGLE APP PASSWORD
        |--------------------------------------------------------------------------
        */

        $mail->Password = 'grqa hghr alxb ltwq';

        /*
        |--------------------------------------------------------------------------
        | SMTP SETTINGS
        |--------------------------------------------------------------------------
        */

        $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;

        $mail->Port = 587;

        $mail->CharSet = 'UTF-8';

        /*
        |--------------------------------------------------------------------------
        | EMAIL CONTENT
        |--------------------------------------------------------------------------
        */

        $mail->setFrom(
            'dermaview2026@gmail.com',
            'DermaView'
        );

        $mail->addAddress(
            $email,
            $firstName . ' ' . $lastName
        );

        $mail->isHTML(true);

        $mail->Subject = 'Welcome to DermaView';

        $mail->Body = "
            <div style='font-family: Arial, sans-serif;'>

                <h2>
                    Welcome to DermaView!
                </h2>

                <p>
                    Hello <b>$firstName</b>,
                </p>

                <p>
                    Your account has been successfully created.
                </p>

                <hr>

                <p>
                    <b>Username:</b> $username
                </p>

                <p>
                    <b>Role:</b> $role
                </p>

                <hr>

                <p>
                    Thank you for registering with DermaView.
                </p>

            </div>
        ";

        $mail->send();

        echo "Registration successful";

    } catch (Exception $e) {

        echo "Registered but email failed: " .
             $mail->ErrorInfo;

    }

} else {

    echo "Registration failed";

}

?>