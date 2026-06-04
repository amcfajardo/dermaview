<?php
// Debug wrapper for process-image.php
// Endpoint returns detailed diagnostics for the upload step.

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success'=>false,'message'=>'Invalid request']);
    exit;
}

$resp = [
    'success' => false,
    'stage' => 'upload',
    'contentType' => $_SERVER['CONTENT_TYPE'] ?? null,
    'procedure' => $_POST['procedure'] ?? '',
    'upload' => [
        'hasImage' => isset($_FILES['image']),
        'image' => null
    ],
    'phpIni' => [
        'upload_max_filesize' => ini_get('upload_max_filesize'),
        'post_max_size' => ini_get('post_max_size'),
        'upload_tmp_dir' => ini_get('upload_tmp_dir'),
        'max_execution_time' => ini_get('max_execution_time'),
        'max_input_time' => ini_get('max_input_time'),
        'max_file_uploads' => ini_get('max_file_uploads'),
        'disable_functions' => ini_get('disable_functions'),
        'memory_limit' => ini_get('memory_limit'),
    ]
];

if (!isset($_FILES['image'])) {
    $resp['message'] = 'No image uploaded (missing $_FILES[image])';
    echo json_encode($resp, JSON_PRETTY_PRINT);
    exit;
}

$resp['upload']['image'] = [
    'name' => $_FILES['image']['name'] ?? null,
    'type' => $_FILES['image']['type'] ?? null,
    'tmp_name' => $_FILES['image']['tmp_name'] ?? null,
    'error' => $_FILES['image']['error'] ?? null,
    'size' => $_FILES['image']['size'] ?? null,
    'client_mtime' => $_FILES['image']['client_mtime'] ?? null,
    'client_name' => $_FILES['image']['client_name'] ?? null,
];

// Interpret upload error
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
$resp['upload']['error_explanation'] = $explanations[$code] ?? 'Unknown upload error code';

// Try move_uploaded_file to see write permissions
$uploadDir = 'uploads/';
if (!file_exists($uploadDir)) {
    @mkdir($uploadDir, 0775, true);
}

$extension = pathinfo($_FILES['image']['name'] ?? '', PATHINFO_EXTENSION);
if (!$extension) $extension = 'jpg';

$filename = time().'_'.bin2hex(random_bytes(6)).'.'.$extension;
$inputPath = $uploadDir.$filename;

$canMove = move_uploaded_file($_FILES['image']['tmp_name'], $inputPath);
$resp['stage'] = 'move_uploaded_file';
$resp['move_uploaded_file_result'] = $canMove;
$resp['moved_to'] = $canMove ? $inputPath : null;

if ($canMove && file_exists($inputPath)) {
    $resp['success'] = true;
    $resp['message'] = 'Upload + move_uploaded_file succeeded (python not executed in debug mode).';
} else {
    $resp['message'] = 'Upload failed at move_uploaded_file stage.';
}

echo json_encode($resp, JSON_PRETTY_PRINT);

