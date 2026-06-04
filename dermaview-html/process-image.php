<?php

header('Content-Type: application/json');

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
| CO2 FRACTIONAL LASER + DERMAPEN
|--------------------------------------------------------------------------
*/

if (
    $procedure ===
    "co2-fractional-laser-dermapen"
) {

    $pythonScript =
        "python/process_co2_dermapen.py";

    /*
    |--------------------------------------------------------------------------
    | PYTHON COMMAND
    |--------------------------------------------------------------------------
    */

    $command =
    "python \"$pythonScript\" " .
    escapeshellarg($inputPath) . " " .
    escapeshellarg($outputPath) . " 2>&1";

    exec(
        $command,
        $output,
        $status
    );

    /*
    |--------------------------------------------------------------------------
    | SUCCESS
    |--------------------------------------------------------------------------
    */

    if (
        $status === 0 &&
        file_exists($outputPath)
    ) {

        echo json_encode([
            "success" => true,
"image" => $webOutputPath
        ]);

    } else {

        echo json_encode([
            "success" => false,
            "message" => "Python image processing failed",
            "debug" => $output,
"command" => $command,
"outputPath" => $outputPath
        ]);

    }

    exit;
}

/*
|--------------------------------------------------------------------------
| FACE SLIMMING
|--------------------------------------------------------------------------
*/

if (
    $procedure ===
    "face_slimming"
) {

    $pythonScript =
        "python/process_face_slimming.py";

    /*
    |--------------------------------------------------------------------------
    | PYTHON COMMAND
    |--------------------------------------------------------------------------
    */

    $command =
    "python \"$pythonScript\" " .
    escapeshellarg($inputPath) . " " .
    escapeshellarg($outputPath) . " 2>&1";

    exec(
        $command,
        $output,
        $status
    );

    /*
    |--------------------------------------------------------------------------
    | SUCCESS
    |--------------------------------------------------------------------------
    */

    if (
        $status === 0 &&
        file_exists($outputPath)
    ) {

        echo json_encode([
            "success" => true,
"image" => $webOutputPath
        ]);


    } else {

        echo json_encode([
            "success" => false,
            "message" => "Face slimming processing failed",
            "debug" => $output,
            "command" => $command,
            "outputPath" => $outputPath
        ]);

    }

    exit;
}

/*
|--------------------------------------------------------------------------
| DIAMOND PEEL WITH FACIAL
|--------------------------------------------------------------------------
*/

if (
    $procedure ===
    "diamond-peel-facial"
) {

    $pythonScript =
        "python/process_diamond_peel.py";

    $command =
    "python \"$pythonScript\" " .
    escapeshellarg($inputPath) . " " .
    escapeshellarg($outputPath) . " 2>&1";

    exec(
        $command,
        $output,
        $status
    );

    if (
        $status === 0 &&
        file_exists($outputPath)
    ) {

        echo json_encode([
        "success" => true,
        "image" => $webOutputPath
    ]);

    } else {

        echo json_encode([
            "success" => false,
            "message" => "Diamond Peel processing failed",
            "debug" => $output
        ]);

    }

    exit;
}

/*
|--------------------------------------------------------------------------
| UNDEREYE AND LIP FILLER
|--------------------------------------------------------------------------
*/

if (
    $procedure ===
    "undereye-lip-filler"
) {

    $pythonScript =
        "python/process_undereye_lip_filler.py";

    $command =
    "python \"$pythonScript\" " .
    escapeshellarg($inputPath) . " " .
    escapeshellarg($outputPath) . " 2>&1";

    exec(
        $command,
        $output,
        $status
    );

    if (
        $status === 0 &&
        file_exists($outputPath)
    ) {

        echo json_encode([
        "success" => true,
        "image" => $webOutputPath
    ]);

    } else {

        echo json_encode([
            "success" => false,
            "message" => "Undereye and Lip Filler processing failed",
            "debug" => $output
        ]);

    }

    exit;
}

/*
|--------------------------------------------------------------------------
| PICO CARBON LASER FACIAL
|--------------------------------------------------------------------------
*/

if (
    $procedure ===
    "pico-carbon-laser"
) {

    $pythonScript =
        "python/process_pico_carbon_laser.py";

    $command =
    "python \"$pythonScript\" " .
    escapeshellarg($inputPath) . " " .
    escapeshellarg($outputPath) . " 2>&1";

    exec(
        $command,
        $output,
        $status
    );

    if (
        $status === 0 &&
        file_exists($outputPath)
    ) {

        echo json_encode([
        "success" => true,
        "image" => $webOutputPath
    ]);

    } else {

        echo json_encode([
            "success" => false,
            "message" => "PICO Carbon Laser processing failed",
            "debug" => $output,
            "command" => $command,
            "outputPath" => $outputPath
        ]);

    }

    exit;
}

/*
|--------------------------------------------------------------------------
| LIP FILLER, CHIN FILLER, AND JAWTOX
|--------------------------------------------------------------------------
*/

if (
    $procedure ===
    "lip-chin-jawtox"
) {

    $pythonScript =
        "python/process_lip_chin_jawtox.py";

    $command =
    "python \"$pythonScript\" " .
    escapeshellarg($inputPath) . " " .
    escapeshellarg($outputPath) . " 2>&1";

    exec(
        $command,
        $output,
        $status
    );

    if (
        $status === 0 &&
        file_exists($outputPath)
    ) {

        echo json_encode([
        "success" => true,
        "image" => $webOutputPath
    ]);

    } else {

        echo json_encode([
            "success" => false,
            "message" => "Lip, Chin, and Jawtox processing failed",
            "debug" => $output,
            "command" => $command,
            "outputPath" => $outputPath
        ]);

    }

    exit;
}


/*
|--------------------------------------------------------------------------
| GENERAL SKIN ASSESSMENT
|--------------------------------------------------------------------------
*/

if ($procedure === "general-skin-assessment") {

    $pythonScript = "python/process_general_skin_assessment.py";

    $command =
        "python \"$pythonScript\" " .
        escapeshellarg($inputPath) . " " .
        escapeshellarg($outputPath) . " 2>&1";

    exec($command, $output, $status);

    if ($status === 0 && file_exists($outputPath)) {
        echo json_encode([
        "success" => true,
        "image" => $webOutputPath
    ]);
    } else {
        echo json_encode([
            "success" => false,
            "message" => "General Skin Assessment processing failed",
            "debug" => $output,
            "command" => $command,
            "outputPath" => $outputPath
        ]);
    }

    exit;
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
