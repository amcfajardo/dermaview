<?php
// Super Admin module: full-system control copy.
require_once '../auth_common.php';
include '../config.php';

header('Content-Type: application/json; charset=utf-8');

auth_require_super_admin(true);

function table_exists($conn, $table_name) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = ?
    ");
    $stmt->bind_param("s", $table_name);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result ? $result->fetch_assoc() : null;

    return $row && (int) $row['total'] > 0;
}

function ensure_patient_notes_table($conn) {
    $conn->query("
        CREATE TABLE IF NOT EXISTS patient_notes (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            patient_key VARCHAR(190) NOT NULL UNIQUE,
            notes TEXT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");
}

function ensure_appointments_table($conn) {
    $conn->query("
        CREATE TABLE IF NOT EXISTS appointments (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            procedure_id VARCHAR(120) NOT NULL,
            procedure_name VARCHAR(180) NOT NULL,
            patient_name VARCHAR(160) NOT NULL,
            email VARCHAR(180) NULL,
            phone VARCHAR(60) NOT NULL,
            appointment_date DATE NOT NULL,
            appointment_time TIME NOT NULL,
            notes TEXT NULL,
            status ENUM('Pending','Confirmed','Completed','Cancelled','No Show') NOT NULL DEFAULT 'Pending',
            assigned_staff VARCHAR(160) NULL,
            source ENUM('online','staff') NOT NULL DEFAULT 'online',
            recorded_by INT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_appointments_date (appointment_date),
            INDEX idx_appointments_status (status),
            INDEX idx_appointments_procedure (procedure_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");
}

function ensure_table_column($conn, $table_name, $column_name, $alter_sql) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS total
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = ?
          AND column_name = ?
    ");

    if (!$stmt) {
        return;
    }

    $stmt->bind_param("ss", $table_name, $column_name);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result ? $result->fetch_assoc() : null;

    if (!$row || (int) $row['total'] === 0) {
        $conn->query($alter_sql);
    }
}

function patient_key($name, $email, $phone) {
    $base = strtolower(trim($email ?: $phone ?: $name));
    return preg_replace('/[^a-z0-9@._+-]+/', '-', $base);
}

function upsert_patient(&$patients, $name, $email, $phone) {
    $name = trim((string) $name);
    if ($name === '') {
        $name = 'Unknown Patient';
    }

    $key = patient_key($name, $email, $phone);
    if (!isset($patients[$key])) {
        $patients[$key] = [
            'patient_key' => $key,
            'patient_name' => $name,
            'email' => $email,
            'phone' => $phone,
            'consultations' => [],
            'uploaded_images' => [],
            'treatment_history' => [],
            'notes' => '',
            'last_activity' => ''
        ];
    }

    if (!$patients[$key]['email'] && $email) $patients[$key]['email'] = $email;
    if (!$patients[$key]['phone'] && $phone) $patients[$key]['phone'] = $phone;

    return $key;
}

ensure_patient_notes_table($conn);
ensure_appointments_table($conn);
ensure_table_column($conn, 'appointments', 'archived_at', "ALTER TABLE appointments ADD COLUMN archived_at TIMESTAMP NULL AFTER updated_at");
ensure_table_column($conn, 'patient_notes', 'archived_at', "ALTER TABLE patient_notes ADD COLUMN archived_at TIMESTAMP NULL AFTER updated_at");

$action = $_POST['action'] ?? 'fetch';

if ($action === 'save_note') {
    $patient_key = trim($_POST['patient_key'] ?? '');
    $notes = trim($_POST['notes'] ?? '');

    if ($patient_key === '') {
        echo json_encode(['status' => 'error', 'message' => 'Missing patient record.']);
        exit();
    }

    $stmt = $conn->prepare("
        INSERT INTO patient_notes (patient_key, notes)
        VALUES (?, ?)
        ON DUPLICATE KEY UPDATE notes = VALUES(notes)
    ");
    $stmt->bind_param("ss", $patient_key, $notes);
    $stmt->execute();

    echo json_encode(['status' => 'ok']);
    exit();
}

$patients = [];

if (table_exists($conn, 'appointments')) {
    $result = $conn->query("
        SELECT patient_name, email, phone, procedure_name, appointment_date, appointment_time, status, notes
        FROM appointments
        WHERE archived_at IS NULL
        ORDER BY appointment_date DESC, appointment_time DESC, id DESC
    ");

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $key = upsert_patient($patients, $row['patient_name'], $row['email'], $row['phone']);
            $timestamp = trim($row['appointment_date'] . ' ' . $row['appointment_time']);
            $patients[$key]['consultations'][] = [
                'date' => $timestamp,
                'procedure' => $row['procedure_name'],
                'status' => $row['status'],
                'notes' => $row['notes']
            ];
            $patients[$key]['treatment_history'][] = $row['procedure_name'];
            if (!$patients[$key]['last_activity'] || strtotime($timestamp) > strtotime($patients[$key]['last_activity'])) {
                $patients[$key]['last_activity'] = $timestamp;
            }
        }
    }
}

if (table_exists($conn, 'processed_images')) {
    ensure_table_column($conn, 'processed_images', 'archived_at', "ALTER TABLE processed_images ADD COLUMN archived_at TIMESTAMP NULL AFTER created_at");

    $result = $conn->query("
        SELECT procedure_name, before_image_path, after_image_path, analysis_type, created_at
        FROM processed_images
        WHERE archived_at IS NULL
        ORDER BY created_at DESC, id DESC
    ");

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $key = upsert_patient($patients, 'Unknown Patient', '', '');
            $patients[$key]['uploaded_images'][] = [
                'before' => $row['before_image_path'],
                'after' => $row['after_image_path'],
                'procedure' => $row['procedure_name'],
                'date' => $row['created_at'],
                'analysis' => $row['analysis_type']
            ];
            $patients[$key]['treatment_history'][] = $row['procedure_name'];
            if (!$patients[$key]['last_activity'] || strtotime($row['created_at']) > strtotime($patients[$key]['last_activity'])) {
                $patients[$key]['last_activity'] = $row['created_at'];
            }
        }
    }
}

$notes_result = $conn->query("SELECT patient_key, notes FROM patient_notes WHERE archived_at IS NULL");
if ($notes_result) {
    while ($row = $notes_result->fetch_assoc()) {
        if (isset($patients[$row['patient_key']])) {
            $patients[$row['patient_key']]['notes'] = $row['notes'];
        }
    }
}

foreach ($patients as &$patient) {
    $patient['treatment_history'] = array_values(array_unique(array_filter($patient['treatment_history'])));
}

usort($patients, function ($a, $b) {
    return strtotime($b['last_activity'] ?: '1970-01-01') <=> strtotime($a['last_activity'] ?: '1970-01-01');
});

echo json_encode(['status' => 'ok', 'patients' => array_values($patients)]);

?>
