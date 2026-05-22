<?php

include '../config.php';

$action = $_POST['action'] ?? '';

if ($action === 'add') {
    $first_name = trim($_POST['first_name']);
    $last_name = trim($_POST['last_name']);
    $email = trim($_POST['email']);
    $employee_number = trim($_POST['employee_number']);
    $role = trim($_POST['role']);
    $password = password_hash($_POST['password'], PASSWORD_DEFAULT);
    $status = "Active";
    $must_change_password = 1;

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
    $result = $conn->query("
        SELECT id, first_name, last_name, email, employee_number, role, status
        FROM users
        ORDER BY id DESC
    ");

    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $id = htmlspecialchars($row['id']);
            $name = htmlspecialchars($row['first_name'] . ' ' . $row['last_name']);
            $email = htmlspecialchars($row['email']);
            $employee_number = htmlspecialchars($row['employee_number']);
            $role = htmlspecialchars(ucfirst($row['role']));
            $status = htmlspecialchars($row['status']);
            $status_class = $row['status'] === 'Active' ? 'account-status-active' : 'account-status-inactive';

            echo "
            <tr>
              <td>$name</td>
              <td>$email</td>
              <td>$employee_number</td>
              <td>$role</td>
              <td><span class='account-status $status_class'>$status</span></td>
              <td>
                <div class='account-row-actions'>
            ";

            if ($row['status'] === 'Active') {
                echo "<button class='account-action-btn deactivate-btn' data-id='$id'>Deactivate</button>";
            } else {
                echo "<button class='account-action-btn reactivate-btn' data-id='$id'>Reactivate</button>";
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
