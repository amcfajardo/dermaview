<?php
require_once '../auth_common.php';
session_start();
include '../config.php';
require_once '../audit_common.php';

auth_require_super_admin(true);
audit_ensure_tables($conn);

$backup_dir = realpath(__DIR__ . '/..') . DIRECTORY_SEPARATOR . 'backups';
$restore_dir = $backup_dir . DIRECTORY_SEPARATOR . 'restore_requests';

function backup_json($payload, $status_code = 200) {
    http_response_code($status_code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($payload);
    exit();
}

function backup_ensure_dirs($backup_dir, $restore_dir) {
    if (!is_dir($backup_dir) && !mkdir($backup_dir, 0775, true)) {
        backup_json(['status' => 'error', 'message' => 'Unable to create backup folder.'], 500);
    }

    if (!is_dir($restore_dir) && !mkdir($restore_dir, 0775, true)) {
        backup_json(['status' => 'error', 'message' => 'Unable to create restore request folder.'], 500);
    }
}

function backup_ensure_table($conn) {
    $conn->query("CREATE TABLE IF NOT EXISTS backup_restore_records (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        record_type VARCHAR(40) NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        storage_path VARCHAR(500) NULL,
        status VARCHAR(120) NOT NULL,
        reason TEXT NULL,
        size_bytes BIGINT UNSIGNED NULL,
        created_by INT NULL,
        created_by_name VARCHAR(160) NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_record_created (record_type, created_at),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
}

function backup_actor_name() {
    $name = trim((string)($_SESSION['user_name'] ?? ''));
    if ($name !== '') return $name;
    return trim((string)($_SESSION['email'] ?? 'Super Admin'));
}

function backup_insert_record($conn, $type, $file_name, $storage_path, $status, $reason, $size_bytes) {
    $created_by = isset($_SESSION['user_id']) ? (int)$_SESSION['user_id'] : null;
    $created_by_value = $created_by === null ? 0 : $created_by;
    $created_by_name = backup_actor_name();

    $stmt = $conn->prepare("
        INSERT INTO backup_restore_records
        (record_type, file_name, storage_path, status, reason, size_bytes, created_by, created_by_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ");

    if (!$stmt) {
        backup_json(['status' => 'error', 'message' => 'Unable to prepare backup record.'], 500);
    }

    $stmt->bind_param(
        'sssssiss',
        $type,
        $file_name,
        $storage_path,
        $status,
        $reason,
        $size_bytes,
        $created_by_value,
        $created_by_name
    );
    $stmt->execute();

    if ($created_by === null) {
        $conn->query("UPDATE backup_restore_records SET created_by = NULL WHERE id = LAST_INSERT_ID()");
    }

    return $conn->insert_id;
}

function backup_rows($conn) {
    backup_ensure_table($conn);

    $result = $conn->query("
        SELECT id, record_type, file_name, status, reason, size_bytes, created_by_name, created_at
        FROM backup_restore_records
        ORDER BY created_at DESC, id DESC
        LIMIT 50
    ");

    $rows = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $rows[] = [
                'id' => (int)$row['id'],
                'type' => $row['record_type'] === 'restore_request' ? 'Restore Request' : 'Backup',
                'file_name' => $row['file_name'],
                'status' => $row['status'],
                'reason' => $row['reason'],
                'size_bytes' => $row['size_bytes'] === null ? null : (int)$row['size_bytes'],
                'created_by_name' => $row['created_by_name'],
                'date' => $row['created_at']
            ];
        }
    }

    return $rows;
}

function backup_sql_value($conn, $value) {
    if ($value === null) return 'NULL';
    return "'" . mysqli_real_escape_string($conn, (string)$value) . "'";
}

function backup_create_database_dump($conn, $database, $path) {
    $handle = fopen($path, 'wb');
    if (!$handle) {
        backup_json(['status' => 'error', 'message' => 'Unable to write backup file.'], 500);
    }

    fwrite($handle, "-- DermaView database backup\n");
    fwrite($handle, "-- Created at " . date('Y-m-d H:i:s') . "\n\n");
    fwrite($handle, "SET FOREIGN_KEY_CHECKS=0;\n\n");

    $tables_result = $conn->query('SHOW TABLES');
    if (!$tables_result) {
        fclose($handle);
        backup_json(['status' => 'error', 'message' => 'Unable to read database tables.'], 500);
    }

    while ($table_row = $tables_result->fetch_array()) {
        $table = $table_row[0];
        $quoted_table = '`' . str_replace('`', '``', $table) . '`';

        fwrite($handle, "DROP TABLE IF EXISTS {$quoted_table};\n");

        $create_result = $conn->query('SHOW CREATE TABLE ' . $quoted_table);
        $create_row = $create_result ? $create_result->fetch_assoc() : null;
        if ($create_row && isset($create_row['Create Table'])) {
            fwrite($handle, $create_row['Create Table'] . ";\n\n");
        }

        $data_result = $conn->query('SELECT * FROM ' . $quoted_table);
        if (!$data_result || $data_result->num_rows === 0) {
            continue;
        }

        while ($data_row = $data_result->fetch_assoc()) {
            $columns = array_map(function ($column) {
                return '`' . str_replace('`', '``', $column) . '`';
            }, array_keys($data_row));
            $values = array_map(function ($value) use ($conn) {
                return backup_sql_value($conn, $value);
            }, array_values($data_row));

            fwrite($handle, 'INSERT INTO ' . $quoted_table . ' (' . implode(', ', $columns) . ') VALUES (' . implode(', ', $values) . ");\n");
        }

        fwrite($handle, "\n");
    }

    fwrite($handle, "SET FOREIGN_KEY_CHECKS=1;\n");
    fclose($handle);
}

backup_ensure_dirs($backup_dir, $restore_dir);
backup_ensure_table($conn);

$action = $_POST['action'] ?? $_GET['action'] ?? 'list';

if ($action === 'list') {
    backup_json(['status' => 'ok', 'records' => backup_rows($conn)]);
}

if ($action === 'create_backup') {
    $timestamp = date('Ymd-His');
    $file_name = 'dermaview-backup-' . $timestamp . '.sql';
    $path = $backup_dir . DIRECTORY_SEPARATOR . $file_name;

    backup_create_database_dump($conn, $database, $path);

    $size = filesize($path);
    $id = backup_insert_record($conn, 'backup', $file_name, $path, 'Backup file saved on server', null, $size);
    audit_log($conn, 'Backup', 'Database backup created', 'Completed', 'backup', (string)$id, ['file' => $file_name]);

    backup_json(['status' => 'ok', 'message' => 'Database backup created.', 'records' => backup_rows($conn), 'download_id' => $id]);
}

if ($action === 'restore_request') {
    $reason = trim((string)($_POST['reason'] ?? ''));
    if ($reason === '') {
        backup_json(['status' => 'error', 'message' => 'Please enter a restore reason.'], 400);
    }

    if (!isset($_FILES['restore_file']) || !is_uploaded_file($_FILES['restore_file']['tmp_name'])) {
        backup_json(['status' => 'error', 'message' => 'Please choose a backup file.'], 400);
    }

    $original_name = basename((string)$_FILES['restore_file']['name']);
    $extension = strtolower(pathinfo($original_name, PATHINFO_EXTENSION));
    $allowed = ['sql', 'zip', 'gz', 'json'];

    if (!in_array($extension, $allowed, true)) {
        backup_json(['status' => 'error', 'message' => 'Backup file must be .sql, .zip, .gz, or .json.'], 400);
    }

    $safe_base = preg_replace('/[^A-Za-z0-9._-]+/', '-', pathinfo($original_name, PATHINFO_FILENAME));
    $safe_base = trim($safe_base, '-_') ?: 'restore-file';
    $file_name = 'restore-request-' . date('Ymd-His') . '-' . $safe_base . '.' . $extension;
    $path = $restore_dir . DIRECTORY_SEPARATOR . $file_name;

    if (!move_uploaded_file($_FILES['restore_file']['tmp_name'], $path)) {
        backup_json(['status' => 'error', 'message' => 'Unable to save restore request file.'], 500);
    }

    $size = filesize($path);
    $id = backup_insert_record($conn, 'restore_request', $original_name, $path, 'Request logged only - database not restored', $reason, $size);
    audit_log($conn, 'Restore Request', 'Restore request recorded', 'Logged only', 'restore_request', (string)$id, ['file' => $original_name, 'reason' => $reason]);

    backup_json(['status' => 'ok', 'message' => 'Restore request recorded for server verification.', 'records' => backup_rows($conn)]);
}

if ($action === 'download') {
    $id = (int)($_GET['id'] ?? 0);
    if ($id <= 0) {
        backup_json(['status' => 'error', 'message' => 'Backup file not found.'], 404);
    }

    $stmt = $conn->prepare("
        SELECT file_name, storage_path
        FROM backup_restore_records
        WHERE id = ? AND record_type = 'backup'
        LIMIT 1
    ");
    $stmt->bind_param('i', $id);
    $stmt->execute();
    $record = $stmt->get_result()->fetch_assoc();

    if (!$record || !is_file($record['storage_path'])) {
        backup_json(['status' => 'error', 'message' => 'Backup file not found on the server.'], 404);
    }

    header('Content-Type: application/sql');
    header('Content-Disposition: attachment; filename="' . basename($record['file_name']) . '"');
    header('Content-Length: ' . filesize($record['storage_path']));
    readfile($record['storage_path']);
    exit();
}

backup_json(['status' => 'error', 'message' => 'Unknown backup action.'], 400);
?>
