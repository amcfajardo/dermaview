<?php
// Simple endpoint to debug PHP file upload diagnostics
// Usage: POST multipart/form-data with field name "image".

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success'=>false,'message'=>'Invalid request method']);
    exit;
}

$resp = [
    'success' => true,
    'requestMethod' => $_SERVER['REQUEST_METHOD'] ?? null,
    'contentType' => $_SERVER['CONTENT_TYPE'] ?? null,
    'uploadErrors' => [],
    'phpIni' => [
        'upload_max_filesize' => ini_get('upload_max_filesize'),
        'post_max_size' => ini_get('post_max_size'),
        'max_execution_time' => ini_get('max_execution_time'),
        'max_input_time' => ini_get('max_input_time'),
        'max_file_uploads' => ini_get('max_file_uploads'),
        'upload_tmp_dir' => ini_get('upload_tmp_dir'),
        'disable_functions' => ini_get('disable_functions'),
        'memory_limit' => ini_get('memory_limit'),
    ],
    'files' => []
];

if (!isset($_FILES['image'])) {
    $resp['success'] = false;
    $resp['message'] = 'No $_FILES[image] received';
} else {
    $resp['files']['image'] = [
        'name' => $_FILES['image']['name'] ?? null,
        'type' => $_FILES['image']['type'] ?? null,
        'tmp_name' => $_FILES['image']['tmp_name'] ?? null,
        'error' => $_FILES['image']['error'] ?? null,
        'size' => $_FILES['image']['size'] ?? null,
    ];

    // Provide human explanation for common upload error codes
    $code = $_FILES['image']['error'] ?? null;
    $explanations = [
        0 => 'UPLOAD_ERR_OK',
        1 => 'UPLOAD_ERR_INI_SIZE (exceeds upload_max_filesize)',
        2 => 'UPLOAD_ERR_FORM_SIZE (exceeds MAX_FILE_SIZE)',
        3 => 'UPLOAD_ERR_PARTIAL (partial upload)',
        4 => 'UPLOAD_ERR_NO_FILE (no file uploaded)',
        6 => 'UPLOAD_ERR_NO_TMP_DIR (missing tmp directory)',
        7 => 'UPLOAD_ERR_CANT_WRITE (cannot write tmp file)',
        8 => 'UPLOAD_ERR_EXTENSION (extension stopped upload)'
    ];
    $resp['uploadErrors']['image_error_code'] = $code;
    $resp['uploadErrors']['image_error_explanation'] = $explanations[$code] ?? 'Unknown upload error code';
}

echo json_encode($resp, JSON_PRETTY_PRINT);

