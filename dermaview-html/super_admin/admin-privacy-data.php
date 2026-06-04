<?php
require_once '../auth_common.php';
session_start();
include '../config.php';
require_once '../audit_common.php';

auth_require_super_admin(true);
audit_ensure_tables($conn);

header('Content-Type: application/json; charset=utf-8');

function privacy_json($payload, $status_code = 200) {
    http_response_code($status_code);
    echo json_encode($payload);
    exit();
}

function privacy_table_exists($conn, $table_name) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = ?
    ");
    $stmt->bind_param("s", $table_name);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();
    return $row && (int)$row['total'] > 0;
}

function privacy_column_exists($conn, $table_name, $column_name) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS total
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = ?
          AND column_name = ?
    ");
    $stmt->bind_param("ss", $table_name, $column_name);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();
    return $row && (int)$row['total'] > 0;
}

function privacy_ensure_column($conn, $table_name, $column_name, $alter_sql) {
    if (privacy_table_exists($conn, $table_name) && !privacy_column_exists($conn, $table_name, $column_name)) {
        $conn->query($alter_sql);
    }
}

function privacy_ensure_tables($conn) {
    $conn->query("
        CREATE TABLE IF NOT EXISTS privacy_archive_logs (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            action VARCHAR(80) NOT NULL,
            status VARCHAR(160) NOT NULL,
            archived_count INT UNSIGNED NOT NULL DEFAULT 0,
            details_json LONGTEXT NULL,
            created_by INT NULL,
            created_by_name VARCHAR(160) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_privacy_archive_created (created_at),
            INDEX idx_privacy_archive_action (action)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");

    $conn->query("
        CREATE TABLE IF NOT EXISTS patient_archive_records (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            patient_key VARCHAR(190) NOT NULL,
            patient_name VARCHAR(160) NOT NULL,
            email VARCHAR(180) NULL,
            phone VARCHAR(60) NULL,
            last_activity DATETIME NULL,
            archive_snapshot LONGTEXT NULL,
            archived_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_patient_archive_key (patient_key),
            INDEX idx_patient_archive_date (archived_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");

    privacy_ensure_column($conn, 'processed_images', 'archived_at', "ALTER TABLE processed_images ADD COLUMN archived_at TIMESTAMP NULL AFTER created_at");
    privacy_ensure_column($conn, 'consultation_image_records', 'archived_at', "ALTER TABLE consultation_image_records ADD COLUMN archived_at TIMESTAMP NULL AFTER date_processed");
    privacy_ensure_column($conn, 'appointments', 'archived_at', "ALTER TABLE appointments ADD COLUMN archived_at TIMESTAMP NULL AFTER updated_at");
    privacy_ensure_column($conn, 'patient_notes', 'archived_at', "ALTER TABLE patient_notes ADD COLUMN archived_at TIMESTAMP NULL AFTER updated_at");
}

function privacy_read_system_settings($conn) {
    $conn->query("
        CREATE TABLE IF NOT EXISTS system_settings (
            id TINYINT UNSIGNED NOT NULL PRIMARY KEY DEFAULT 1,
            settings_json LONGTEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");

    $result = $conn->query("SELECT settings_json FROM system_settings WHERE id = 1");
    if (!$result || $result->num_rows === 0) {
        return ['imageRetentionPeriod' => '180 days'];
    }

    $row = $result->fetch_assoc();
    $settings = json_decode($row['settings_json'] ?? '', true);
    return is_array($settings) ? $settings : ['imageRetentionPeriod' => '180 days'];
}

function privacy_actor_name() {
    $name = trim((string)($_SESSION['user_name'] ?? ''));
    return $name !== '' ? $name : 'Super Admin';
}

function privacy_insert_log($conn, $action, $status, $count, $details = []) {
    $created_by = isset($_SESSION['user_id']) ? (int)$_SESSION['user_id'] : null;
    $created_by_value = $created_by === null ? 0 : $created_by;
    $created_by_name = privacy_actor_name();
    $details_json = json_encode($details, JSON_UNESCAPED_SLASHES);

    $stmt = $conn->prepare("
        INSERT INTO privacy_archive_logs
        (action, status, archived_count, details_json, created_by, created_by_name)
        VALUES (?, ?, ?, ?, ?, ?)
    ");
    $stmt->bind_param("ssisis", $action, $status, $count, $details_json, $created_by_value, $created_by_name);
    $stmt->execute();

    if ($created_by === null) {
        $conn->query("UPDATE privacy_archive_logs SET created_by = NULL WHERE id = LAST_INSERT_ID()");
    }
}

function privacy_rows($conn) {
    privacy_ensure_tables($conn);

    $result = $conn->query("
        SELECT action, status, archived_count, created_at
        FROM privacy_archive_logs
        ORDER BY created_at DESC, id DESC
        LIMIT 50
    ");

    $rows = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $rows[] = [
                'action' => $row['action'],
                'status' => $row['status'],
                'archived_count' => (int)$row['archived_count'],
                'date' => $row['created_at']
            ];
        }
    }

    return $rows;
}

function privacy_retention_days($conn) {
    $settings = privacy_read_system_settings($conn);
    $value = (string)($settings['imageRetentionPeriod'] ?? '180 days');
    if (preg_match('/(\d+)/', $value, $matches)) {
        return max(1, (int)$matches[1]);
    }
    return 180;
}

function privacy_archive_path($web_path, $category) {
    $web_path = trim((string)$web_path);
    if ($web_path === '' || preg_match('/^(https?:|data:)/i', $web_path)) {
        return null;
    }

    $root = realpath(__DIR__ . '/..');
    $source = realpath($root . DIRECTORY_SEPARATOR . str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $web_path));
    if (!$source || !is_file($source) || strpos($source, $root) !== 0) {
        return null;
    }

    $archive_web_dir = 'archive/' . trim($category, '/') . '/' . date('Ymd');
    $archive_dir = $root . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $archive_web_dir);
    if (!is_dir($archive_dir)) {
        mkdir($archive_dir, 0775, true);
    }

    $name = basename($source);
    $target = $archive_dir . DIRECTORY_SEPARATOR . $name;
    if (is_file($target)) {
        $target = $archive_dir . DIRECTORY_SEPARATOR . pathinfo($name, PATHINFO_FILENAME) . '-' . bin2hex(random_bytes(3)) . '.' . pathinfo($name, PATHINFO_EXTENSION);
    }

    if (!rename($source, $target)) {
        return null;
    }

    return $archive_web_dir . '/' . basename($target);
}

function privacy_archive_disk_files($conn, $kind, $days) {
    $root = realpath(__DIR__ . '/..');
    if (!$root) return [0, []];

    $cutoff = time() - ($days * 86400);
    $patterns = $kind === 'uploaded'
        ? [
            ['dir' => 'uploads', 'prefix' => null, 'exclude_prefix' => 'processed_']
        ]
        : [
            ['dir' => 'processed_uploads', 'prefix' => null, 'exclude_prefix' => null],
            ['dir' => 'uploads', 'prefix' => 'processed_', 'exclude_prefix' => null]
        ];

    $count = 0;
    $moved = [];

    foreach ($patterns as $pattern) {
        $dir = $root . DIRECTORY_SEPARATOR . $pattern['dir'];
        if (!is_dir($dir)) continue;

        $items = glob($dir . DIRECTORY_SEPARATOR . '*');
        if (!$items) continue;

        foreach ($items as $path) {
            if (!is_file($path) || filemtime($path) >= $cutoff) continue;

            $name = basename($path);
            if ($pattern['prefix'] !== null && strpos($name, $pattern['prefix']) !== 0) continue;
            if ($pattern['exclude_prefix'] !== null && strpos($name, $pattern['exclude_prefix']) === 0) continue;

            $web_path = $pattern['dir'] . '/' . $name;
            $new_path = privacy_archive_path($web_path, $kind === 'uploaded' ? 'images/uploaded' : 'images/processed');
            if (!$new_path) continue;

            $count++;
            $moved[] = $new_path;
        }
    }

    return [$count, $moved];
}

function privacy_archive_images($conn, $kind, $days) {
    $cutoff = date('Y-m-d H:i:s', time() - ($days * 86400));
    $count = 0;
    $moved = [];

    if (privacy_table_exists($conn, 'processed_images')) {
        $column = $kind === 'uploaded' ? 'before_image_path' : 'after_image_path';
        $result = $conn->query("
            SELECT id, {$column} AS image_path
            FROM processed_images
            WHERE archived_at IS NULL
              AND created_at < '" . $conn->real_escape_string($cutoff) . "'
              AND {$column} IS NOT NULL
              AND {$column} <> ''
        ");

        if ($result) {
            while ($row = $result->fetch_assoc()) {
                $new_path = privacy_archive_path($row['image_path'], $kind === 'uploaded' ? 'images/uploaded' : 'images/processed');
                if (!$new_path) continue;

                $stmt = $conn->prepare("UPDATE processed_images SET {$column} = ? WHERE id = ?");
                $id = (int)$row['id'];
                $stmt->bind_param("si", $new_path, $id);
                $stmt->execute();
                $count++;
                $moved[] = $new_path;
            }
        }
    }

    if (privacy_table_exists($conn, 'consultation_image_records')) {
        $column = $kind === 'uploaded' ? 'original_image_path' : 'processed_image_path';
        $result = $conn->query("
            SELECT id, {$column} AS image_path
            FROM consultation_image_records
            WHERE archived_at IS NULL
              AND date_processed < '" . $conn->real_escape_string($cutoff) . "'
              AND {$column} IS NOT NULL
              AND {$column} <> ''
        ");

        if ($result) {
            while ($row = $result->fetch_assoc()) {
                $new_path = privacy_archive_path($row['image_path'], $kind === 'uploaded' ? 'images/uploaded' : 'images/processed');
                if (!$new_path) continue;

                $stmt = $conn->prepare("UPDATE consultation_image_records SET {$column} = ? WHERE id = ?");
                $id = (int)$row['id'];
                $stmt->bind_param("si", $new_path, $id);
                $stmt->execute();
                $count++;
                $moved[] = $new_path;
            }
        }
    }

    [$disk_count, $disk_moved] = privacy_archive_disk_files($conn, $kind, $days);
    $count += $disk_count;
    $moved = array_merge($moved, $disk_moved);

    $label = $kind === 'uploaded' ? 'Archive old uploaded images' : 'Archive old processed images';
    $status = $count > 0 ? "Archived {$count} file(s) to archive/images/" . ($kind === 'uploaded' ? 'uploaded' : 'processed') : "No files older than {$days} day(s) found";
    privacy_insert_log($conn, $label, $status, $count, ['retention_days' => $days, 'paths' => array_slice($moved, 0, 30)]);
    audit_log($conn, 'Privacy Archive', $label, $status, 'privacy_archive', null, ['count' => $count, 'retention_days' => $days]);

    return $status;
}

function privacy_patient_key($name, $email, $phone) {
    $base = strtolower(trim($email ?: $phone ?: $name));
    return preg_replace('/[^a-z0-9@._+-]+/', '-', $base);
}

function privacy_html_escape($value) {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

function privacy_write_patient_archive_report($archive_dir, $archive_file, $patients, $days) {
    $rows = '';

    foreach ($patients as $patient) {
        $appointments = '';
        foreach ($patient['appointments'] as $appointment) {
            $appointments .= '<tr>'
                . '<td>' . privacy_html_escape(trim(($appointment['appointment_date'] ?? '') . ' ' . ($appointment['appointment_time'] ?? ''))) . '</td>'
                . '<td>' . privacy_html_escape($appointment['procedure_name'] ?? '') . '</td>'
                . '<td>' . privacy_html_escape($appointment['status'] ?? '') . '</td>'
                . '<td>' . privacy_html_escape($appointment['notes'] ?? '') . '</td>'
                . '</tr>';
        }

        if ($appointments === '') {
            $appointments = '<tr><td colspan="4">No appointment rows recorded.</td></tr>';
        }

        $rows .= '<section class="patient">'
            . '<h2>' . privacy_html_escape($patient['patient_name']) . '</h2>'
            . '<dl>'
            . '<div><dt>Patient Key</dt><dd>' . privacy_html_escape($patient['patient_key']) . '</dd></div>'
            . '<div><dt>Email</dt><dd>' . privacy_html_escape($patient['email']) . '</dd></div>'
            . '<div><dt>Phone</dt><dd>' . privacy_html_escape($patient['phone']) . '</dd></div>'
            . '<div><dt>Last Activity</dt><dd>' . privacy_html_escape($patient['last_activity']) . '</dd></div>'
            . '</dl>'
            . '<table><thead><tr><th>Date / Time</th><th>Procedure</th><th>Status</th><th>Notes</th></tr></thead><tbody>'
            . $appointments
            . '</tbody></table>'
            . '</section>';
    }

    $html = '<!doctype html><html><head><meta charset="utf-8">'
        . '<title>Patient Records Archive</title>'
        . '<style>'
        . 'body{font-family:Arial,sans-serif;color:#111827;line-height:1.5;padding:32px;}'
        . 'h1{margin:0 0 8px;font-size:28px;}'
        . '.meta{color:#4b5563;margin:0 0 24px;}'
        . '.patient{page-break-inside:avoid;border-top:1px solid #d1d5db;padding-top:18px;margin-top:22px;}'
        . 'h2{font-size:20px;margin:0 0 10px;}'
        . 'dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 20px;margin:0 0 14px;}'
        . 'dt{font-weight:700;color:#374151;}dd{margin:2px 0 0;}'
        . 'table{width:100%;border-collapse:collapse;margin-top:10px;}'
        . 'th,td{border:1px solid #d1d5db;padding:8px;text-align:left;vertical-align:top;font-size:13px;}'
        . 'th{background:#f3f4f6;}'
        . '</style></head><body>'
        . '<h1>Patient Records Archive</h1>'
        . '<p class="meta">Archived on ' . privacy_html_escape(date('Y-m-d H:i:s')) . ' | Retention: ' . privacy_html_escape($days) . ' day(s) | Records: ' . count($patients) . '</p>'
        . $rows
        . '</body></html>';

    return file_put_contents($archive_dir . DIRECTORY_SEPARATOR . $archive_file, $html) !== false;
}

function privacy_archive_patients($conn, $days) {
    if (!privacy_table_exists($conn, 'appointments')) {
        privacy_insert_log($conn, 'Archive inactive patient records', 'No appointment records found', 0, ['retention_days' => $days]);
        return 'No appointment records found';
    }

    $cutoff = date('Y-m-d H:i:s', time() - ($days * 86400));
    $root = realpath(__DIR__ . '/..');
    $archive_web_dir = 'archive/files/patient-records/' . date('Ymd');
    $archive_dir = $root . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $archive_web_dir);
    if (!is_dir($archive_dir)) {
        mkdir($archive_dir, 0775, true);
    }

    $archive_file = 'patient-records-archive-' . date('Ymd-His') . '-' . bin2hex(random_bytes(3)) . '.html';
    $batch_patients = [];

    $result = $conn->query("
        SELECT patient_name, email, phone, MAX(CONCAT(appointment_date, ' ', appointment_time)) AS last_activity
        FROM appointments
        WHERE archived_at IS NULL
        GROUP BY patient_name, email, phone
        HAVING last_activity < '" . $conn->real_escape_string($cutoff) . "'
    ");

    $count = 0;
    if ($result) {
        while ($patient = $result->fetch_assoc()) {
            $key = privacy_patient_key($patient['patient_name'], $patient['email'], $patient['phone']);
            $snapshot_stmt = $conn->prepare("
                SELECT id, procedure_name, appointment_date, appointment_time, status, notes
                FROM appointments
                WHERE archived_at IS NULL
                  AND patient_name = ?
                  AND COALESCE(email, '') = COALESCE(?, '')
                  AND COALESCE(phone, '') = COALESCE(?, '')
                ORDER BY appointment_date DESC, appointment_time DESC
            ");
            $snapshot_stmt->bind_param("sss", $patient['patient_name'], $patient['email'], $patient['phone']);
            $snapshot_stmt->execute();
            $snapshot_rows = [];
            $snapshot_result = $snapshot_stmt->get_result();
            while ($row = $snapshot_result->fetch_assoc()) {
                $snapshot_rows[] = $row;
            }

            $snapshot_json = json_encode(['appointments' => $snapshot_rows], JSON_UNESCAPED_SLASHES);
            $batch_patients[] = [
                'patient_key' => $key,
                'patient_name' => $patient['patient_name'],
                'email' => $patient['email'],
                'phone' => $patient['phone'],
                'last_activity' => $patient['last_activity'],
                'appointments' => $snapshot_rows
            ];

            $archive_stmt = $conn->prepare("
                INSERT INTO patient_archive_records
                (patient_key, patient_name, email, phone, last_activity, archive_snapshot)
                VALUES (?, ?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE
                    patient_name = VALUES(patient_name),
                    email = VALUES(email),
                    phone = VALUES(phone),
                    last_activity = VALUES(last_activity),
                    archive_snapshot = VALUES(archive_snapshot),
                    archived_at = NOW()
            ");
            $archive_stmt->bind_param("ssssss", $key, $patient['patient_name'], $patient['email'], $patient['phone'], $patient['last_activity'], $snapshot_json);
            $archive_stmt->execute();

            $update_stmt = $conn->prepare("
                UPDATE appointments
                SET archived_at = NOW()
                WHERE archived_at IS NULL
                  AND patient_name = ?
                  AND COALESCE(email, '') = COALESCE(?, '')
                  AND COALESCE(phone, '') = COALESCE(?, '')
            ");
            $update_stmt->bind_param("sss", $patient['patient_name'], $patient['email'], $patient['phone']);
            $update_stmt->execute();

            if (privacy_table_exists($conn, 'patient_notes')) {
                $notes_stmt = $conn->prepare("UPDATE patient_notes SET archived_at = NOW() WHERE patient_key = ?");
                $notes_stmt->bind_param("s", $key);
                $notes_stmt->execute();
            }

            $count++;
        }
    }

    $archive_web_path = $archive_web_dir . '/' . $archive_file;
    if ($count > 0) {
        privacy_write_patient_archive_report($archive_dir, $archive_file, $batch_patients, $days);
    }

    $status = $count > 0 ? "Archived {$count} inactive patient record(s) to {$archive_web_path}" : "No inactive patient records older than {$days} day(s) found";
    privacy_insert_log($conn, 'Archive inactive patient records', $status, $count, ['retention_days' => $days, 'archive_file' => $count > 0 ? $archive_web_path : null]);
    audit_log($conn, 'Privacy Archive', 'Inactive patient records archived', $status, 'privacy_archive', null, ['count' => $count, 'retention_days' => $days]);
    return $status;
}

privacy_ensure_tables($conn);
$action = $_POST['action'] ?? $_GET['action'] ?? 'list';

if ($action === 'list') {
    privacy_json(['status' => 'ok', 'records' => privacy_rows($conn)]);
}

$days = privacy_retention_days($conn);

if ($action === 'archive_uploaded_images') {
    privacy_json(['status' => 'ok', 'message' => privacy_archive_images($conn, 'uploaded', $days), 'records' => privacy_rows($conn)]);
}

if ($action === 'archive_processed_images') {
    privacy_json(['status' => 'ok', 'message' => privacy_archive_images($conn, 'processed', $days), 'records' => privacy_rows($conn)]);
}

if ($action === 'archive_inactive_patients') {
    privacy_json(['status' => 'ok', 'message' => privacy_archive_patients($conn, $days), 'records' => privacy_rows($conn)]);
}

privacy_json(['status' => 'error', 'message' => 'Unknown privacy action.'], 400);
?>
