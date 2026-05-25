<?php
// Shared audit + presence helpers used by both admin and super_admin.

require_once __DIR__ . '/config.php';

function audit_ensure_tables($conn) {
    // Presence (online users)
    $conn->query("CREATE TABLE IF NOT EXISTS user_presence (
        id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_id VARCHAR(128) NOT NULL,
        role VARCHAR(64) NULL,
        user_name VARCHAR(160) NULL,
        last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_user_session (user_id, session_id),
        INDEX idx_last_seen (last_seen),
        INDEX idx_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    // Audit trail
    $conn->query("CREATE TABLE IF NOT EXISTS activity_logs (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        actor_user_id INT NULL,
        actor_role VARCHAR(64) NULL,
        actor_user_name VARCHAR(160) NULL,
        target_type VARCHAR(80) NULL,
        target_id VARCHAR(190) NULL,
        type VARCHAR(80) NOT NULL,
        title VARCHAR(255) NOT NULL,
        status VARCHAR(80) NULL,
        meta_json JSON NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_actor_created (actor_user_id, created_at),
        INDEX idx_created_at (created_at),
        INDEX idx_type_created (type, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
}

function audit_now_iso() {
    return gmdate('c');
}

function audit_current_actor() {
    $actor_user_id = isset($_SESSION['user_id']) ? (int)$_SESSION['user_id'] : null;
    $actor_role = isset($_SESSION['role']) ? (string)$_SESSION['role'] : null;
    $actor_user_name = isset($_SESSION['user_name']) ? (string)$_SESSION['user_name'] : null;

    return [$actor_user_id, $actor_role, $actor_user_name];
}

function audit_log($conn, $type, $title, $status = null, $target_type = null, $target_id = null, $meta = null) {
    if ($conn == null) return;

    $type = trim((string)$type);
    $title = trim((string)$title);
    if ($type === '' || $title === '') return;

    $meta_json = null;
    if (is_array($meta)) {
        $meta_json = json_encode($meta, JSON_UNESCAPED_UNICODE);
    }

    [$actor_user_id, $actor_role, $actor_user_name] = audit_current_actor();

    $stmt = $conn->prepare("
        INSERT INTO activity_logs
        (actor_user_id, actor_role, actor_user_name, target_type, target_id, type, title, status, meta_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");

    $status = $status === null ? null : (string)$status;
    $target_type = $target_type === null ? null : (string)$target_type;
    $target_id = $target_id === null ? null : (string)$target_id;

    // actor_user_id can be NULL; bind_param doesn't like NULL with i.
    // We'll handle by casting to int when present.
    $actor_user_id_val = $actor_user_id === null ? 0 : $actor_user_id;

    $stmt->bind_param(
        "issssssss",
        $actor_user_id_val,
        $actor_role,
        $actor_user_name,
        $target_type,
        $target_id,
        $type,
        $title,
        $status,
        $meta_json
    );

    // If actor_user_id was null, we still inserted 0. Fix to NULL.
    if ($actor_user_id === null) {
        $conn->query("UPDATE activity_logs SET actor_user_id = NULL WHERE id = LAST_INSERT_ID()");
    }

    $stmt->execute();
}

function audit_get_recent_activity($conn, $limit = 50) {
    audit_ensure_tables($conn);
    $limit = max(1, (int)$limit);

    $stmt = $conn->prepare("
        SELECT type, title, status, created_at, actor_user_name
        FROM activity_logs
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    ");
    $stmt->bind_param("i", $limit);
    $stmt->execute();
    $result = $stmt->get_result();

    $items = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $items[] = [
                'type' => $row['type'],
                'title' => $row['title'] . (empty($row['actor_user_name']) ? '' : (' — ' . $row['actor_user_name'])),
                'status' => $row['status'] ?: 'Recorded',
                'date' => $row['created_at']
            ];
        }
    }

    return $items;
}

function presence_touch($conn) {
    audit_ensure_tables($conn);

    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }

    if (!isset($_SESSION['user_id'])) return;

    $user_id = (int)$_SESSION['user_id'];
    $role = isset($_SESSION['role']) ? (string)$_SESSION['role'] : null;
    $user_name = isset($_SESSION['user_name']) ? (string)$_SESSION['user_name'] : null;

    // Use PHP session id if available.
    $session_id = session_id();
    if (!$session_id) $session_id = bin2hex(random_bytes(16));

    $stmt = $conn->prepare("
        INSERT INTO user_presence (user_id, session_id, role, user_name, last_seen)
        VALUES (?, ?, ?, ?, NOW())
        ON DUPLICATE KEY UPDATE
            role = VALUES(role),
            user_name = VALUES(user_name),
            last_seen = NOW()
    ");

    $stmt->bind_param("isss", $user_id, $session_id, $role, $user_name);
    $stmt->execute();
}

function presence_set_offline($conn) {
    audit_ensure_tables($conn);

    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }

    if (!isset($_SESSION['user_id'])) return;

    $user_id = (int)$_SESSION['user_id'];
    $role = isset($_SESSION['role']) ? (string)$_SESSION['role'] : null;
    $user_name = isset($_SESSION['user_name']) ? (string)$_SESSION['user_name'] : null;
    $session_id = session_id();

    // Mark last_seen to far past to be excluded by online threshold.
    $past = date('Y-m-d H:i:s', time() - 3600);

    $stmt = $conn->prepare("
        UPDATE user_presence
        SET role = ?, user_name = ?, last_seen = ?
        WHERE user_id = ? AND session_id = ?
    ");
    $stmt->bind_param("sssis", $role, $user_name, $past, $user_id, $session_id);
    $stmt->execute();
}

function presence_get_online_users($conn, $within_seconds = 90) {
    audit_ensure_tables($conn);

    $within_seconds = max(10, (int)$within_seconds);

    $cutoff = date('Y-m-d H:i:s', time() - $within_seconds);

    $stmt = $conn->prepare("
        SELECT user_id, role, user_name, MAX(last_seen) AS last_seen
        FROM user_presence
        WHERE last_seen >= ?
        GROUP BY user_id, role, user_name
        ORDER BY last_seen DESC
        LIMIT 50
    ");

    $stmt->bind_param("s", $cutoff);
    $stmt->execute();
    $result = $stmt->get_result();

    $items = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $items[] = [
                'user_id' => (int)$row['user_id'],
                'role' => $row['role'],
                'user_name' => $row['user_name'] ?: ('User #' . (int)$row['user_id']),
                'last_seen' => $row['last_seen']
            ];
        }
    }

    return $items;
}

