-- Add columns in place: preserve existing users and every referencing post/comment/media row.
-- The generated rebuild attempted to SELECT new columns from the old table; it has never been applied.
ALTER TABLE `community_users` ADD COLUMN `learn_guide_version` integer DEFAULT 2 NOT NULL CONSTRAINT `community_user_guide_version` CHECK (`learn_guide_version` = 2);
--> statement-breakpoint
ALTER TABLE `community_users` ADD COLUMN `learn_guide_status` text DEFAULT 'legacy' NOT NULL CONSTRAINT `community_user_guide_status` CHECK (`learn_guide_status` IN ('legacy', 'pending', 'in_progress', 'completed', 'skipped'));
--> statement-breakpoint
ALTER TABLE `community_users` ADD COLUMN `learn_guide_step` integer DEFAULT 0 NOT NULL CONSTRAINT `community_user_guide_step` CHECK (typeof(`learn_guide_step`) = 'integer' AND `learn_guide_step` BETWEEN 0 AND 6);
--> statement-breakpoint
ALTER TABLE `community_users` ADD COLUMN `learn_guide_updated_at` text;
