CREATE TABLE `community_audit` (
	`id` text PRIMARY KEY NOT NULL,
	`actor_id` text NOT NULL,
	`action` text NOT NULL,
	`target_type` text NOT NULL,
	`target_id` text NOT NULL,
	`detail_json` text NOT NULL,
	`at` text NOT NULL,
	CONSTRAINT "community_cas_guard" CHECK("community_audit"."action" <> '__cas_failed__')
);
--> statement-breakpoint
CREATE INDEX `community_audit_time` ON `community_audit` (`at`);--> statement-breakpoint
CREATE TABLE `community_comments` (
	`id` text PRIMARY KEY NOT NULL,
	`post_id` text NOT NULL,
	`user_id` text NOT NULL,
	`client_request_id` text NOT NULL,
	`request_hash` text NOT NULL,
	`text` text NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	`moderation_reason` text DEFAULT '' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`mutation_token` text NOT NULL,
	FOREIGN KEY (`post_id`) REFERENCES `community_posts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`user_id`) REFERENCES `community_users`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "community_comment_status" CHECK("community_comments"."status" IN ('pending','published','rejected','hidden','deleted')),
	CONSTRAINT "community_comment_version" CHECK("community_comments"."version" >= 1)
);
--> statement-breakpoint
CREATE UNIQUE INDEX `community_comment_request` ON `community_comments` (`user_id`,`client_request_id`);--> statement-breakpoint
CREATE INDEX `community_comment_post` ON `community_comments` (`post_id`,`status`,`created_at`);--> statement-breakpoint
CREATE INDEX `community_comment_owner` ON `community_comments` (`user_id`,`updated_at`);--> statement-breakpoint
CREATE TABLE `community_likes` (
	`post_id` text NOT NULL,
	`user_id` text NOT NULL,
	`created_at` text NOT NULL,
	PRIMARY KEY(`post_id`, `user_id`),
	FOREIGN KEY (`post_id`) REFERENCES `community_posts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`user_id`) REFERENCES `community_users`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `community_media` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`object_key` text NOT NULL,
	`mime` text NOT NULL,
	`size` integer NOT NULL,
	`created_at` text NOT NULL,
	`mutation_token` text NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `community_users`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "community_media_size" CHECK("community_media"."size" BETWEEN 1 AND 5242880),
	CONSTRAINT "community_media_type" CHECK("community_media"."mime" IN ('image/png','image/jpeg','image/webp'))
);
--> statement-breakpoint
CREATE UNIQUE INDEX `community_media_object` ON `community_media` (`object_key`);--> statement-breakpoint
CREATE INDEX `community_media_owner` ON `community_media` (`user_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `community_posts` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`client_request_id` text NOT NULL,
	`request_hash` text NOT NULL,
	`title` text DEFAULT '' NOT NULL,
	`text` text DEFAULT '' NOT NULL,
	`attachments_json` text DEFAULT '[]' NOT NULL,
	`rights_confirmed` integer DEFAULT 0 NOT NULL,
	`status` text DEFAULT 'draft' NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	`moderation_reason` text DEFAULT '' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`mutation_token` text NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `community_users`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "community_post_status" CHECK("community_posts"."status" IN ('draft','pending','published','rejected','hidden','deleted')),
	CONSTRAINT "community_post_version" CHECK("community_posts"."version" >= 1),
	CONSTRAINT "community_post_rights" CHECK("community_posts"."rights_confirmed" IN (0,1))
);
--> statement-breakpoint
CREATE UNIQUE INDEX `community_post_request` ON `community_posts` (`user_id`,`client_request_id`);--> statement-breakpoint
CREATE INDEX `community_post_feed` ON `community_posts` (`status`,`created_at`);--> statement-breakpoint
CREATE INDEX `community_post_owner` ON `community_posts` (`user_id`,`updated_at`);--> statement-breakpoint
CREATE TABLE `community_reports` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`target_type` text NOT NULL,
	`target_id` text NOT NULL,
	`reason` text NOT NULL,
	`status` text DEFAULT 'open' NOT NULL,
	`resolution` text DEFAULT '' NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`mutation_token` text NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `community_users`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "community_report_type" CHECK("community_reports"."target_type" IN ('post','comment')),
	CONSTRAINT "community_report_status" CHECK("community_reports"."status" IN ('open','resolved','dismissed'))
);
--> statement-breakpoint
CREATE UNIQUE INDEX `community_report_open` ON `community_reports` (`user_id`,`target_type`,`target_id`) WHERE "community_reports"."status" = 'open';--> statement-breakpoint
CREATE INDEX `community_report_queue` ON `community_reports` (`status`,`created_at`);--> statement-breakpoint
CREATE TABLE `community_settings` (
	`id` text PRIMARY KEY NOT NULL,
	`posting_enabled` integer DEFAULT 1 NOT NULL,
	`comments_enabled` integer DEFAULT 1 NOT NULL,
	`likes_enabled` integer DEFAULT 1 NOT NULL,
	`allow_external_links` integer DEFAULT 1 NOT NULL,
	`announcement_json` text DEFAULT '{"zh":"","en":"","ja":"","de":""}' NOT NULL,
	`catalog_hidden_ids_json` text DEFAULT '[]' NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	`updated_at` text NOT NULL,
	`mutation_token` text NOT NULL,
	CONSTRAINT "community_settings_singleton" CHECK("community_settings"."id" = 'global'),
	CONSTRAINT "community_settings_version" CHECK("community_settings"."version" >= 1),
	CONSTRAINT "community_settings_booleans" CHECK("community_settings"."posting_enabled" IN (0,1) AND "community_settings"."comments_enabled" IN (0,1) AND "community_settings"."likes_enabled" IN (0,1) AND "community_settings"."allow_external_links" IN (0,1))
);
--> statement-breakpoint
CREATE TABLE `community_users` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text DEFAULT '琴友' NOT NULL,
	`disabled` integer DEFAULT 0 NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`mutation_token` text DEFAULT '' NOT NULL,
	CONSTRAINT "community_user_disabled" CHECK("community_users"."disabled" IN (0, 1)),
	CONSTRAINT "community_user_version" CHECK("community_users"."version" >= 1)
);
