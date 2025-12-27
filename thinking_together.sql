/*
 Navicat Premium Data Transfer

 Source Server         : Mysql
 Source Server Type    : MySQL
 Source Server Version : 80012
 Source Host           : localhost:3306
 Source Schema         : thinking_together

 Target Server Type    : MySQL
 Target Server Version : 80012
 File Encoding         : 65001

 Date: 26/12/2025 21:12:32
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for agenda_items
-- ----------------------------
DROP TABLE IF EXISTS `agenda_items`;
CREATE TABLE `agenda_items`  (
  `item_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '议程项目唯一标识',
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联线程ID',
  `question` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '议程问题',
  `priority` int(11) NULL DEFAULT 50 COMMENT '优先级',
  `status` enum('open','active','closed') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'open' COMMENT '状态',
  `created_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '组织者' COMMENT '创建者',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`item_id`) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  INDEX `idx_status`(`status` ASC) USING BTREE,
  CONSTRAINT `agenda_items_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '议程项目表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for comments
-- ----------------------------
DROP TABLE IF EXISTS `comments`;
CREATE TABLE `comments`  (
  `comment_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '评论唯一ID',
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联对话ID',
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '评论用户ID',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '评论内容',
  `is_deleted` tinyint(1) NULL DEFAULT 0 COMMENT '是否已删除',
  `is_violation` tinyint(1) NULL DEFAULT 0 COMMENT '是否违规',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`comment_id`) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  INDEX `idx_user_id`(`user_id` ASC) USING BTREE,
  INDEX `idx_created_at`(`created_at` ASC) USING BTREE,
  CONSTRAINT `fk_comment_thread` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_comment_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '对话评论表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for consensus
-- ----------------------------
DROP TABLE IF EXISTS `consensus`;
CREATE TABLE `consensus`  (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联线程ID',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '共识内容',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  CONSTRAINT `consensus_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 69 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '共识点表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for disagreements
-- ----------------------------
DROP TABLE IF EXISTS `disagreements`;
CREATE TABLE `disagreements`  (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联线程ID',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '争议内容',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  CONSTRAINT `disagreements_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 58 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '争议点表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for events
-- ----------------------------
DROP TABLE IF EXISTS `events`;
CREATE TABLE `events`  (
  `event_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '事件唯一标识',
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联线程ID',
  `speaker` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '发言者',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '发言内容',
  `turn_id` int(11) NOT NULL COMMENT '发言轮次',
  `tags` json NULL COMMENT '标签列表',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`event_id`) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  INDEX `idx_turn_id`(`thread_id` ASC, `turn_id` ASC) USING BTREE,
  CONSTRAINT `events_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '发言事件表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for forbidden_words
-- ----------------------------
DROP TABLE IF EXISTS `forbidden_words`;
CREATE TABLE `forbidden_words`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `word` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '违禁词',
  `created_by` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '创建者ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_word`(`word` ASC) USING BTREE,
  INDEX `idx_created_by`(`created_by` ASC) USING BTREE,
  CONSTRAINT `fk_forbidden_word_user` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '违禁词表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for moderation_logs
-- ----------------------------
DROP TABLE IF EXISTS `moderation_logs`;
CREATE TABLE `moderation_logs`  (
  `log_id` int(11) NOT NULL AUTO_INCREMENT,
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '对话ID',
  `moderator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '审核管理员ID',
  `action` enum('approve','reject') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '审核动作：通过/驳回',
  `reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '审核原因（驳回时必填）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '审核时间',
  PRIMARY KEY (`log_id`) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  INDEX `idx_moderator_id`(`moderator_id` ASC) USING BTREE,
  INDEX `idx_created_at`(`created_at` ASC) USING BTREE,
  CONSTRAINT `fk_mod_moderator` FOREIGN KEY (`moderator_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_mod_thread` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '审核日志表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for open_questions
-- ----------------------------
DROP TABLE IF EXISTS `open_questions`;
CREATE TABLE `open_questions`  (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联线程ID',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '问题内容',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  CONSTRAINT `open_questions_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 246 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '开放问题表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for style_health
-- ----------------------------
DROP TABLE IF EXISTS `style_health`;
CREATE TABLE `style_health`  (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联线程ID',
  `metric_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '指标名称',
  `count` int(11) NULL DEFAULT 0 COMMENT '计数',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_thread_metric`(`thread_id` ASC, `metric_name` ASC) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  CONSTRAINT `style_health_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 145 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '风格健康统计表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for thread_likes
-- ----------------------------
DROP TABLE IF EXISTS `thread_likes`;
CREATE TABLE `thread_likes`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '对话ID',
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '点赞用户ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_thread_user`(`thread_id` ASC, `user_id` ASC) USING BTREE COMMENT '同一用户对同一对话只能点赞一次',
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  INDEX `idx_user_id`(`user_id` ASC) USING BTREE,
  CONSTRAINT `fk_like_thread` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_like_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '对话点赞表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for thread_owners
-- ----------------------------
DROP TABLE IF EXISTS `thread_owners`;
CREATE TABLE `thread_owners`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '线程ID',
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '创建者用户ID（NULL表示游客创建）',
  `is_public` tinyint(1) NULL DEFAULT 0 COMMENT '是否公开分享',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `publication_status` enum('draft','pending','published','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'draft' COMMENT '发布状态：草稿/待审核/已公开/已驳回',
  `submitted_for_review_at` datetime NULL DEFAULT NULL COMMENT '提交审核时间',
  `reviewed_at` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `reviewed_by` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核管理员ID',
  `rejection_reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '驳回原因',
  `is_locked` tinyint(1) NULL DEFAULT 0 COMMENT '是否锁定（公开后不可继续对话）',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_user_id`(`user_id` ASC) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  INDEX `idx_is_public`(`is_public` ASC) USING BTREE,
  INDEX `idx_publication_status`(`publication_status` ASC) USING BTREE,
  INDEX `idx_reviewed_by`(`reviewed_by` ASC) USING BTREE,
  CONSTRAINT `thread_owners_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `thread_owners_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 30 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '对话所有者表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for threads
-- ----------------------------
DROP TABLE IF EXISTS `threads`;
CREATE TABLE `threads`  (
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '线程唯一标识',
  `topic` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '讨论话题',
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '创建用户ID（NULL表示游客）',
  `phase` enum('opening','discussion','closing') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'opening' COMMENT '讨论阶段',
  `turn_id` int(11) NULL DEFAULT 0 COMMENT '发言轮次',
  `last_speaker` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '最后发言者',
  `last_user_interjection` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '最后用户插话',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`thread_id`) USING BTREE,
  INDEX `idx_user_id`(`user_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '讨论线程表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_sessions
-- ----------------------------
DROP TABLE IF EXISTS `user_sessions`;
CREATE TABLE `user_sessions`  (
  `session_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '会话令牌',
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户ID',
  `refresh_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` timestamp NOT NULL COMMENT '过期时间',
  PRIMARY KEY (`session_id`) USING BTREE,
  INDEX `idx_user_id`(`user_id` ASC) USING BTREE,
  INDEX `idx_expires_at`(`expires_at` ASC) USING BTREE,
  CONSTRAINT `user_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户会话表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户唯一ID',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '邮箱',
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希',
  `avatar_url` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '头像URL',
  `is_active` tinyint(1) NULL DEFAULT 1 COMMENT '账户是否激活',
  `is_verified` tinyint(1) NULL DEFAULT 0 COMMENT '邮箱是否验证',
  `role` enum('guest','user','admin','super_admin') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'guest',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_login_at` timestamp NULL DEFAULT NULL,
  `is_banned` tinyint(1) NULL DEFAULT 0 COMMENT '是否被封禁',
  `banned_reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '封禁原因',
  `banned_at` datetime NULL DEFAULT NULL COMMENT '封禁时间',
  `banned_by` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '封禁执行者ID',
  PRIMARY KEY (`user_id`) USING BTREE,
  UNIQUE INDEX `username`(`username` ASC) USING BTREE,
  UNIQUE INDEX `email`(`email` ASC) USING BTREE,
  INDEX `idx_username`(`username` ASC) USING BTREE,
  INDEX `idx_email`(`email` ASC) USING BTREE,
  INDEX `idx_role`(`role` ASC) USING BTREE,
  INDEX `fk_banned_by`(`banned_by` ASC) USING BTREE,
  CONSTRAINT `fk_banned_by` FOREIGN KEY (`banned_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
