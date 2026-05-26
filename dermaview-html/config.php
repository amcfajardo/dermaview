<?php

$host = "localhost";
$user = "dermaviewuser";
$password = "admin123";
$database = "dermaview";

mysqli_report(MYSQLI_REPORT_OFF);
$conn = @new mysqli($host, $user, $password, $database);

if ($conn->connect_error) {
    http_response_code(503);

    $message = "The clinic database is currently unavailable. Please try again in a moment.";
    $accept = $_SERVER['HTTP_ACCEPT'] ?? '';
    $action = $_POST['action'] ?? '';

    if (stripos($accept, 'application/json') !== false || str_ends_with((string) $action, '_json')) {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode([
            'status' => 'error',
            'message' => $message
        ]);
    } else {
        header('Content-Type: text/plain; charset=utf-8');
        echo $message;
    }

    exit();
}

?>
