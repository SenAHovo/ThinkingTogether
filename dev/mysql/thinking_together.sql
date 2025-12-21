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

 Date: 21/12/2025 15:42:47
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
-- Records of agenda_items
-- ----------------------------

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
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '共识点表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of consensus
-- ----------------------------

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
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '争议点表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of disagreements
-- ----------------------------

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
-- Records of events
-- ----------------------------
INSERT INTO `events` VALUES ('5908ab84a2384e2f8a85910cdf88d8ed', '9d3e1345671b', '用户', '为我讲解一下智能体开发', 1, '{\"tags\": [\"topic\"], \"metadata\": {\"timestamp\": \"2025-12-21T15:40:57.083085\", \"topic_count\": 0, \"action_count\": 0, \"speaker_type\": \"user\", \"has_consensus\": false, \"has_questions\": false, \"keyword_count\": 4, \"content_length\": 11, \"has_key_points\": false, \"question_count\": 0, \"consensus_count\": 0, \"key_point_count\": 0, \"primary_emotion\": \"中性\", \"complexity_score\": 0.003, \"has_action_items\": false, \"has_disagreement\": false, \"disagreement_count\": 0}}', '2025-12-21 15:40:57');
INSERT INTO `events` VALUES ('997107ac708d457eb6e5026260c9c1c2', '9d3e1345671b', '组织者', '现在大家都在说“智能体”，感觉它就像个能自己干活的小助手，但到底它到底是个啥？是未来要取代人的工具，还是只是个更聪明的工具？这事儿到底靠谱不靠谱？', 2, '{\"tags\": [\"opening\"], \"metadata\": {\"timestamp\": \"2025-12-21T15:41:11.624729\", \"topic_count\": 0, \"action_count\": 0, \"speaker_type\": \"organizer\", \"has_consensus\": false, \"has_questions\": true, \"keyword_count\": 10, \"content_length\": 73, \"has_key_points\": false, \"question_count\": 1, \"consensus_count\": 0, \"key_point_count\": 0, \"primary_emotion\": \"中性\", \"complexity_score\": 0.262, \"has_action_items\": false, \"has_disagreement\": false, \"disagreement_count\": 0}}', '2025-12-21 15:41:12');
INSERT INTO `events` VALUES ('fd63f323f46849ebbb67f5f41553f92e', '9d3e1345671b', '理论家', '在讨论智能体开发时，确实需要厘清“智能体”这一概念的边界条件。智能体通常被定义为能够自主感知环境、做出决策并采取行动的系统，而不仅仅是执行预设任务的工具。与聊天机器人等通用AI工具相比，智能体更强调自主性和适应性。关键变量在于智能体的学习能力和自我优化能力，这使其能够在复杂、动态的环境中不断调整策略，而不仅仅是根据固定算法回应用户。\n\n例如，聊天机器人一般是基于固定的对话模型，处理输入并生成输出，但它缺乏对环境变化的实时适应能力。相对而言，智能体可以通过不断的学习和反馈机制，逐步提升其决策能力和效率。这种能力的差异决定了智能体在实际应用中的灵活性和广泛性，尤其是在需要实时反应和复杂决策的场景中。', 3, '{\"tags\": [], \"metadata\": {\"timestamp\": \"2025-12-21T15:41:23.805053\", \"topic_count\": 2, \"action_count\": 0, \"speaker_type\": \"theorist\", \"has_consensus\": false, \"has_questions\": false, \"keyword_count\": 10, \"content_length\": 301, \"has_key_points\": false, \"question_count\": 0, \"consensus_count\": 0, \"key_point_count\": 0, \"primary_emotion\": \"消极\", \"complexity_score\": 0.23, \"has_action_items\": false, \"has_disagreement\": false, \"disagreement_count\": 0}}', '2025-12-21 15:41:24');

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
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '开放问题表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of open_questions
-- ----------------------------

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
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '风格健康统计表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of style_health
-- ----------------------------

-- ----------------------------
-- Table structure for threads
-- ----------------------------
DROP TABLE IF EXISTS `threads`;
CREATE TABLE `threads`  (
  `thread_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '线程唯一标识',
  `topic` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '讨论话题',
  `phase` enum('opening','discussion','closing') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'opening' COMMENT '讨论阶段',
  `turn_id` int(11) NULL DEFAULT 0 COMMENT '发言轮次',
  `last_speaker` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '最后发言者',
  `last_user_interjection` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '最后用户插话',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`thread_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '讨论线程表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of threads
-- ----------------------------
INSERT INTO `threads` VALUES ('9d3e1345671b', '为我讲解一下智能体开发', 'opening', 0, NULL, NULL, '2025-12-21 15:40:49', '2025-12-21 15:40:49');

SET FOREIGN_KEY_CHECKS = 1;
