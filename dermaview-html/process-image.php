<?php

header('Content-Type: application/json');
$requestStart = microtime(true);

function process_read_system_settings() {
    $settings = [
        'uploadSizeLimit' => '10 MB',
        'allowedImageTypes' => 'JPG, PNG, WEBP'
    ];

    $config_path = __DIR__ . '/config.php';
    if (!is_file($config_path)) {
        return $settings;
    }

    include $config_path;
    if (!isset($conn) || !$conn) {
        return $settings;
    }

    $result = $conn->query("SELECT settings_json FROM system_settings WHERE id = 1");
    if ($result && $result->num_rows > 0) {
        $row = $result->fetch_assoc();
        $saved = json_decode($row['settings_json'] ?? '', true);
        if (is_array($saved)) {
            $settings = array_merge($settings, $saved);
        }
    }

    return $settings;
}

function process_size_limit_bytes($value) {
    if (!preg_match('/(\d+(?:\.\d+)?)\s*(kb|mb|gb)?/i', (string)$value, $matches)) {
        return 10 * 1024 * 1024;
    }

    $number = (float)$matches[1];
    $unit = strtolower($matches[2] ?? 'mb');
    if ($unit === 'gb') return (int)round($number * 1024 * 1024 * 1024);
    if ($unit === 'kb') return (int)round($number * 1024);
    return (int)round($number * 1024 * 1024);
}

function process_allowed_extensions($value) {
    $extensions = preg_split('/[\s,]+/', strtolower((string)$value));
    $extensions = array_filter(array_map(function ($item) {
        $item = ltrim(trim($item), '.');
        return $item === 'jpeg' ? 'jpg' : $item;
    }, $extensions));

    return $extensions ?: ['jpg', 'png', 'webp'];
}

function processing_timing_payload(float $requestStart, float $scriptStart, float $scriptEnd): array {
    return [
        'script_ms' => (int)round(($scriptEnd - $scriptStart) * 1000),
        'total_ms' => (int)round((microtime(true) - $requestStart) * 1000),
        'script_seconds' => round($scriptEnd - $scriptStart, 3),
        'total_seconds' => round(microtime(true) - $requestStart, 3),
    ];
}

function run_procedure_script(
    string $procedure,
    string $pythonScript,
    string $failureMessage,
    string $inputPath,
    string $outputPath,
    string $webOutputPath,
    float $requestStart,
    float $intensity = 1.0
): void {
    $command =
        "python \"$pythonScript\" " .
        escapeshellarg($inputPath) . " " .
        escapeshellarg($outputPath) . " " .
        escapeshellarg((string)$intensity) . " 2>&1";

    $scriptStart = microtime(true);
    exec($command, $output, $status);
    $scriptEnd = microtime(true);
    $timing = processing_timing_payload($requestStart, $scriptStart, $scriptEnd);

    if ($status === 0 && file_exists($outputPath)) {
        echo json_encode([
            "success" => true,
            "image" => $webOutputPath,
            "procedure" => $procedure,
            "timing" => $timing
        ]);
    } else {
        echo json_encode([
            "success" => false,
            "message" => $failureMessage,
            "debug" => $output,
            "command" => $command,
            "outputPath" => $outputPath,
            "procedure" => $procedure,
            "timing" => $timing
        ]);
    }

    exit;
}


/*
|--------------------------------------------------------------------------
| CHECK REQUEST METHOD
|--------------------------------------------------------------------------
*/

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {

    echo json_encode([
        "success" => false,
        "message" => "Invalid request"
    ]);

    exit;
}

/*
|--------------------------------------------------------------------------
| CHECK IMAGE
|--------------------------------------------------------------------------
*/

if (!isset($_FILES['image'])) {

    echo json_encode([
        "success" => false,
        "message" => "No image uploaded"
    ]);

    exit;
}

$systemSettings = process_read_system_settings();
$sizeLimitBytes = process_size_limit_bytes($systemSettings['uploadSizeLimit'] ?? '10 MB');
$allowedExtensions = process_allowed_extensions($systemSettings['allowedImageTypes'] ?? 'JPG, PNG, WEBP');
$uploadedExtension = strtolower(pathinfo($_FILES['image']['name'] ?? '', PATHINFO_EXTENSION));
if ($uploadedExtension === 'jpeg') {
    $uploadedExtension = 'jpg';
}

if (($_FILES['image']['size'] ?? 0) > $sizeLimitBytes) {
    echo json_encode([
        "success" => false,
        "message" => "Image exceeds the configured upload size limit"
    ]);
    exit;
}

if (!in_array($uploadedExtension, $allowedExtensions, true)) {
    echo json_encode([
        "success" => false,
        "message" => "Image type is not allowed by system settings"
    ]);
    exit;
}

/*
|--------------------------------------------------------------------------
| GET PROCEDURE
|--------------------------------------------------------------------------
*/

$procedure = $_POST['procedure'] ?? '';

/*
|--------------------------------------------------------------------------
| CREATE UPLOADS FOLDER
|--------------------------------------------------------------------------
*/

$baseDir = dirname(__FILE__) . DIRECTORY_SEPARATOR;


