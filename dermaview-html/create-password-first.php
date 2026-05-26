<?php
session_start();
include 'config.php';

if (!isset($_SESSION['user_id'])) {
    header("Location: index.html");
    exit();
}

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $new_password = $_POST['new_password'];
    $confirm_password = $_POST['confirm_password'];

    if ($new_password !== $confirm_password) {
        echo "
        <script>
            alert('Passwords do not match.');
            window.location.href = 'create-password-first.php';
        </script>
        ";
        exit();
    }

    $hashed_password = password_hash($new_password, PASSWORD_DEFAULT);
    $user_id = $_SESSION['user_id'];

    $stmt = $conn->prepare("
        UPDATE users
        SET password = ?, must_change_password = 0
        WHERE id = ?
    ");

    $stmt->bind_param("si", $hashed_password, $user_id);

    if ($stmt->execute()) {
        echo "
        <script>
            alert('Password changed successfully. Please login again.');
            window.location.href = 'index.html';
        </script>
        ";
        session_destroy();
        exit();
    } else {
        echo "
        <script>
            alert('Failed to change password.');
            window.location.href = 'create-password-first.php';
        </script>
        ";
        exit();
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DermaView | Change Password</title>
  <link rel="stylesheet" href="styles/global.css?v=20260526-6" />
  <link rel="stylesheet" href="styles/header.css" />
  <style>
    .auth-page {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px;
      background: linear-gradient(180deg, var(--color-bg-light) 0%, var(--color-bg-lighter) 100%);
    }

    .auth-card {
      width: 100%;
      max-width: 450px;
      background: var(--color-white);
      border: 1px solid var(--color-border);
      border-radius: 24px;
      padding: 40px;
      box-shadow: var(--shadow-md);
    }

    .auth-title {
      margin: 0 0 12px;
      color: var(--color-text);
      font-size: 2rem;
      font-weight: 800;
      text-align: center;
      line-height: 1.15;
    }

    .auth-subtitle {
      margin: 0 0 28px;
      color: var(--color-text-secondary);
      text-align: center;
      line-height: 1.6;
    }

    .auth-form {
      display: grid;
      gap: 18px;
    }

    .auth-input {
      width: 100%;
      min-height: 56px;
      padding: 0 16px;
      border: 1px solid #d1d5db;
      border-radius: 14px;
      background: var(--color-white);
      color: var(--color-text);
      font: inherit;
      font-size: 1rem;
      outline: none;
      transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
    }

    .auth-input:focus {
      border-color: var(--color-primary);
      box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14);
    }

    .auth-button {
      min-height: 56px;
      border: 0;
      border-radius: 14px;
      padding: 0 18px;
      background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
      color: #ffffff;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
      transition: transform var(--transition-fast), box-shadow var(--transition-fast);
    }

    .auth-button:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-hover);
    }

    @media (max-width: 560px) {
      .auth-page {
        padding: 20px;
      }

      .auth-card {
        padding: 28px 22px;
      }
    }
  </style>
</head>
<body>

<div class="auth-page">
  <div class="auth-card">
    <h1 class="auth-title">Change Password</h1>
    <p class="auth-subtitle">Create a new password before continuing to your account.</p>

    <form method="POST" class="auth-form">
      <input
        type="password"
        name="new_password"
        placeholder="New Password"
        class="auth-input"
        required
      >

      <input
        type="password"
        name="confirm_password"
        placeholder="Confirm New Password"
        class="auth-input"
        required
      >

      <button type="submit" class="auth-button">
        Save New Password
      </button>
    </form>
  </div>
</div>

<script src="system-branding.js?v=20260526-4"></script>
</body>
</html>
