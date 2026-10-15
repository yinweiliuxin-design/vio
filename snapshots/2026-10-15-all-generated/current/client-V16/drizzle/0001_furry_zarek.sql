ALTER TABLE `community_posts` ADD COLUMN `topic` text NOT NULL DEFAULT 'practice' CHECK (`topic` IN ('practice','help','work'));
