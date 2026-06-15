SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS `users`;
DROP VIEW IF EXISTS `users`;
DROP TABLE IF EXISTS `users_data`;

CREATE TABLE `users_data` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `role` varchar(50) NOT NULL,
  `employee_number` varchar(255) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `status` varchar(20) DEFAULT 'Active',
  `must_change_password` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`employee_number`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('20', 'yes175929@gmail.com', 'Staff', 'One', 'staff', '211', '$2y$10$iHfVtqsaHPKy.LXtWhlijOY5hfaVOjXp5CzRd2oXs4LdQwbXESvFW', '2026-05-25 22:17:08', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('21', 'raeqt0917@gmail.com', 'Staff', 'Two', 'staff', '212', '$2y$10$MevbtoPJ/yc8d40f9SlBVuvhwUvAyBqhI3V6sFJEwQZfqLtTESfOu', '2026-05-25 22:17:27', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('22', 'eamfjrdzz0917@gmail.com', 'Staff', 'Three', 'staff', '213', '$2y$10$oWp1OxOyB9B1UwphH8UnK..bgYWSF3nkvlL/arabecFhQKAICYRz2', '2026-05-25 22:17:48', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('23', 'rain.qwerty12@gmail.com', 'Staff', 'Four', 'staff', '214', '$2y$10$ksXMXLTIFNtsqs2HUVgnYOY6JB4mcp8Ga3V0FczmHYxOZhw8FN.Wq', '2026-05-25 22:18:03', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('24', 'tktkabc123@gmail.com', 'Staff', 'Five', 'staff', '215', '$2y$10$WU7Ez6F1NW2JgbjQZRcJVeAEcYrPnBhw168p15Sw10jZ30rfEiT0C', '2026-05-25 22:18:33', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('25', 'drmsungs@gmail.com', 'Admin', 'One', 'admin', '216', '$2y$10$LQ5gX86WzQm2A3VMvPHuAu7QTnmURMb2YFxZOgckO8xaCGg2NeVKy', '2026-05-25 22:18:50', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('26', 'dizongabby0916@gmail.com', 'Admin', 'Two', 'admin', '217', '$2y$10$6s1MDN4TclNCcW6tioCnz.lyVk8rfTqfz8m0ALEXPmhZ37WXDakRW', '2026-05-25 22:19:04', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('27', 'dizongabby101@gmail.com', 'Admin', 'Three', 'admin', '218', '$2y$10$4.ZFAX4cYhmOTpTaGVfu3OpOohVzFnBZorihgx2EwsJV80sxqVoR.', '2026-05-25 22:19:19', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('28', 'rgabrielolivar@gmail.com', 'Super', 'Admin1', 'superadmin', '219', '$2y$10$6VH/Nqvr08W2K.ziz6QfJO4yyTUgKI78ECO2aZOw55oKExztsgNsi', '2026-05-25 22:19:35', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('29', 'oliva.gabrielb@gmail.com', 'Super', 'Admin2', 'superadmin', '220', '$2y$10$fIMMZNQIR/hFFHKHV8cAe.5WgW3/eXppkQ4eOaiP9.3P6S0PNzdkm', '2026-05-25 22:19:53', 'Active', '0');
INSERT INTO `users_data` (`id`, `email`, `first_name`, `last_name`, `role`, `employee_number`, `password`, `created_at`, `status`, `must_change_password`) VALUES ('31', 'kyleangela592@gmail.com', 'staff', 'six', 'staff', '111', '$2y$10$ku5G2mSUj6Q1b68IN0zfm.mF/Xe5JgvPiA4/yDiZWsY2Yy/s1EurW', '2026-05-26 18:02:05', 'Active', '0');

CREATE VIEW `users` AS SELECT * FROM `users_data`;

SET FOREIGN_KEY_CHECKS=1;
