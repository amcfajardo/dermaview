<?php

function password_policy_message() {
    return 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.';
}

function password_policy_is_valid($password) {
    if (strlen((string) $password) < 8) {
        return false;
    }

    return preg_match('/[A-Z]/', $password) &&
        preg_match('/[a-z]/', $password) &&
        preg_match('/[0-9]/', $password) &&
        preg_match('/[^A-Za-z0-9]/', $password);
}

function password_policy_require($password) {
    if (!password_policy_is_valid($password)) {
        echo password_policy_message();
        exit;
    }
}

?>
