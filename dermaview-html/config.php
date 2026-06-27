<?php

$host = "localhost";
$username = "dermaviewuser";
$password = "admin123";
$database = "dermaview";

mysqli_report(MYSQLI_REPORT_OFF);

$conn = @mysqli_connect($host, $username, $password, $database);

if (!$conn) {
    http_response_code(503);
    die("Database connection failed. Please make sure MySQL is running and the database is available.");
}

?>
