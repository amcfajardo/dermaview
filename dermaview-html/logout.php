<?php

session_start();
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth_common.php';

try {
    require_once __DIR__ . '/audit_common.php';
    presence_set_offline($conn);
} catch (Throwable $e) {}

auth_clear_active_session_if_current();

session_destroy();

header("Location: index.html");

exit;

?>