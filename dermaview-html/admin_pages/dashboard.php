<?php

include '../config.php';

header('Content-Type: application/json; charset=utf-8');

$procedure_count = 7;
$image_tables = ['processed_images', 'uploaded_images', 'image_records', 'consultations'];

function table_exists($conn, $table_name) {
    $stmt = $conn->prepare("
        SELECT COUNT(*) AS table_count
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = ?
    ");
    $stmt->bind_param("s", $table_name);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result ? $result->fetch_assoc() : null;

    return $row && (int) $row['table_count'] > 0;
}

function count_rows($conn, $table_name, $where = '') {
    if (!table_exists($conn, $table_name)) {
        return 0;
    }

    $sql = "SELECT COUNT(*) AS total FROM `$table_name`";
    if ($where !== '') {
        $sql .= " WHERE $where";
    }

    $result = $conn->query($sql);
    $row = $result ? $result->fetch_assoc() : null;

    return $row ? (int) $row['total'] : 0;
}

function count_image_records($conn, $tables) {
    $total = 0;

    foreach ($tables as $table) {
        if (table_exists($conn, $table)) {
            $total += count_rows($conn, $table);
        }
    }

    return $total;
}

function fetch_recent_appointments($conn) {
    if (!table_exists($conn, 'appointments')) {
        return [];
    }

    $result = $conn->query("
        SELECT patient_name, procedure_name, status, created_at
        FROM appointments
        ORDER BY created_at DESC, id DESC
        LIMIT 5
    ");

    $items = [];

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $items[] = [
                'type' => 'Appointment',
                'title' => $row['patient_name'] . ' requested ' . $row['procedure_name'],
                'meta' => $row['status'],
                'created_at' => $row['created_at']
            ];
        }
    }

    return $items;
}

function fetch_recent_users($conn) {
    if (!table_exists($conn, 'users')) {
        return [];
    }

    $result = $conn->query("
        SELECT first_name, last_name, role, status, created_at
        FROM users
        ORDER BY created_at DESC, id DESC
        LIMIT 5
    ");

    $items = [];

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $name = trim($row['first_name'] . ' ' . $row['last_name']);

            $items[] = [
                'type' => 'Staff Account',
                'title' => $name . ' was added as ' . ucfirst($row['role']),
                'meta' => $row['status'],
                'created_at' => $row['created_at']
            ];
        }
    }

    return $items;
}

$total_staff = count_rows($conn, 'users');
$active_staff = count_rows($conn, 'users', "status = 'Active'");
$total_appointments = count_rows($conn, 'appointments');
$pending_appointments = count_rows($conn, 'appointments', "status = 'Pending'");
$confirmed_appointments = count_rows($conn, 'appointments', "status = 'Confirmed'");
$completed_appointments = count_rows($conn, 'appointments', "status = 'Completed'");
$processed_images = count_image_records($conn, $image_tables);

$recent_activity = array_merge(fetch_recent_appointments($conn), fetch_recent_users($conn));
usort($recent_activity, function ($a, $b) {
    return strtotime($b['created_at']) <=> strtotime($a['created_at']);
});
$recent_activity = array_slice($recent_activity, 0, 6);

echo json_encode([
    'status' => 'ok',
    'stats' => [
        'procedures' => $procedure_count,
        'images' => $processed_images,
        'staff' => $total_staff,
        'appointments' => $total_appointments,
        'pending_appointments' => $pending_appointments,
        'confirmed_appointments' => $confirmed_appointments,
        'completed_appointments' => $completed_appointments
    ],
    'recent_activity' => $recent_activity,
    'system_status' => [
        [
            'label' => 'Database',
            'value' => 'Connected',
            'state' => 'good'
        ],
        [
            'label' => 'Staff Accounts',
            'value' => $active_staff . ' active / ' . $total_staff . ' total',
            'state' => $total_staff > 0 ? 'good' : 'warning'
        ],
        [
            'label' => 'Appointments',
            'value' => $total_appointments . ' recorded',
            'state' => 'good'
        ],
        [
            'label' => 'Image Records',
            'value' => $processed_images > 0 ? $processed_images . ' stored' : 'No records yet',
            'state' => $processed_images > 0 ? 'good' : 'neutral'
        ]
    ]
]);

?>
