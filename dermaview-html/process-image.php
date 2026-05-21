<?php

header('Content-Type: application/json');

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

$uploadDir = "uploads/";

if (!file_exists($uploadDir)) {

    mkdir($uploadDir, 0777, true);

}

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

$outputPath =
    $uploadDir .
    "processed_" .
    pathinfo($filename, PATHINFO_FILENAME) .
    ".jpg";

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

    echo json_encode([
        "success" => false,
        "message" => "Failed to upload image"
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
        "process_co2_dermapen.py";

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
            "image" => $outputPath
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
        "process_face_slimming.py";

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
            "image" => $outputPath
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
| INVALID PROCEDURE
|--------------------------------------------------------------------------
*/

echo json_encode([
    "success" => false,
    "message" => "Procedure not supported"
]);

?>