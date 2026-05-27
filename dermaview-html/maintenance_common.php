<?php

function maintenance_normalized_role_value($role) {
    return strtolower(str_replace([' ', '-'], '_', trim((string) $role)));
}

function maintenance_is_super_admin_role($role) {
    return in_array(maintenance_normalized_role_value($role), ['super_admin', 'superadmin'], true);
}

function maintenance_default_settings() {
    return [
        'maintenanceMode' => 'off',
        'maintenanceStartedAt' => ''
    ];
}

function maintenance_ensure_settings_table($conn) {
    $conn->query("
        CREATE TABLE IF NOT EXISTS system_settings (
            id TINYINT UNSIGNED NOT NULL PRIMARY KEY DEFAULT 1,
            settings_json LONGTEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");
}

function maintenance_read_settings($conn) {
    maintenance_ensure_settings_table($conn);

    $result = $conn->query("SELECT settings_json FROM system_settings WHERE id = 1");
    if (!$result || $result->num_rows === 0) {
        return maintenance_default_settings();
    }

    $row = $result->fetch_assoc();
    $saved = json_decode($row['settings_json'] ?? '', true);
    if (!is_array($saved)) {
        $saved = [];
    }

    return array_merge(maintenance_default_settings(), $saved);
}

function maintenance_is_active($conn) {
    $settings = maintenance_read_settings($conn);
    return ($settings['maintenanceMode'] ?? 'off') === 'on';
}

function maintenance_destroy_current_session() {
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }

    $_SESSION = [];

    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(
            session_name(),
            '',
            time() - 42000,
            $params['path'],
            $params['domain'],
            $params['secure'],
            $params['httponly']
        );
    }

    session_destroy();
}

function maintenance_requires_logout($conn, $role) {
    return maintenance_is_active($conn) && !maintenance_is_super_admin_role($role);
}

?>
