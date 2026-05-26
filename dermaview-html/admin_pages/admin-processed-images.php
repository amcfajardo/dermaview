<?php

require_once '../auth_common.php';
auth_start_session();
include '../config.php';

header('Content-Type: application/json; charset=utf-8');

function ensure_processed_images_table($conn) {
    $conn->query("
        CREATE TABLE IF NOT EXISTS processed_images (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            procedure_id VARCHAR(120) NOT NULL,
            procedure_name VARCHAR(180) NOT NULL,
            analysis_type VARCHAR(80) NOT NULL DEFAULT 'Treatment Visualization',
            before_image_path VARCHAR(255) NOT NULL,
            after_image_path VARCHAR(255) NOT NULL,
            metrics_json LONGTEXT NULL,
            recommendations_json LONGTEXT NULL,
            handled_by VARCHAR(160) NULL,
            handled_by_user_id INT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_processed_images_procedure (procedure_id),
            INDEX idx_processed_images_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");

    ensure_processed_images_column($conn, 'handled_by', "ALTER TABLE processed_images ADD COLUMN handled_by VARCHAR(160) NULL AFTER recommendations_json");
    ensure_processed_images_column($conn, 'handled_by_user_id', "ALTER TABLE processed_images ADD COLUMN handled_by_user_id INT NULL AFTER handled_by");
}

function ensure_processed_images_column($conn, $column_name, $alter_sql) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS total
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'processed_images'
          AND column_name = ?
    ");

    if (!$stmt) {
        return;
    }

    $stmt->bind_param("s", $column_name);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result ? $result->fetch_assoc() : null;

    if (!$row || (int) $row['total'] === 0) {
        $conn->query($alter_sql);
    }
}

function clean_text($value) {
    return trim((string) $value);
}

function is_processing_staff_role($role) {
    $role = strtolower(str_replace([' ', '-'], '_', trim((string) $role)));
    return $role === 'staff';
}

function require_processing_staff_user($conn) {
    $user_id = isset($_SESSION['user_id']) ? (int) $_SESSION['user_id'] : 0;
    $employee_number = clean_text($_SESSION['employee_number'] ?? '');
    $session_name = clean_text($_SESSION['user_name'] ?? '');

    if ($user_id <= 0 && $employee_number === '' && $session_name === '') {
        http_response_code(403);
        echo json_encode([
            'status' => 'error',
            'message' => 'Staff login required. Please log in again from the staff account.'
        ]);
        exit();
    }

    if ($user_id > 0) {
        $stmt = $conn->prepare("
        SELECT id, first_name, last_name, email, employee_number, role, status
        FROM users
        WHERE id = ?
        LIMIT 1
        ");
        $bind_type = "i";
        $bind_value = $user_id;
    } else {
        $stmt = $conn->prepare("
        SELECT id, first_name, last_name, email, employee_number, role, status
        FROM users
        WHERE employee_number = ?
           OR email = ?
           OR TRIM(CONCAT(first_name, ' ', last_name)) = ?
        LIMIT 1
        ");
        $bind_type = "sss";
        $bind_value = $employee_number !== '' ? $employee_number : $session_name;
    }

    if (!$stmt) {
        http_response_code(500);
        echo json_encode([
            'status' => 'error',
            'message' => 'Unable to verify staff account.'
        ]);
        exit();
    }

    if ($bind_type === "i") {
        $stmt->bind_param($bind_type, $bind_value);
    } else {
        $stmt->bind_param($bind_type, $bind_value, $bind_value, $bind_value);
    }

    $stmt->execute();
    $result = $stmt->get_result();
    $user = $result ? $result->fetch_assoc() : null;

    if (!$user || !is_processing_staff_role($user['role'] ?? '') || strcasecmp((string) ($user['status'] ?? ''), 'Inactive') === 0) {
        $seen_role = $user ? clean_text($user['role'] ?? '') : clean_text($_SESSION['role'] ?? '');
        $seen_status = $user ? clean_text($user['status'] ?? '') : '';
        http_response_code(403);
        echo json_encode([
            'status' => 'error',
            'message' => 'Staff account required.' . ($seen_role !== '' ? ' Current session role: ' . $seen_role . '.' : '') . ($seen_status !== '' ? ' Status: ' . $seen_status . '.' : '')
        ]);
        exit();
    }

    return $user;
}

function staff_name_from_user($user) {
    $name = trim(($user['first_name'] ?? '') . ' ' . ($user['last_name'] ?? ''));

    if ($name !== '') {
        return $name;
    }

    $fallback = trim($user['email'] ?? $user['employee_number'] ?? '');

    if ($fallback !== '') {
        return $fallback;
    }

    return 'Staff #' . (int) ($user['id'] ?? 0);
}

function ensure_archive_directories() {
    $root = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'archive';
    $dirs = [
        $root . DIRECTORY_SEPARATOR . 'files',
        $root . DIRECTORY_SEPARATOR . 'images'
    ];

    foreach ($dirs as $dir) {
        if (!is_dir($dir)) {
            mkdir($dir, 0775, true);
        }
    }
}

function save_data_url_image($data_url, $prefix) {
    if (!preg_match('/^data:image\/(png|jpe?g|webp);base64,/', $data_url, $matches)) {
        return null;
    }

    $extension = strtolower($matches[1]);
    if ($extension === 'jpeg') {
        $extension = 'jpg';
    }

    $base64 = substr($data_url, strpos($data_url, ',') + 1);
    $binary = base64_decode($base64, true);

    if ($binary === false) {
        return null;
    }

    $upload_dir = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'processed_uploads';

    if (!is_dir($upload_dir)) {
        mkdir($upload_dir, 0775, true);
    }

    $file_name = $prefix . '-' . date('Ymd-His') . '-' . bin2hex(random_bytes(4)) . '.' . $extension;
    $file_path = $upload_dir . DIRECTORY_SEPARATOR . $file_name;

    if (file_put_contents($file_path, $binary) === false) {
        return null;
    }

    return 'processed_uploads/' . $file_name;
}

ensure_processed_images_table($conn);
ensure_archive_directories();

$action = $_POST['action'] ?? 'fetch_json';

if ($action === 'add') {
    $processing_staff_user = require_processing_staff_user($conn);
}

if ($action === 'fetch_json') {
    auth_require_admin(true);
}

if ($action === 'add') {
    $procedure_id = clean_text($_POST['procedure_id'] ?? '');
    $procedure_name = clean_text($_POST['procedure_name'] ?? '');
    $analysis_type = clean_text($_POST['analysis_type'] ?? 'Treatment Visualization');
    $before_image = $_POST['before_image'] ?? '';
    $after_image = $_POST['after_image'] ?? '';
    $metrics_json = $_POST['metrics_json'] ?? null;
    $recommendations_json = $_POST['recommendations_json'] ?? null;
    $handled_by_user_id = (int) $processing_staff_user['id'];
    $handled_by = staff_name_from_user($processing_staff_user);

    if ($procedure_id === '' || $procedure_name === '' || $before_image === '' || $after_image === '') {
        http_response_code(422);
        echo json_encode([
            'status' => 'error',
            'message' => 'Missing image record details.'
        ]);
        exit();
    }

    $before_path = save_data_url_image($before_image, 'before');
    $after_path = save_data_url_image($after_image, 'after');

    if (!$before_path || !$after_path) {
        http_response_code(422);
        echo json_encode([
            'status' => 'error',
            'message' => 'Unable to save analyzed images.'
        ]);
        exit();
    }

    $stmt = $conn->prepare("
        INSERT INTO processed_images
        (procedure_id, procedure_name, analysis_type, before_image_path, after_image_path, metrics_json, recommendations_json, handled_by, handled_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->bind_param(
        "ssssssssi",
        $procedure_id,
        $procedure_name,
        $analysis_type,
        $before_path,
        $after_path,
        $metrics_json,
        $recommendations_json,
        $handled_by,
        $handled_by_user_id
    );

    if ($stmt->execute()) {
        echo json_encode([
            'status' => 'ok',
            'message' => 'Analyzed images saved.',
            'id' => $stmt->insert_id
        ]);
    } else {
        http_response_code(500);
        echo json_encode([
            'status' => 'error',
            'message' => 'Failed to save image record.'
        ]);
    }

    exit();
}

if ($action === 'fetch_json') {
    $result = $conn->query("
        SELECT id, procedure_id, procedure_name, analysis_type, before_image_path, after_image_path,
               metrics_json, recommendations_json, handled_by, handled_by_user_id, created_at
        FROM processed_images
        ORDER BY created_at DESC, id DESC
        LIMIT 100
    ");

    $images = [];

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $handled_by = trim((string) ($row['handled_by'] ?? ''));
            if ($handled_by === '' || strcasecmp($handled_by, 'System') === 0) {
                $handled_by = 'Not recorded';
            }

            $images[] = [
                'id' => (int) $row['id'],
                'procedure_id' => $row['procedure_id'],
                'procedure_name' => $row['procedure_name'],
                'analysis_type' => $row['analysis_type'],
                'before_image_path' => $row['before_image_path'],
                'after_image_path' => $row['after_image_path'],
                'metrics' => $row['metrics_json'] ? json_decode($row['metrics_json'], true) : null,
                'recommendations' => $row['recommendations_json'] ? json_decode($row['recommendations_json'], true) : null,
                'handled_by' => $handled_by,
                'handled_by_user_id' => $row['handled_by_user_id'] !== null ? (int) $row['handled_by_user_id'] : null,
                'created_at' => $row['created_at']
            ];
        }
    }

    echo json_encode([
        'status' => 'ok',
        'images' => $images
    ]);
    exit();
}

http_response_code(400);
echo json_encode([
    'status' => 'error',
    'message' => 'Invalid action.'
]);

?>
