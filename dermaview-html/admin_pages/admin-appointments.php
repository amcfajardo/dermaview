<?php

session_start();
include '../config.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

require '../src/Exception.php';
require '../src/PHPMailer.php';
require '../src/SMTP.php';

function sendAppointmentEmail($toEmail, $patientName, $subject, $messageBody) {
    if (empty($toEmail)) {
        return false;
    }

    $mail = new PHPMailer(true);

    try {
        $mail->isSMTP();
        $mail->Host = 'smtp.gmail.com';
        $mail->SMTPAuth = true;

        $mail->Username = 'dermaview2026@gmail.com';
        $mail->Password = 'grqa hghr alxb ltwq';

        $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;
        $mail->Port = 587;
        $mail->CharSet = 'UTF-8';

        $mail->setFrom('YOUR_GMAIL@gmail.com', 'DermaView');
        $mail->addAddress($toEmail, $patientName);

        $mail->isHTML(true);
        $mail->Subject = $subject;
        $mail->Body = $messageBody;

        $mail->send();
        return true;

    } catch (Exception $e) {
        return false;
    }
}

header('Content-Type: text/html; charset=utf-8');

$procedure_names = [
    'general-skin-assessment' => 'General Skin Assessment',
    'co2-fractional-laser-dermapen' => 'CO2 Fractional Laser + Dermapen',
    'face-slimming' => 'Face Slimming',
    'diamond-peel-facial' => 'Diamond Peel With Facial',
    'undereye-lip-filler' => 'Undereye and Lip Filler Procedure',
    'pico-carbon-laser' => 'PICO Carbon Laser Facial Procedure',
    'lip-chin-jawtox' => 'Lip Filler, Chin Filler, and Jawtox'
];

function clean_text($value) {
    return trim((string) $value);
}

function format_time_label($time) {
    if (!$time) {
        return '';
    }

    $timestamp = strtotime($time);
    return $timestamp ? date('g:i A', $timestamp) : $time;
}

function status_class($status) {
    $key = strtolower(str_replace(' ', '-', $status));
    return 'appointment-status-' . $key;
}

