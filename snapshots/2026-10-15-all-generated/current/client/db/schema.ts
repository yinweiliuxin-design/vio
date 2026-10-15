import { sql } from 'drizzle-orm';
import { sqliteTable, text, integer, index, uniqueIndex, primaryKey, check } from 'drizzle-orm/sqlite-core';

export const communityUsers = sqliteTable('community_users', {
  id: text('id').primaryKey(),
  name: text('name').notNull().default('琴友'),
  disabled: integer('disabled').notNull().default(0),
  version: integer('version').notNull().default(1),
  createdAt: text('created_at').notNull(), updatedAt: text('updated_at').notNull(),
  mutationToken: text('mutation_token').notNull().default(''),
  learnGuideVersion: integer('learn_guide_version').notNull().default(2),
  learnGuideStatus: text('learn_guide_status').notNull().default('legacy'),
  learnGuideStep: integer('learn_guide_step').notNull().default(0),
  learnGuideUpdatedAt: text('learn_guide_updated_at'),
}, table => [
  check('community_user_disabled', sql`${table.disabled} IN (0, 1)`), check('community_user_version', sql`${table.version} >= 1`),
  check('community_user_guide_version', sql`${table.learnGuideVersion} = 2`),
  check('community_user_guide_status', sql`${table.learnGuideStatus} IN ('legacy', 'pending', 'in_progress', 'completed', 'skipped')`),
  check('community_user_guide_step', sql`typeof(${table.learnGuideStep}) = 'integer' AND ${table.learnGuideStep} BETWEEN 0 AND 6`),
]);

export const communityPosts = sqliteTable('community_posts', {
  id: text('id').primaryKey(), userId: text('user_id').notNull().references(() => communityUsers.id),
  clientRequestId: text('client_request_id').notNull(), requestHash: text('request_hash').notNull(),
  title: text('title').notNull().default(''), text: text('text').notNull().default(''),
  topic: text('topic').notNull().default('practice'),
  attachmentsJson: text('attachments_json').notNull().default('[]'),
  rightsConfirmed: integer('rights_confirmed').notNull().default(0),
  status: text('status').notNull().default('draft'), version: integer('version').notNull().default(1),
  moderationReason: text('moderation_reason').notNull().default(''),
  createdAt: text('created_at').notNull(), updatedAt: text('updated_at').notNull(),
  mutationToken: text('mutation_token').notNull(),
}, table => [
  uniqueIndex('community_post_request').on(table.userId, table.clientRequestId),
  index('community_post_feed').on(table.status, table.createdAt), index('community_post_owner').on(table.userId, table.updatedAt),
  check('community_post_status', sql`${table.status} IN ('draft','pending','published','rejected','hidden','deleted')`),
  check('community_post_topic', sql`${table.topic} IN ('practice','help','work')`),
  check('community_post_version', sql`${table.version} >= 1`), check('community_post_rights', sql`${table.rightsConfirmed} IN (0,1)`),
]);

export const communityComments = sqliteTable('community_comments', {
  id: text('id').primaryKey(), postId: text('post_id').notNull().references(() => communityPosts.id),
  userId: text('user_id').notNull().references(() => communityUsers.id),
  clientRequestId: text('client_request_id').notNull(), requestHash: text('request_hash').notNull(),
  text: text('text').notNull(), status: text('status').notNull().default('pending'),
  version: integer('version').notNull().default(1), moderationReason: text('moderation_reason').notNull().default(''),
  createdAt: text('created_at').notNull(), updatedAt: text('updated_at').notNull(), mutationToken: text('mutation_token').notNull(),
}, table => [
  uniqueIndex('community_comment_request').on(table.userId, table.clientRequestId), index('community_comment_post').on(table.postId, table.status, table.createdAt),
  index('community_comment_owner').on(table.userId, table.updatedAt),
  check('community_comment_status', sql`${table.status} IN ('pending','published','rejected','hidden','deleted')`), check('community_comment_version', sql`${table.version} >= 1`),
]);

export const communityLikes = sqliteTable('community_likes', {
  postId: text('post_id').notNull().references(() => communityPosts.id), userId: text('user_id').notNull().references(() => communityUsers.id),
  createdAt: text('created_at').notNull(),
}, table => [primaryKey({ columns: [table.postId, table.userId] })]);

export const communityReports = sqliteTable('community_reports', {
  id: text('id').primaryKey(), userId: text('user_id').notNull().references(() => communityUsers.id),
  targetType: text('target_type').notNull(), targetId: text('target_id').notNull(), reason: text('reason').notNull(),
  status: text('status').notNull().default('open'), resolution: text('resolution').notNull().default(''),
  version: integer('version').notNull().default(1), createdAt: text('created_at').notNull(), updatedAt: text('updated_at').notNull(),
  mutationToken: text('mutation_token').notNull(),
}, table => [
  uniqueIndex('community_report_open').on(table.userId, table.targetType, table.targetId).where(sql`${table.status} = 'open'`),
  index('community_report_queue').on(table.status, table.createdAt),
  check('community_report_type', sql`${table.targetType} IN ('post','comment')`), check('community_report_status', sql`${table.status} IN ('open','resolved','dismissed')`),
]);

