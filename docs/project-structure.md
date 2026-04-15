# Project Structure

AITrader 现已引入 `src/aitrader` 分层结构：

- `src/aitrader/app`: CLI、use case、应用服务
- `src/aitrader/domain`: 领域模型与业务规则落点
- `src/aitrader/infrastructure`: 数据库、市场数据、配置、仓储
- `src/aitrader/interfaces`: FastAPI、Web 入口、请求响应模型
- `src/aitrader/shared`: 通用工具

兼容性说明：

- 原有根目录脚本暂时保留，便于渐进迁移
- Web 入口统一到 `aitrader.interfaces.api.main:app`
- `web/` 下原有入口与路由文件保留为兼容导出
- 后续可继续把 `core/`、`database/`、`datafeed/` 里的实现逐步迁入 `src/aitrader`
