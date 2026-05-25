<?php

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
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_processed_images_procedure (procedure_id),
            INDEX idx_processed_images_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");
}

function clean_text($value) {
    return trim((string) $value);
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
    $procedure_id = clean_text($_POST['procedure_id'] ?? '');
    $procedure_name = clean_text($_POST['procedure_name'] ?? '');
    $analysis_type = clean_text($_POST['analysis_type'] ?? 'Treatment Visualization');
    $before_image = $_POST['before_image'] ?? '';
    $after_image = $_POST['after_image'] ?? '';
    $metrics_json = $_POST['metrics_json'] ?? null;
    $recommendations_json = $_POST['recommendations_json'] ?? null;

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
        (procedure_id, procedure_name, analysis_type, before_image_path, after_image_path, metrics_json, recommendations_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->bind_param(
        "sssssss",
        $procedure_id,
        $procedure_name,
        $analysis_type,
        $before_path,
        $after_path,
        $metrics_json,
        $recommendations_json
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
        SELECT id, procedure_id, procedure_name, analysis_type, before_image_path, after_image_path, metrics_json, recommendations_json, created_at
        FROM processed_images
        ORDER BY created_at DESC, id DESC
        LIMIT 100
    ");

    $images = [];

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $images[] = [
                'id' => (int) $row['id'],
                'procedure_id' => $row['procedure_id'],
                'procedure_name' => $row['procedure_name'],
                'analysis_type' => $row['analysis_type'],
                'before_image_path' => $row['before_image_path'],
                'after_image_path' => $row['after_image_path'],
                'metrics' => $row['metrics_json'] ? json_decode($row['metrics_json'], true) : null,
                'recommendations' => $row['recommendations_json'] ? json_decode($row['recommendations_json'], true) : null,
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
