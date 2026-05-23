<?php

$host = "localhost";
$user = "root";
$password = "admin123";
$database = "dermaview";

$conn = new mysqli($host, $user, $password, $database);

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

?>