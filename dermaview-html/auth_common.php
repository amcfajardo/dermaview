<?php

require_once __DIR__ . '/maintenance_common.php';

function auth_start_session() {
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }
}

function auth_normalized_role() {
    auth_start_session();
    return strtolower(str_replace([' ', '-'], '_', trim((string)($_SESSION['role'] ?? ''))));
}

function auth_is_super_admin_role($role) {
    $role = strtolower(str_replace([' ', '-'], '_', trim((string)$role)));
    return in_array($role, ['super_admin', 'superadmin'], true);
}

function auth_is_admin_role($role) {
    $role = strtolower(str_replace([' ', '-'], '_', trim((string)$role)));
    return $role === 'admin' || auth_is_super_admin_role($role);
}

function auth_is_staff_role($role) {
    $role = strtolower(str_replace([' ', '-'], '_', trim((string)$role)));
    return $role === 'staff';
}

function auth_ensure_single_session_columns() {
    global $conn;
    if (!isset($conn) || !$conn) {
        return;
    }

    $result = $conn->query("SHOW COLUMNS FROM users LIKE 'active_session_token'");
    if (!$result || $result->num_rows === 0) {
        $conn->query("ALTER TABLE users ADD COLUMN active_session_token VARCHAR(128) NULL");
    }
}

function auth_create_active_session($user_id) {
    auth_start_session();
    auth_ensure_single_session_columns();

    global $conn;
    if (!isset($conn) || !$conn) {
        return null;
    }

    $token = bin2hex(random_bytes(32));
    $stmt = $conn->prepare("UPDATE users SET active_session_token = ? WHERE id = ?");
    $user_id = (int)$user_id;
    $stmt->bind_param("si", $token, $user_id);
    $stmt->execute();

    $_SESSION['active_session_token'] = $token;
    return $token;
}

function auth_current_session_is_active() {
    auth_start_session();

    if (!isset($_SESSION['user_id'])) {
        return true;
    }

    if (!isset($_SESSION['active_session_token'])) {
        return false;
    }

    auth_ensure_single_session_columns();

    global $conn;
    if (!isset($conn) || !$conn) {
        return true;
    }

    $user_id = (int)$_SESSION['user_id'];
    $stmt = $conn->prepare("SELECT active_session_token FROM users WHERE id = ? LIMIT 1");
    $stmt->bind_param("i", $user_id);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();

    if (!$row) {
        return false;
    }

    return hash_equals((string)($row['active_session_token'] ?? ''), (string)$_SESSION['active_session_token']);
}

function auth_clear_active_session_if_current() {
    auth_start_session();

    if (!isset($_SESSION['user_id'], $_SESSION['active_session_token'])) {
        return;
    }

    auth_ensure_single_session_columns();

    global $conn;
    if (!isset($conn) || !$conn) {
        return;
    }

    $user_id = (int)$_SESSION['user_id'];
    $token = (string)$_SESSION['active_session_token'];
    $stmt = $conn->prepare("UPDATE users SET active_session_token = NULL WHERE id = ? AND active_session_token = ?");
    $stmt->bind_param("is", $user_id, $token);
    $stmt->execute();
}

function auth_session_is_expired() {
    auth_start_session();

    global $conn;
    if (!isset($conn) || !isset($_SESSION['role'])) {
        return false;
    }

    $settings = maintenance_read_settings($conn);
    $timeout_minutes = (int)($settings['sessionTimeout'] ?? 30);
    $timeout_minutes = max(5, min(480, $timeout_minutes));
    $last_activity = (int)($_SESSION['last_activity_at'] ?? $_SESSION['login_at'] ?? time());

    return (time() - $last_activity) > ($timeout_minutes * 60);
}

function auth_refresh_session_activity() {
    auth_start_session();

    if (isset($_SESSION['role'])) {
        $_SESSION['last_activity_at'] = time();
    }
}

function auth_should_force_logout() {
    auth_start_session();

    global $conn;
    if (!isset($_SESSION['user_id'], $_SESSION['role']) || !isset($conn)) {
        return false;
    }

    return maintenance_requires_logout($conn, $_SESSION['role']) || auth_session_is_expired() || !auth_current_session_is_active();
}

function auth_page_redirect($path) {
    header('Location: ' . $path);
    exit();
}

function auth_require_page_login($redirect = 'index.html') {
    auth_start_session();

    if (auth_should_force_logout()) {
        maintenance_destroy_current_session();
        auth_page_redirect($redirect);
    }

    if (!isset($_SESSION['user_id'], $_SESSION['role'])) {
        auth_page_redirect($redirect);
    }

    auth_refresh_session_activity();
}

function auth_require_staff_page($redirect = 'index.html', $admin_redirect = 'admin_pages/admin.html', $super_admin_redirect = 'super_admin/super-admin.html') {
    auth_require_page_login($redirect);

    if (!auth_is_staff_role(auth_normalized_role())) {
        $role = auth_normalized_role();
        if (auth_is_super_admin_role($role)) {
            auth_page_redirect($super_admin_redirect);
        }
        if (auth_is_admin_role($role)) {
            auth_page_redirect($admin_redirect);
        }
        auth_page_redirect($redirect);
    }
}

function auth_require_admin_page($redirect = '../index.html') {
    auth_require_page_login($redirect);

    if (!auth_is_admin_role(auth_normalized_role())) {
        auth_page_redirect($redirect);
    }
}

function auth_require_super_admin_page($redirect = '../index.html') {
    auth_require_page_login($redirect);

    if (!auth_is_super_admin_role(auth_normalized_role())) {
        auth_page_redirect(auth_is_admin_role(auth_normalized_role()) ? '../admin_pages/admin.html' : $redirect);
    }
}

function auth_require_admin($json = false) {
    auth_start_session();

    if (auth_should_force_logout()) {
        maintenance_destroy_current_session();
        http_response_code(503);
        if ($json) {
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode(['status' => 'expired', 'message' => 'Session expired or signed in somewhere else. Please log in again.']);
        } else {
            echo 'Session expired or signed in somewhere else. Please log in again.';
        }
        exit();
    }

    if (isset($_SESSION['user_id']) && auth_is_admin_role(auth_normalized_role())) {
        auth_refresh_session_activity();
        return;
    }

    http_response_code(403);
    if ($json) {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['status' => 'error', 'message' => 'Admin access required.']);
    } else {
        echo 'Admin access required.';
    }
    exit();
}

function auth_require_super_admin($json = false) {
    auth_start_session();

    if (auth_should_force_logout()) {
        maintenance_destroy_current_session();
        http_response_code(503);
        if ($json) {
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode(['status' => 'expired', 'message' => 'Session expired or signed in somewhere else. Please log in again.']);
        } else {
            echo 'Session expired or signed in somewhere else. Please log in again.';
        }
        exit();
    }

    if (isset($_SESSION['user_id']) && auth_is_super_admin_role(auth_normalized_role())) {
        auth_refresh_session_activity();
        return;
    }

    http_response_code(403);
    if ($json) {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['status' => 'error', 'message' => 'Super admin access required.']);
    } else {
        echo 'Super admin access required.';
    }
    exit();
}

?>