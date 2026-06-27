<?php

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

require 'src/Exception.php';
require 'src/PHPMailer.php';
require 'src/SMTP.php';

include 'config.php';
require_once 'password_policy.php';

function registration_html($value) {
    return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
}

function registration_prepare_mailer() {
    $mail = new PHPMailer(true);
    $mail->isSMTP();
    $mail->Host = 'smtp.gmail.com';
    $mail->SMTPAuth = true;
    $mail->Username = 'dermaview2026@gmail.com';
    $mail->Password = 'grqa hghr alxb ltwq';
    $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;
    $mail->Port = 587;
    $mail->CharSet = 'UTF-8';
    $mail->setFrom('dermaview2026@gmail.com', 'DermaView');
    $mail->isHTML(true);

    return $mail;
}

function registration_ensure_otp_table($conn) {
    $conn->query("
        CREATE TABLE IF NOT EXISTS registration_otps (
            email VARCHAR(255) NOT NULL PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            otp_hash VARCHAR(255) NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    ");

    $conn->query("DELETE FROM registration_otps WHERE expires_at < NOW()");
}

function registration_generate_employee_number($conn) {
    for ($attempt = 0; $attempt < 100; $attempt++) {
        $employee_number = (string) random_int(10000000, 99999999);
        $stmt = $conn->prepare("SELECT id FROM users WHERE employee_number = ? LIMIT 1");
        $stmt->bind_param("s", $employee_number);
        $stmt->execute();

        if ($stmt->get_result()->num_rows === 0) {
            return $employee_number;
        }
    }

    return null;
}

function registration_email_exists($conn, $email) {
    $stmt = $conn->prepare("SELECT id FROM users WHERE email = ? LIMIT 1");
    $stmt->bind_param("s", $email);
    $stmt->execute();

    return $stmt->get_result()->num_rows > 0;
}

function registration_send_admin_notice($conn, $first_name, $last_name, $email, $employee_number) {
    $adminQuery = $conn->query("
        SELECT email, first_name, last_name
        FROM users
        WHERE role IN ('admin', 'super_admin', 'superadmin')
          AND status = 'Active'
          AND email IS NOT NULL
          AND email <> ''
    ");

    if (!$adminQuery || $adminQuery->num_rows === 0) {
        return;
    }

    $adminMail = registration_prepare_mailer();

    while ($admin = $adminQuery->fetch_assoc()) {
        $adminName = trim(($admin['first_name'] ?? '') . ' ' . ($admin['last_name'] ?? ''));
        $adminMail->addAddress($admin['email'], $adminName);
    }

    $adminMail->Subject = 'New DermaView Registration Needs Role Assignment';
    $adminMail->Body = "
        <div style='font-family: Arial, sans-serif;'>
            <h2>New registration pending</h2>
            <p>A new employee account has registered and needs a role assignment.</p>
            <p><b>Name:</b> " . registration_html($first_name . ' ' . $last_name) . "</p>
            <p><b>Email:</b> " . registration_html($email) . "</p>
            <p><b>Employee Number:</b> " . registration_html($employee_number) . "</p>
            <p>Please review this account in the Staff / Employees tab and assign Admin or Staff.</p>
        </div>
    ";

    $adminMail->send();
}

registration_ensure_otp_table($conn);

$action = $_POST['action'] ?? 'request_otp';
$email = trim($_POST['email'] ?? '');
$firstName = trim($_POST['first_name'] ?? '');
$lastName = trim($_POST['last_name'] ?? '');
$password = $_POST['password'] ?? '';
$confirmPassword = $_POST['confirm_password'] ?? '';

if ($action === 'request_otp') {
    if ($email === '' || $firstName === '' || $lastName === '' || $password === '' || $confirmPassword === '') {
        echo "Please fill in all fields";
        exit;
    }

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        echo "Invalid email address";
        exit;
    }

    if ($password !== $confirmPassword) {
        echo "Passwords do not match";
        exit;
    }

    password_policy_require($password);

    if (registration_email_exists($conn, $email)) {
        echo "Email already exists";
        exit;
    }

    $otp = (string) random_int(100000, 999999);
    $passwordHash = password_hash($password, PASSWORD_DEFAULT);
    $otpHash = password_hash($otp, PASSWORD_DEFAULT);
    $stmt = $conn->prepare("
        REPLACE INTO registration_otps
        (email, first_name, last_name, password_hash, otp_hash, expires_at)
        VALUES (?, ?, ?, ?, ?, DATE_ADD(NOW(), INTERVAL 10 MINUTE))
    ");
    $stmt->bind_param("sssss", $email, $firstName, $lastName, $passwordHash, $otpHash);

    if (!$stmt->execute()) {
        echo "Failed to start registration";
        exit;
    }

    try {
        $mail = registration_prepare_mailer();
        $mail->addAddress($email, $firstName . ' ' . $lastName);
        $mail->Subject = 'DermaView Registration OTP';
        $mail->Body = "
            <div style='font-family: Arial, sans-serif;'>
                <h2>Complete your DermaView registration</h2>
                <p>Hello <b>" . registration_html($firstName) . "</b>,</p>
                <p>Your 6-digit registration OTP is:</p>
                <h1 style='letter-spacing: 4px;'>" . registration_html($otp) . "</h1>
                <p>This code expires in 10 minutes.</p>
            </div>
        ";
        $mail->send();

        echo "OTP sent";
    } catch (Exception $e) {
        echo "Failed to send OTP";
    }

    exit;
}

if ($action === 'verify_otp') {
    $otp = trim($_POST['otp'] ?? '');

    if ($email === '' || $otp === '') {
        echo "Enter the OTP sent to your email";
        exit;
    }

    if (!preg_match('/^\d{6}$/', $otp)) {
        echo "Invalid OTP";
        exit;
    }

    $stmt = $conn->prepare("
        SELECT email, first_name, last_name, password_hash, otp_hash, expires_at
        FROM registration_otps
        WHERE email = ?
        LIMIT 1
    ");
    $stmt->bind_param("s", $email);
    $stmt->execute();
    $pending = $stmt->get_result()->fetch_assoc();

    if (!$pending) {
        echo "Please request a new OTP";
        exit;
    }

    $expiryStmt = $conn->prepare("SELECT expires_at < NOW() AS is_expired FROM registration_otps WHERE email = ? LIMIT 1");
    $expiryStmt->bind_param("s", $email);
    $expiryStmt->execute();
    $expiry = $expiryStmt->get_result()->fetch_assoc();

    if ((int) ($expiry['is_expired'] ?? 1) === 1) {
        $delete = $conn->prepare("DELETE FROM registration_otps WHERE email = ?");
        $delete->bind_param("s", $email);
        $delete->execute();
        echo "OTP expired. Please request a new OTP.";
        exit;
    }

    if (!password_verify($otp, $pending['otp_hash'])) {
        echo "Incorrect OTP";
        exit;
    }

    if (registration_email_exists($conn, $email)) {
        echo "Email already exists";
        exit;
    }

    $employeeNumber = registration_generate_employee_number($conn);

    if ($employeeNumber === null) {
        echo "Failed to generate employee number";
        exit;
    }

    $role = 'pending';
    $status = 'Pending';
    $firstName = $pending['first_name'];
    $lastName = $pending['last_name'];
    $passwordHash = $pending['password_hash'];

    $insert = $conn->prepare("
        INSERT INTO users
        (email, first_name, last_name, role, employee_number, password, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ");
    $insert->bind_param("sssssss", $email, $firstName, $lastName, $role, $employeeNumber, $passwordHash, $status);

    if (!$insert->execute()) {
        echo "Registration failed";
        exit;
    }

    $delete = $conn->prepare("DELETE FROM registration_otps WHERE email = ?");
    $delete->bind_param("s", $email);
    $delete->execute();

    try {
        $mail = registration_prepare_mailer();
        $mail->addAddress($email, $firstName . ' ' . $lastName);
        $mail->Subject = 'DermaView Account Created';
        $mail->Body = "
            <div style='font-family: Arial, sans-serif;'>
                <h2>Welcome to DermaView!</h2>
                <p>Hello <b>" . registration_html($firstName) . "</b>,</p>
                <p>Your account has been created and submitted for admin review.</p>
                <p>You can sign in after an admin assigns your role.</p>
                <hr>
                <p><b>Employee Number:</b> " . registration_html($employeeNumber) . "</p>
                <hr>
                <p>Thank you for registering with DermaView.</p>
            </div>
        ";
        $mail->send();
    } catch (Exception $e) {
        echo "Registration successful but email failed";
        exit;
    }

    try {
        registration_send_admin_notice($conn, $firstName, $lastName, $email, $employeeNumber);
    } catch (Exception $e) {
        // User account creation already succeeded; admin can still see it in Staff / Employees.
    }

    echo "Registration successful";
    exit;
}

echo "Invalid action";
exit;

?>
