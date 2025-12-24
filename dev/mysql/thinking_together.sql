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

 Date: 24/12/2025 15:17:27
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
) ENGINE = InnoDB AUTO_INCREMENT = 35 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '共识点表' ROW_FORMAT = Dynamic;

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
) ENGINE = InnoDB AUTO_INCREMENT = 16 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '争议点表' ROW_FORMAT = Dynamic;

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
) ENGINE = InnoDB AUTO_INCREMENT = 112 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '开放问题表' ROW_FORMAT = Dynamic;

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
) ENGINE = InnoDB AUTO_INCREMENT = 58 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '风格健康统计表' ROW_FORMAT = Dynamic;

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
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_user_id`(`user_id` ASC) USING BTREE,
  INDEX `idx_thread_id`(`thread_id` ASC) USING BTREE,
  INDEX `idx_is_public`(`is_public` ASC) USING BTREE,
  CONSTRAINT `thread_owners_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`thread_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `thread_owners_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '对话所有者表' ROW_FORMAT = Dynamic;

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
  `refresh_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '刷新令牌',
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
  `avatar_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '头像URL',
  `is_active` tinyint(1) NULL DEFAULT 1 COMMENT '账户是否激活',
  `is_verified` tinyint(1) NULL DEFAULT 0 COMMENT '邮箱是否验证',
  `role` enum('guest','user','admin') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'guest' COMMENT '用户角色：guest-游客, user-普通用户,           \r\n  admin-管理员',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_login_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`user_id`) USING BTREE,
  UNIQUE INDEX `username`(`username` ASC) USING BTREE,
  UNIQUE INDEX `email`(`email` ASC) USING BTREE,
  INDEX `idx_username`(`username` ASC) USING BTREE,
  INDEX `idx_email`(`email` ASC) USING BTREE,
  INDEX `idx_role`(`role` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
