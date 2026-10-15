CREATE TABLE `user_preset_backups` (
	`user_id` text PRIMARY KEY NOT NULL,
	`presets_json` text DEFAULT '[]' NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	`updated_at` text NOT NULL,
	`mutation_token` text NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `community_users`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "user_preset_backup_version" CHECK("user_preset_backups"."version" >= 1),
	CONSTRAINT "user_preset_backup_json" CHECK(json_valid("user_preset_backups"."presets_json") AND json_type("user_preset_backups"."presets_json") = 'array' AND json_array_length("user_preset_backups"."presets_json") <= 100)
);
--> statement-breakpoint
-- Add the feature flag in place; preserve existing settings and all referencing data.
ALTER TABLE `community_settings` ADD COLUMN `cloud_preset_backup_enabled` integer DEFAULT 1 NOT NULL CONSTRAINT `community_settings_preset_backup` CHECK (`cloud_preset_backup_enabled` IN (0,1));
