<?php

require_once '../auth_common.php';
include '../config.php';

auth_require_admin(false);

$action = $_POST['action'] ?? '';

$allowed_roles = ['staff'];

$staff_role_sql = "'staff'";

function role_label($role) {
    $labels = [
        'staff' => 'Staff'
    ];

    return $labels[strtolower($role)] ?? ucfirst(str_replace('_', ' ', $role));
}

if ($action === 'add') {
    $first_name = trim($_POST['first_name']);
    $last_name = trim($_POST['last_name']);
    $email = trim($_POST['email']);
    $employee_number = trim($_POST['employee_number']);
    $role = strtolower(trim($_POST['role']));
    $password = password_hash($_POST['password'], PASSWORD_DEFAULT);
    $status = "Active";
    $must_change_password = 1;
    if (!in_array($role, $allowed_roles, true)) {
        echo "Invalid role selected.";
        exit();
    }

    $stmt = $conn->prepare("
        INSERT INTO users
        (email, first_name, last_name, role, employee_number, password, status, must_change_password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ");

    $stmt->bind_param(
        "sssssssi",
        $email,
        $first_name,
        $last_name,
        $role,
        $employee_number,
        $password,
        $status,
        $must_change_password
    );

    if ($stmt->execute()) {
        echo "Account added successfully.";
    } else {
        echo "Failed to add account. Email or employee number may already exist.";
    }

    exit();
}

if ($action === 'update') {
    $id = (int) ($_POST['id'] ?? 0);
    $first_name = trim($_POST['first_name'] ?? '');
    $last_name = trim($_POST['last_name'] ?? '');
    $email = trim($_POST['email'] ?? '');
    $employee_number = trim($_POST['employee_number'] ?? '');
    $role = strtolower(trim($_POST['role'] ?? ''));

    if ($id <= 0 || $first_name === '' || $last_name === '' || $email === '' || $employee_number === '') {
        echo "Please complete all account fields.";
        exit();
    }

    if (!in_array($role, $allowed_roles, true)) {
        echo "Invalid role selected.";
        exit();
    }

    $stmt = $conn->prepare("
        UPDATE users
        SET first_name = ?, last_name = ?, email = ?, employee_number = ?, role = ?
        WHERE id = ?
          AND role IN ($staff_role_sql)
    ");

    $stmt->bind_param("sssssi", $first_name, $last_name, $email, $employee_number, $role, $id);

    echo ($stmt->execute() && $stmt->affected_rows >= 0)
        ? "Account updated."
        : "Failed to update account. Email or employee number may already exist.";

    exit();
}

if ($action === 'reset_password') {
    $id = (int) ($_POST['id'] ?? 0);
    $password = trim($_POST['password'] ?? '');

    if ($id <= 0 || strlen($password) < 6) {
        echo "Enter a temporary password with at least 6 characters.";
        exit();
    }

    $hash = password_hash($password, PASSWORD_DEFAULT);
    $must_change_password = 1;

    $stmt = $conn->prepare("
        UPDATE users
        SET password = ?, must_change_password = ?
        WHERE id = ?
          AND role IN ($staff_role_sql)
    ");

    $stmt->bind_param("sii", $hash, $must_change_password, $id);

    echo ($stmt->execute() && $stmt->affected_rows > 0)
        ? "Password reset. The user must change it on next sign-in."
        : "Failed to reset password.";

    exit();
}

if ($action === 'deactivate') {
    $id = (int) ($_POST['id'] ?? 0);

    if ($id <= 0) {
        echo "Invalid account.";
        exit();
    }

    $stmt = $conn->prepare("
        UPDATE users
        SET status = 'Inactive'
        WHERE id = ?
          AND role IN ($staff_role_sql)
    ");

    $stmt->bind_param("i", $id);

    if ($stmt->execute() && $stmt->affected_rows > 0) {
        echo "Account deactivated.";
    } else {
        echo "Failed to deactivate account.";
    }

    exit();
}

if ($action === 'reactivate') {
    $id = (int) ($_POST['id'] ?? 0);

    if ($id <= 0) {
        echo "Invalid account.";
        exit();
    }

    $stmt = $conn->prepare("
        UPDATE users
        SET status = 'Active'
        WHERE id = ?
          AND role IN ($staff_role_sql)
    ");

    $stmt->bind_param("i", $id);

    if ($stmt->execute() && $stmt->affected_rows > 0) {
        echo "Account reactivated.";
    } else {
        echo "Failed to reactivate account.";
    }

    exit();
}

if ($action === 'fetch') {
    $scope = $_POST['scope'] ?? 'all';
    $role_filter = '';

    if ($scope === 'admin') {
        $role_filter = "WHERE 1 = 0";
    } elseif ($scope === 'staff') {
        $role_filter = "WHERE role IN ($staff_role_sql)";
    }

    $result = $conn->query("
        SELECT id, first_name, last_name, email, employee_number, role, status
        FROM users
        $role_filter
        ORDER BY id DESC
    ");

    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $id = htmlspecialchars($row['id']);
            $name = htmlspecialchars($row['first_name'] . ' ' . $row['last_name']);
            $email = htmlspecialchars($row['email']);
            $employee_number = htmlspecialchars($row['employee_number']);
            $role_key = strtolower($row['role']);
            $role = htmlspecialchars(role_label($role_key));
            $status = htmlspecialchars($row['status']);
            $status_class = $row['status'] === 'Active' ? 'account-status-active' : 'account-status-inactive';
            $first_name = htmlspecialchars($row['first_name']);
            $last_name = htmlspecialchars($row['last_name']);
            $role_raw = htmlspecialchars($role_key);

            echo "
            <tr
              data-id='$id'
              data-first-name='$first_name'
              data-last-name='$last_name'
              data-email='$email'
              data-employee-number='$employee_number'
              data-role='$role_raw'
            >
              <td>$name</td>
              <td>$email</td>
              <td>$employee_number</td>
              <td>$role</td>
              <td><span class='account-status $status_class'>$status</span></td>
              <td>
                <div class='account-row-actions'>
                  <button type='button' class='account-action-btn edit-account-btn' data-id='$id'>Edit</button>
                  <button type='button' class='account-action-btn reset-password-btn' data-id='$id'>Reset Password</button>
            ";

            if ($row['status'] === 'Active') {
                echo "<button type='button' class='account-action-btn deactivate-btn' data-id='$id'>Deactivate</button>";
            } else {
                echo "<button type='button' class='account-action-btn reactivate-btn' data-id='$id'>Reactivate</button>";
            }

            echo "
                </div>
              </td>
            </tr>
            ";
        }
    } else {
        echo "
        <tr>
          <td colspan='6' style='text-align:center;'>
            No accounts found.
          </td>
        </tr>
        ";
    }

    exit();
}

echo "Invalid action.";
exit();

?>
