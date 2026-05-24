<?php
session_start();
include 'config.php';

if (!isset($_SESSION['user_id'])) {
    header("Location: login.html");
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
            window.location.href = 'login.html';
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
<html>
<head>
  <title>Change Password</title>
  <link rel="stylesheet" href="styles/global.css">
</head>
<body>

<div class="auth-page">
  <div class="auth-card">
    <h1>Change Password</h1>

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

</body>
</html>
