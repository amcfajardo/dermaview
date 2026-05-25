<?php

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

function auth_require_admin($json = false) {
    auth_start_session();

    if (isset($_SESSION['user_id']) && auth_is_admin_role(auth_normalized_role())) {
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

    if (isset($_SESSION['user_id']) && auth_is_super_admin_role(auth_normalized_role())) {
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