export const communitySettings = sqliteTable('community_settings', {
  id: text('id').primaryKey(), postingEnabled: integer('posting_enabled').notNull().default(1),
  commentsEnabled: integer('comments_enabled').notNull().default(1), likesEnabled: integer('likes_enabled').notNull().default(1),
  allowExternalLinks: integer('allow_external_links').notNull().default(1),
  cloudPresetBackupEnabled: integer('cloud_preset_backup_enabled').notNull().default(1),
  announcementJson: text('announcement_json').notNull().default('{"zh":"","en":"","ja":"","de":""}'),
  catalogHiddenIdsJson: text('catalog_hidden_ids_json').notNull().default('[]'),
  version: integer('version').notNull().default(1), updatedAt: text('updated_at').notNull(), mutationToken: text('mutation_token').notNull(),
}, table => [
  check('community_settings_singleton', sql`${table.id} = 'global'`), check('community_settings_version', sql`${table.version} >= 1`),
  check('community_settings_booleans', sql`${table.postingEnabled} IN (0,1) AND ${table.commentsEnabled} IN (0,1) AND ${table.likesEnabled} IN (0,1) AND ${table.allowExternalLinks} IN (0,1)`),
  check('community_settings_preset_backup', sql`${table.cloudPresetBackupEnabled} IN (0,1)`),
]);

// Private, account-owned snapshots. These parameters never appear in community/admin responses.
export const userPresetBackups = sqliteTable('user_preset_backups', {
  userId: text('user_id').primaryKey().references(() => communityUsers.id),
  presetsJson: text('presets_json').notNull().default('[]'),
  version: integer('version').notNull().default(1),
  updatedAt: text('updated_at').notNull(), mutationToken: text('mutation_token').notNull(),
}, table => [
  check('user_preset_backup_version', sql`${table.version} >= 1`),
  check('user_preset_backup_json', sql`json_valid(${table.presetsJson}) AND json_type(${table.presetsJson}) = 'array' AND json_array_length(${table.presetsJson}) <= 100`),
]);

export const communityMedia = sqliteTable('community_media', {
  id: text('id').primaryKey(), userId: text('user_id').notNull().references(() => communityUsers.id),
  objectKey: text('object_key').notNull(), mime: text('mime').notNull(), size: integer('size').notNull(),
  createdAt: text('created_at').notNull(), mutationToken: text('mutation_token').notNull(),
}, table => [
  uniqueIndex('community_media_object').on(table.objectKey), index('community_media_owner').on(table.userId, table.createdAt),
  check('community_media_size', sql`${table.size} BETWEEN 1 AND 5242880`), check('community_media_type', sql`${table.mime} IN ('image/png','image/jpeg','image/webp')`),
]);

// Video objects remain private; lifecycle tombstones survive object cleanup and late uploads.
export const communityVideos = sqliteTable('community_videos', {
  id: text('id').primaryKey(), userId: text('user_id').notNull().references(() => communityUsers.id),
  objectKey: text('object_key').notNull(), requestHash: text('request_hash').notNull().default(''),
  mime: text('mime').notNull().default(''), size: integer('size').notNull().default(0),
  durationMs: integer('duration_ms').notNull().default(0), width: integer('width').notNull().default(0), height: integer('height').notNull().default(0),
  container: text('container').notNull().default(''), videoCodec: text('video_codec').notNull().default(''), audioCodec: text('audio_codec').notNull().default(''),
  verification: text('verification').notNull().default(''),
  state: text('state').notNull().default('uploading'), uploadActive: integer('upload_active').notNull().default(0),
  cleanupPending: integer('cleanup_pending').notNull().default(0), errorCode: text('error_code').notNull().default(''),
  uploadToken: text('upload_token').notNull(), version: integer('version').notNull().default(1),
  createdAt: text('created_at').notNull(), updatedAt: text('updated_at').notNull(), mutationToken: text('mutation_token').notNull(),
}, table => [
  uniqueIndex('community_video_object').on(table.objectKey), index('community_video_owner').on(table.userId, table.state, table.createdAt),
  check('community_video_state', sql`${table.state} IN ('uploading','ready','failed','cancelled','deleting','deleted')`),
  check('community_video_size', sql`typeof(${table.size}) = 'integer' AND ${table.size} BETWEEN 0 AND 20000000`),
  check('community_video_duration', sql`typeof(${table.durationMs}) = 'integer' AND ${table.durationMs} BETWEEN 0 AND 60000`),
  check('community_video_dimensions', sql`${table.width} BETWEEN 0 AND 4096 AND ${table.height} BETWEEN 0 AND 4096 AND ${table.width} * ${table.height} <= 8294400`),
  check('community_video_type', sql`${table.mime} IN ('','video/mp4','video/webm')`),
  check('community_video_flags', sql`${table.uploadActive} IN (0,1) AND ${table.cleanupPending} IN (0,1) AND ${table.version} >= 1`),
  check('community_video_ready', sql`${table.state} <> 'ready' OR (${table.size} > 0 AND ${table.durationMs} > 0 AND ${table.width} > 0 AND ${table.height} > 0 AND ${table.mime} <> '' AND length(${table.requestHash}) = 64 AND ${table.uploadActive} = 0 AND ${table.cleanupPending} = 0)`),
]);

export const communityAudit = sqliteTable('community_audit', {
  id: text('id').primaryKey(), actorId: text('actor_id').notNull(), action: text('action').notNull(),
  targetType: text('target_type').notNull(), targetId: text('target_id').notNull(),
  detailJson: text('detail_json').notNull(), at: text('at').notNull(),
}, table => [
  index('community_audit_time').on(table.at),
  // A failed compare-and-swap makes this check abort the ENTIRE D1 batch, including its content write.
  check('community_cas_guard', sql`${table.action} <> '__cas_failed__'`),
]);
