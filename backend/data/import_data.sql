-- 导入公告数据
INSERT OR REPLACE INTO announcements (id, content, image_url, priority, is_active, start_time, end_time, created_at, updated_at, color, bold, title) VALUES
(1, '系统已于今日完成升级，新增公告功能、多用户API配置等多项功能，欢迎体验！', NULL, 1, 1, NULL, NULL, '2026-05-04 03:17:35', '2026-05-04 03:17:35', '#ef4444', 1, '系统升级通知'),
(2, '公告轮播功能上线，管理员可在后台发布公告，用户可在右上角查看最新公告。', NULL, 2, 1, NULL, NULL, '2026-05-04 03:17:35', '2026-05-04 03:17:35', '#3b82f6', 0, '新功能上线'),
(3, '尊敬的用户：

为进一步提升策略验证体验与实战参考价值，知行量化回测系统已完成重构升级，并正式上线。

本次升级围绕 系统核心性能 回测速度 回测与实盘一致性 进行了重点优化，新增支持 筛选器与交易配置回测，将原本仅在实盘生效的部分关键配置正式同步纳入回测流程，包括：

筛选器
最大持仓张数
最大订单数
自动平反向仓
是否反向开仓

在此前的使用过程中，由于上述配置仅支持实盘、不支持回测，部分策略可能出现 "回测有订单，实盘无订单" 的情况，影响用户对策略结果的判断。

本次升级后，回测结果将更贴近真实交易执行逻辑，进一步提升回测与实盘的一致性，帮助用户更准确地进行策略验证、参数筛选与实战判断。

感谢您一直以来对知行量化的支持与信任。
知行量化团队
2026年4月17日', NULL, 3, 1, NULL, NULL, '2026-05-04 03:17:35', '2026-05-04 03:56:44', '#22c55e', 1, '关于知行量化升级的公告');

-- 导入站点配置
INSERT OR REPLACE INTO site_configs (id, key, value, updated_at) VALUES
(1, 'activity_banner_url', '/static/uploads/activities/89eac663902e4c8a9ad7c0a645d5c675.jpg', '2026-05-04 12:27:36.168678'),
(2, 'site_name', '𝓧量化系统', '2026-05-04 12:02:14.620746'),
(3, 'site_slogan', 'AI驱动-重新定义量化交易', '2026-05-04 12:02:14.621186'),
(7, 'logo_url', '', '2026-05-04 12:02:14.635836'),
(8, 'allow_register', 'true', '2026-05-04 12:02:14.631991'),
(13, 'okx_register_url', 'https://www.baidu.com/', '2026-05-04 12:02:14.633777'),
(14, 'bitget_register_url', 'https://www.baidu.com/', '2026-05-04 12:02:14.634105'),
(15, 'htx_register_url', 'https://www.baidu.com/', '2026-05-04 12:02:14.634430'),
(18, 'site_logo', '/static/uploads/site-logo.jpg', '2026-05-04 13:41:44'),
(19, 'activity_banners', '[{"url": "/static/uploads/activities/70206adf8f204b1db4a44b49f3ba7f6b.jpg", "link": ""}, {"url": "/static/uploads/activities/cea78a0f6ff94159bcb7f368d0e3204b.jpg", "link": ""}]', '2026-05-08 03:12:50.495013');

-- 导入热门活动
INSERT OR REPLACE INTO hot_activities (id, display_order, icon_url, title, desc, status, badge, badge_type, is_active, created_at, updated_at) VALUES
(1, 1, '/static/uploads/activities/64375250991a40698abadbaf509e78b5.jpg', '新用户注册送体验金', '完成注册即送100U体验金，开启量化之旅', '进行中', 'HOT', 'hot', 1, '2026-04-30 08:18:26', '2026-05-08 03:12:50.495614'),
(2, 2, '/static/uploads/activities/d1674d0f9f5549d39874f669e2ad67bd.jpg', '邀请好友双赢奖励', '每邀请一位好友注册并绑定交易所，双方各得50U', '进行中', 'NEW', 'new', 1, '2026-04-30 08:18:26', '2026-05-08 03:12:50.496018'),
(3, 3, '/static/uploads/activities/61f9b4b3d7d4433ba61b43c0bfbfb142.jpg', '策略收益排行榜', '每周收益排名前10的用户额外奖励策略额度', '即将开始', '', 'none', 1, '2026-04-30 08:18:26', '2026-05-08 03:12:50.496459');
