<?php

session_start();

try {
    require_once __DIR__ . '/audit_common.php';
    presence_set_offline($conn);
} catch (Throwable $e) {}

session_destroy();

header("Location: login.html");

exit;

?>