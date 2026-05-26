<?php

$host = "localhost";
$username = "dermaviewuser";
$password = "admin123";
$database = "dermaview";

$conn = mysqli_connect($host, $username, $password, $database);

if (!$conn) {
    die("Database connection failed: " . mysqli_connect_error());
}

?>
