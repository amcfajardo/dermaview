<?php

include '../config.php';

header('Content-Type: application/json; charset=utf-8');

function clean_text($value) {
    return trim((string) $value);
}

function ensure_procedures_table($conn) {
    $conn->query("
        CREATE TABLE IF NOT EXISTS procedures (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            procedure_name VARCHAR(180) NOT NULL,
            category VARCHAR(80) NOT NULL,
            short_description TEXT NOT NULL,
            full_description TEXT NULL,
            benefits TEXT NULL,
            preparation_guidelines TEXT NULL,
            aftercare_instructions TEXT NULL,
            session_duration VARCHAR(80) NULL,
            recommended_sessions VARCHAR(80) NULL,
            status ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
            procedure_image VARCHAR(255) NULL,
            sort_order INT UNSIGNED NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_procedures_status (status),
            INDEX idx_procedures_category (category),
            INDEX idx_procedures_sort_order (sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");

    $column_check = $conn->query("
        SELECT COUNT(*) AS total
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'procedures'
          AND column_name = 'sort_order'
    ");
    $column_row = $column_check ? $column_check->fetch_assoc() : ['total' => 0];

    if ((int) $column_row['total'] === 0) {
        $conn->query("ALTER TABLE procedures ADD COLUMN sort_order INT UNSIGNED NOT NULL DEFAULT 0 AFTER procedure_image");
        $conn->query("ALTER TABLE procedures ADD INDEX idx_procedures_sort_order (sort_order)");
    }

    $conn->query("UPDATE procedures SET sort_order = id WHERE sort_order = 0");

    $result = $conn->query("SELECT COUNT(*) AS total FROM procedures");
    $row = $result ? $result->fetch_assoc() : ['total' => 0];

    if ((int) $row['total'] > 0) {
        return;
    }

    $seed = [
        ['CO2 Fractional Laser + Dermapen', 'Laser', 'Combined resurfacing and microneedling for texture, scars, and rejuvenation.', 'A combined procedure plan used for patient education and treatment documentation.', 'Improves appearance of texture, scarring, and uneven tone.', 'Avoid harsh actives and disclose recent procedures.', 'Use sun protection and follow clinic aftercare.', '45-90 minutes', '3-5 sessions'],
        ['Face Slimming Package', 'Contouring', 'Non-surgical contouring plan for facial definition and balance.', 'A contouring package for facial slimming awareness and planning.', 'Supports facial balance and jawline definition.', 'Avoid alcohol and disclose medication history.', 'Avoid massage unless instructed by staff.', '30-60 minutes', '1-3 sessions'],
        ['Diamond Peel with Facial', 'Facial', 'Gentle exfoliation with cleansing facial care for smoother-looking skin.', 'A facial service combining exfoliation and cleansing steps.', 'Helps remove dull surface buildup and improves skin feel.', 'Arrive with clean skin when possible.', 'Avoid harsh scrubs for several days.', '45-60 minutes', '1-4 sessions'],
        ['Undereye and Lip Filler', 'Filler', 'Targeted filler service for undereye support and lip enhancement.', 'A filler procedure documented for awareness and consultation review.', 'Supports volume correction and profile balance.', 'Disclose allergies, medication, and previous fillers.', 'Avoid pressure, heat, and strenuous activity as instructed.', '45-75 minutes', '1 session plus review'],
        ['PICO Carbon Laser Facial', 'Skin Rejuvenation', 'Carbon-assisted laser facial for tone, pores, and brightness.', 'A laser facial option for skin rejuvenation awareness.', 'Improves brightness, oil appearance, and visible pores.', 'Avoid sun exposure before treatment.', 'Use sunscreen and gentle products after treatment.', '45-60 minutes', '3-6 sessions'],
        ['Lip Filler, Chin Filler, and Jawtox', 'Filler', 'Profile-balancing injectables for lips, chin, and jawline tension.', 'A combined injectable package for consultation documentation.', 'Supports profile harmony and jawline relaxation.', 'Avoid blood-thinning products unless medically required.', 'Avoid heavy exercise and pressure after treatment.', '60-90 minutes', '1 session plus review'],
        ['General Skin Assessment', 'Acne Treatment', 'Consultation-based assessment for personalized treatment planning.', 'A baseline consultation for skin condition review and treatment planning.', 'Helps staff recommend appropriate procedures and care.', 'Bring medication and skincare history.', 'Follow the personalized care plan.', '30 minutes', '1 session']
    ];

    $stmt = $conn->prepare("
        INSERT INTO procedures
        (procedure_name, category, short_description, full_description, benefits, preparation_guidelines, aftercare_instructions, session_duration, recommended_sessions, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");

    foreach ($seed as $index => $item) {
        $sort_order = $index + 1;
        $stmt->bind_param("sssssssssi", $item[0], $item[1], $item[2], $item[3], $item[4], $item[5], $item[6], $item[7], $item[8], $sort_order);
        $stmt->execute();
    }
}

function save_uploaded_image() {
    if (empty($_FILES['procedure_image']['tmp_name'])) {
        return null;
    }

    $allowed = [
        'image/jpeg' => 'jpg',
        'image/png' => 'png',
        'image/webp' => 'webp'
    ];
    $mime = mime_content_type($_FILES['procedure_image']['tmp_name']);

    if (!isset($allowed[$mime])) {
        return null;
    }

    $dir = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'uploads' . DIRECTORY_SEPARATOR . 'procedures';
    if (!is_dir($dir)) {
        mkdir($dir, 0775, true);
    }

    $name = 'procedure-' . date('Ymd-His') . '-' . bin2hex(random_bytes(4)) . '.' . $allowed[$mime];
    $path = $dir . DIRECTORY_SEPARATOR . $name;

    if (!move_uploaded_file($_FILES['procedure_image']['tmp_name'], $path)) {
        return null;
    }

    return 'uploads/procedures/' . $name;
}

ensure_procedures_table($conn);

$action = $_POST['action'] ?? 'fetch';

if ($action === 'fetch' || $action === 'fetch_public') {
    $where = $action === 'fetch_public' ? "WHERE status = 'Active'" : "";
    $result = $conn->query("
        SELECT id, procedure_name, category, short_description, full_description, benefits,
               preparation_guidelines, aftercare_instructions, session_duration,
               recommended_sessions, status, procedure_image, sort_order, updated_at
        FROM procedures
        $where
        ORDER BY sort_order ASC, id ASC
    ");

    $procedures = [];

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $procedures[] = $row;
        }
    }

    echo json_encode(['status' => 'ok', 'procedures' => $procedures]);
    exit();
}

if ($action === 'save') {
    $id = (int) ($_POST['id'] ?? 0);
    $name = clean_text($_POST['procedure_name'] ?? '');
    $category = clean_text($_POST['category'] ?? '');
    $short = clean_text($_POST['short_description'] ?? '');
    $full = clean_text($_POST['full_description'] ?? '');
    $benefits = clean_text($_POST['benefits'] ?? '');
    $preparation = clean_text($_POST['preparation_guidelines'] ?? '');
    $aftercare = clean_text($_POST['aftercare_instructions'] ?? '');
    $duration = clean_text($_POST['session_duration'] ?? '');
    $sessions = clean_text($_POST['recommended_sessions'] ?? '');
    $status = clean_text($_POST['status'] ?? 'Active');
    $image = save_uploaded_image();

    if ($name === '' || $category === '' || $short === '') {
        http_response_code(422);
        echo json_encode(['status' => 'error', 'message' => 'Procedure name, category, and description are required.']);
        exit();
    }

    if (!in_array($status, ['Active', 'Inactive'], true)) {
        $status = 'Active';
    }

    if ($id > 0) {
        if ($image) {
            $stmt = $conn->prepare("
                UPDATE procedures
                SET procedure_name=?, category=?, short_description=?, full_description=?, benefits=?,
                    preparation_guidelines=?, aftercare_instructions=?, session_duration=?,
                    recommended_sessions=?, status=?, procedure_image=?
                WHERE id=?
            ");
            $stmt->bind_param("sssssssssssi", $name, $category, $short, $full, $benefits, $preparation, $aftercare, $duration, $sessions, $status, $image, $id);
        } else {
            $stmt = $conn->prepare("
                UPDATE procedures
                SET procedure_name=?, category=?, short_description=?, full_description=?, benefits=?,
                    preparation_guidelines=?, aftercare_instructions=?, session_duration=?,
                    recommended_sessions=?, status=?
                WHERE id=?
            ");
            $stmt->bind_param("ssssssssssi", $name, $category, $short, $full, $benefits, $preparation, $aftercare, $duration, $sessions, $status, $id);
        }
    } else {
        $sort_result = $conn->query("SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM procedures");
        $sort_row = $sort_result ? $sort_result->fetch_assoc() : ['next_order' => 1];
        $sort_order = (int) $sort_row['next_order'];

        $stmt = $conn->prepare("
            INSERT INTO procedures
            (procedure_name, category, short_description, full_description, benefits, preparation_guidelines,
             aftercare_instructions, session_duration, recommended_sessions, status, procedure_image, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->bind_param("sssssssssssi", $name, $category, $short, $full, $benefits, $preparation, $aftercare, $duration, $sessions, $status, $image, $sort_order);
    }

    if ($stmt->execute()) {
        echo json_encode(['status' => 'ok', 'message' => 'Procedure saved.']);
    } else {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'message' => 'Failed to save procedure.']);
    }

    exit();
}

if ($action === 'toggle') {
    $id = (int) ($_POST['id'] ?? 0);
    $stmt = $conn->prepare("
        UPDATE procedures
        SET status = IF(status = 'Active', 'Inactive', 'Active')
        WHERE id = ?
    ");
    $stmt->bind_param("i", $id);
    $stmt->execute();
    echo json_encode(['status' => 'ok', 'message' => 'Procedure status updated.']);
    exit();
}

if ($action === 'reorder') {
    $ids_json = $_POST['ids'] ?? '[]';
    $ids = json_decode($ids_json, true);

    if (!is_array($ids)) {
        http_response_code(422);
        echo json_encode(['status' => 'error', 'message' => 'Invalid procedure order.']);
        exit();
    }

    $stmt = $conn->prepare("UPDATE procedures SET sort_order = ? WHERE id = ?");

    foreach ($ids as $index => $id) {
        $sort_order = $index + 1;
        $procedure_id = (int) $id;

        if ($procedure_id <= 0) {
            continue;
        }

        $stmt->bind_param("ii", $sort_order, $procedure_id);
        $stmt->execute();
    }

    echo json_encode(['status' => 'ok', 'message' => 'Procedure order saved.']);
    exit();
}

if ($action === 'delete') {
    $id = (int) ($_POST['id'] ?? 0);
    $stmt = $conn->prepare("DELETE FROM procedures WHERE id = ?");
    $stmt->bind_param("i", $id);
    $stmt->execute();
    echo json_encode(['status' => 'ok', 'message' => 'Procedure deleted.']);
    exit();
}

http_response_code(400);
echo json_encode(['status' => 'error', 'message' => 'Invalid action.']);

?>