function ensure_appointment_columns($conn) {
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

    $result = $conn->query("
        SELECT COUNT(*) AS total
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'appointments'
          AND column_name = 'assigned_staff'
    ");
    $row = $result ? $result->fetch_assoc() : null;

    if (!$row || (int) $row['total'] === 0) {
        $conn->query("ALTER TABLE appointments ADD COLUMN assigned_staff VARCHAR(160) NULL AFTER status");
    }
}

ensure_appointment_columns($conn);

$action = $_POST['action'] ?? '';

if ($action === 'add') {
    $procedure_id = clean_text($_POST['procedure_id'] ?? '');
    $procedure_name = $procedure_names[$procedure_id] ?? clean_text($_POST['procedure_name'] ?? '');
    $patient_name = clean_text($_POST['patient_name'] ?? '');
    $email = clean_text($_POST['email'] ?? '');
    $phone = clean_text($_POST['phone'] ?? '');
    $appointment_date = clean_text($_POST['appointment_date'] ?? '');
    $appointment_time = clean_text($_POST['appointment_time'] ?? '');
    $notes = clean_text($_POST['notes'] ?? '');
    $status = clean_text($_POST['status'] ?? 'Pending');
    $assigned_staff = clean_text($_POST['assigned_staff'] ?? '');
    $source = clean_text($_POST['source'] ?? 'online');
    $recorded_by = isset($_SESSION['user_id']) ? (int) $_SESSION['user_id'] : null;

    if ($procedure_id === '' || $procedure_name === '' || $patient_name === '' || $phone === '' || $appointment_date === '' || $appointment_time === '') {
        echo "Please complete the required appointment fields.";
        exit();
    }

    $allowed_statuses = ['Pending', 'Confirmed', 'Completed', 'Cancelled', 'No Show'];
    if (!in_array($status, $allowed_statuses, true)) {
        $status = 'Pending';
    }

    $allowed_sources = ['online', 'staff'];
    if (!in_array($source, $allowed_sources, true)) {
        $source = 'online';
    }

    $stmt = $conn->prepare("
        INSERT INTO appointments
        (procedure_id, procedure_name, patient_name, email, phone, appointment_date, appointment_time, notes, status, assigned_staff, source, recorded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");

    $stmt->bind_param(
        "sssssssssssi",
        $procedure_id,
        $procedure_name,
        $patient_name,
        $email,
        $phone,
        $appointment_date,
        $appointment_time,
        $notes,
        $status,
        $assigned_staff,
        $source,
        $recorded_by
    );

    if ($stmt->execute()) {

    sendAppointmentEmail(
        $email,
        $patient_name,
        "DermaView Appointment Scheduled",
        "
        <h2>Appointment Scheduled</h2>
        <p>Hello <b>$patient_name</b>,</p>
        <p>Your appointment has been successfully scheduled.</p>

        <p><b>Procedure:</b> $procedure_name</p>
        <p><b>Date:</b> $appointment_date</p>
        <p><b>Time:</b> " . format_time_label($appointment_time) . "</p>
        <p><b>Status:</b> $status</p>

        <br>
        <p>Thank you for choosing DermaView.</p>
        "
    );

    echo "Appointment saved successfully.";

} else {
    echo "Failed to save appointment.";
}

    exit();
}

if ($action === 'update_status') {
    $id = (int) ($_POST['id'] ?? 0);
    $status = clean_text($_POST['status'] ?? '');
    $allowed_statuses = ['Pending', 'Confirmed', 'Completed', 'Cancelled', 'No Show'];

    if ($id <= 0 || !in_array($status, $allowed_statuses, true)) {
        echo "Invalid appointment update.";
        exit();
    }

    $stmt = $conn->prepare("
        UPDATE appointments
        SET status = ?
        WHERE id = ?
    ");
    $stmt->bind_param("si", $status, $id);

    if ($stmt->execute()) {

    $infoStmt = $conn->prepare("
        SELECT patient_name, email, procedure_name, appointment_date, appointment_time, status
        FROM appointments
        WHERE id = ?
    ");

    $infoStmt->bind_param("i", $id);
    $infoStmt->execute();

    $infoResult = $infoStmt->get_result();

    if ($infoResult && $infoResult->num_rows > 0) {
        $appointment = $infoResult->fetch_assoc();

        sendAppointmentEmail(
            $appointment['email'],
            $appointment['patient_name'],
            "DermaView Appointment Status Updated",
            "
            <h2>Appointment Status Updated</h2>

            <p>Hello <b>{$appointment['patient_name']}</b>,</p>

            <p>Your appointment status has been updated.</p>

            <p><b>Procedure:</b> {$appointment['procedure_name']}</p>
            <p><b>Date:</b> {$appointment['appointment_date']}</p>
            <p><b>Time:</b> " . format_time_label($appointment['appointment_time']) . "</p>
            <p><b>New Status:</b> $status</p>

            <br>
            <p>Please contact DermaView for any concerns.</p>
            "
        );
    }

    echo "Appointment status updated.";

} else {
    echo "Failed to update appointment.";
}

    exit();
}

if ($action === 'fetch_json') {
    header('Content-Type: application/json; charset=utf-8');

    $result = $conn->query("
        SELECT id, procedure_id, procedure_name, patient_name, email, phone, appointment_date, appointment_time, notes, status, assigned_staff, source
        FROM appointments
        ORDER BY appointment_date ASC, appointment_time ASC, id ASC
    ");

    $appointments = [];

    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $appointments[] = [
                'id' => (int) $row['id'],
                'procedure_id' => $row['procedure_id'],
                'procedure_name' => $row['procedure_name'],
                'patient_name' => $row['patient_name'],
                'email' => $row['email'],
                'phone' => $row['phone'],
                'appointment_date' => $row['appointment_date'],
                'appointment_time' => $row['appointment_time'],
                'time_label' => format_time_label($row['appointment_time']),
                'notes' => $row['notes'],
                'status' => $row['status'],
                'assigned_staff' => $row['assigned_staff'],
                'source' => $row['source']
            ];
        }
    }

    echo json_encode([
        'status' => 'ok',
        'appointments' => $appointments
    ]);
    exit();
}

if ($action === 'fetch') {
    $result = $conn->query("
        SELECT id, procedure_name, patient_name, email, phone, appointment_date, appointment_time, notes, status, assigned_staff, source
        FROM appointments
        ORDER BY appointment_date DESC, appointment_time DESC, id DESC
    ");

    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $id = (int) $row['id'];
            $date = htmlspecialchars(date('M j, Y', strtotime($row['appointment_date'])));
            $time = htmlspecialchars(format_time_label($row['appointment_time']));
            $patient_name = htmlspecialchars($row['patient_name']);
            $email = htmlspecialchars($row['email']);
            $phone = htmlspecialchars($row['phone']);
            $procedure_name = htmlspecialchars($row['procedure_name']);
            $assigned_staff = htmlspecialchars($row['assigned_staff'] ?: 'Unassigned');
            $status = htmlspecialchars($row['status']);
            $source = htmlspecialchars(ucfirst($row['source']));
            $notes = htmlspecialchars($row['notes']);
            $status_class = htmlspecialchars(status_class($row['status']));

            echo "
            <tr title='$notes'>
              <td><strong>$date</strong><br><span class='table-muted'>$time</span></td>
              <td>$patient_name</td>
              <td>$phone<br><span class='table-muted'>$email</span></td>
              <td>$procedure_name</td>
              <td>$assigned_staff</td>
              <td><span class='appointment-status $status_class'>$status</span></td>
              <td>$source</td>
              <td>
                <select class='appointment-status-select' data-id='$id'>
                  <option value='Pending' " . ($row['status'] === 'Pending' ? 'selected' : '') . ">Pending</option>
                  <option value='Confirmed' " . ($row['status'] === 'Confirmed' ? 'selected' : '') . ">Confirmed</option>
                  <option value='Completed' " . ($row['status'] === 'Completed' ? 'selected' : '') . ">Completed</option>
                  <option value='Cancelled' " . ($row['status'] === 'Cancelled' ? 'selected' : '') . ">Cancelled</option>
                  <option value='No Show' " . ($row['status'] === 'No Show' ? 'selected' : '') . ">No Show</option>
                </select>
              </td>
            </tr>
            ";
        }
    } else {
        echo "
        <tr>
          <td colspan='8' class='accounts-empty-cell'>
            No appointments found.
          </td>
        </tr>
        ";
    }

    exit();
}

echo "Invalid action.";
exit();

?>