$uploadDirWeb = "uploads/";
$uploadDir = $baseDir . $uploadDirWeb;

$archiveDirsWeb = [
    "archive/files/",
    "archive/images/"
];
$archiveDirs = [];
foreach ($archiveDirsWeb as $dweb) {
    $archiveDirs[] = $baseDir . $dweb;
}

function ensureWritableDir(string $dir, string $dirWeb): array {
    if (!is_dir($dir)) {
        @mkdir($dir, 0775, true);
    }


    $exists = is_dir($dir);
    $writable = is_writable($dir);

    return [
        'dir' => $dir,
        'dirWeb' => $dirWeb,
        'exists' => $exists,
        'writable' => $writable,
    ];
}

$uploadStatus = ensureWritableDir($uploadDir, $uploadDirWeb);
$archiveStatus = [];
foreach ($archiveDirs as $idx => $adir) {
    $archiveStatus[] = ensureWritableDir($adir, $archiveDirsWeb[$idx]);
}

if (!$uploadStatus['exists'] || !$uploadStatus['writable']) {
    echo json_encode([
        "success" => false,
        "message" => "Upload directory is not writable",
        "uploadDir" => $uploadStatus,
        "archiveDirs" => $archiveStatus,
    ]);
    exit;
}

// Use web-relative paths for python output returned to frontend, but absolute paths for filesystem operations
$uploadDirWeb = rtrim($uploadDirWeb, '/').'/';
foreach ($archiveDirsWeb as &$dweb) {
    $dweb = rtrim($dweb, '/').'/';
}
unset($dweb);


/*
|--------------------------------------------------------------------------
| FILE PATHS
|--------------------------------------------------------------------------
*/

$filename =
    time() . "_" .
    basename($_FILES['image']['name']);

$inputPath =
    $uploadDir . $filename;

$extension = pathinfo($_FILES['image']['name'], PATHINFO_EXTENSION);

$filename =
    time() . "_" .
    uniqid() . "." .
    $extension;

$inputPath =
    $uploadDir . $filename;

$outputFileName =
    "processed_" .
    pathinfo($filename, PATHINFO_FILENAME) .
    ".jpg";

$outputPath = $uploadDir . $outputFileName;

// web URL path returned to frontend
$webOutputPath = $uploadDirWeb . $outputFileName;

/*
|--------------------------------------------------------------------------
| MOVE UPLOADED FILE
|--------------------------------------------------------------------------
*/

if (
    !move_uploaded_file(
        $_FILES['image']['tmp_name'],
        $inputPath
    )
) {
    $fileErr = $_FILES['image']['error'] ?? null;
    $fileSize = $_FILES['image']['size'] ?? null;
    $fileName = $_FILES['image']['name'] ?? null;
    $tmpName = $_FILES['image']['tmp_name'] ?? null;

    echo json_encode([
        "success" => false,
        "message" => "Failed to upload image",
        "uploadError" => $fileErr,
        "uploadSize" => $fileSize,
        "uploadName" => $fileName,
        "uploadTmp" => $tmpName
    ]);

    exit;
}



/*
|--------------------------------------------------------------------------
| RUN SUPPORTED PROCEDURE SCRIPT
|--------------------------------------------------------------------------
*/

$procedureScripts = [
    "co2-fractional-laser-dermapen" => [
        "script" => "python/process_co2_dermapen.py",
        "message" => "CO2 Fractional Laser + Dermapen processing failed",
        "intensity" => 2.25
    ],
    "face_slimming" => [
        "script" => "python/process_face_slimming.py",
        "message" => "Face slimming processing failed",
        "intensity" => 2.35
    ],
    "diamond-peel-facial" => [
        "script" => "python/process_diamond_peel.py",
        "message" => "Diamond Peel processing failed",
        "intensity" => 2.25
    ],
    "undereye-lip-filler" => [
        "script" => "python/process_undereye_lip_filler.py",
        "message" => "Undereye and Lip Filler processing failed",
        "intensity" => 2.35
    ],
    "pico-carbon-laser" => [
        "script" => "python/process_pico_carbon_laser.py",
        "message" => "PICO Carbon Laser processing failed",
        "intensity" => 2.25
    ],
    "lip-chin-jawtox" => [
        "script" => "python/process_lip_chin_jawtox.py",
        "message" => "Lip, Chin, and Jawtox processing failed",
        "intensity" => 3.00
    ],
    "general-skin-assessment" => [
        "script" => "python/process_general_skin_assessment.py",
        "message" => "General Skin Assessment processing failed",
        "intensity" => 1.0
    ]
];

if (isset($procedureScripts[$procedure])) {
    run_procedure_script(
        $procedure,
        $procedureScripts[$procedure]["script"],
        $procedureScripts[$procedure]["message"],
        $inputPath,
        $outputPath,
        $webOutputPath,
        $requestStart,
        (float)($procedureScripts[$procedure]["intensity"] ?? 1.0)
    );
}

/*
|--------------------------------------------------------------------------
| INVALID PROCEDURE
|--------------------------------------------------------------------------
*/

echo json_encode([
    "success" => false,
    "message" => "Procedure not supported"
]);

?>
