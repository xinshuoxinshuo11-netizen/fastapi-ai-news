# AI 掘金头条课程复刻

本目录 `day06-00` 是下载源码与课程物料整合后的独立运行版本。保留老师的 FastAPI 分层、Vue/Vant 页面和前端流式问答流程；本机问答使用用户环境中的 DeepSeek 配置，千问入口保留。

## 已验证状态

2026-10-03 已完成前后端安装、独立 SQL 导入和运行联调：13 项后端回归测试、6 项前端回归测试、60 项真实 HTTP 断言通过，覆盖全部 17 个业务接口。浏览器已验证注册、登录、新闻分类与详情、相关推荐、收藏、历史、简介更新，以及 DeepSeek 真实流式回复。

页面已对照第三章第 30 页、第四章第 2 页、第五章第 2 页、第六章第 17 页的实际截图。保留课程主要布局与原始新闻素材；动态浏览量、账号信息、回复内容会变化，不声明与老师最终源码逐字一致。

## 直接运行

本机依赖与数据库已经准备好。在项目根目录双击 **Start.cmd**，或在 PowerShell 中运行：

```powershell
.\Start.ps1
```

- 首页：[http://127.0.0.1:5176](http://127.0.0.1:5176)
- 接口文档：[http://127.0.0.1:19000/docs](http://127.0.0.1:19000/docs)
- 课程测试账号：`admin`，密码：`123456`。已实际登录验证。
- 停止服务：双击 `Stop.cmd` 或执行 `.\Stop.ps1`。只停止本项目启动记录对应的进程树，核对进程创建时间以避免误停复用 PID。

启动脚本会核对端口就绪；重复启动本项目会跳过，其他程序占用目标端口则报错。后台日志位于 `logs/`。无需启动旧 `day06`。

## 数据与环境

- 后端专用 Python 环境：`.venv/`；本机 Python 3.11.9。
- 前端专用依赖：`frontend/node_modules/`；本机 Node 24.13.0。
- MySQL：`127.0.0.1:3306`，库 `news_app_day06_00`。
- Redis：`127.0.0.1:6379`，逻辑库 0，键前缀 `day06_00:`。
- MySQL、Redis 使用本机已有服务；本项目的运行不依赖旧项目新闻库。

`sql/database.sql` 保留素材原件；`sql/database.day06-00.sql` 只改两处建库和选库名称。首次初始化为 8 张表、8 个分类、403 条新闻、1 个 admin 用户。验收产生的随机用户及浏览器专用注册用户已清理，admin 的测试收藏、历史和正常浏览量变化可供查看。

数据库与 Redis 配置在根目录 `.env`；前端配置在 `frontend/.env.local`。示例文件不包含真实密钥。若重建到另一台机器，先安装 MySQL、Redis、Python、Node，并填写自己的连接配置，再执行：

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
# 安装前先编辑上述两个本机配置文件，填写自己的连接配置。
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe init_db.py
cd frontend
npm ci
cd ..
.\Start.ps1
```

`init_db.py` 只允许初始化 `news_app_day06_00`；目标库已有表时跳过导入，不覆盖已有数据。部分导入或已有异常表结构需要人工核对，脚本不会自动清库。

## 模型配置

当前 `frontend/.env.local` 使用 DeepSeek 端点和 `deepseek-chat`。`Start.ps1` 会依次读取当前进程、用户环境、系统环境里的 `DEEPSEEK_API_KEY`，无须将密钥写入源码。已在浏览器发送测试问题并收到真实回复。

切回课程千问时，修改前端本机配置，再停止、重新启动服务：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:19000
VITE_AI_API_ENDPOINT=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
VITE_AI_MODEL=qwen-plus
```

再在本机环境配置自己的 `DASHSCOPE_API_KEY` 或 `QWEN_API_KEY`，端点须匹配账号地区。北京兼容端点与模型示例依据[阿里云模型调用文档](https://www.alibabacloud.com/help/en/model-studio/model-calling-in-sub-workspace)。本轮没有使用千问 Key 发起真实请求；素材中的预览模型名称不作为实时可用性承诺。

课程采用前端直接调用模型，运行时浏览器可以看到 Key；本版本保留这一教学方式，仅用于本机练习。当前源码与本次无 Key 构建产物检查均未包含真实 Key。不要把带 Key 的前端运行包作为公开网站发布。

## 上传 GitHub 与密钥边界

本地 Git 仓库只提交源码、课程 SQL、无密钥的环境示例、文档和测试。`.gitignore` 排除所有 `.env*` 本机配置（保留 `.env.example`）、`dist/`、依赖、日志及临时目录。使用 Git 提交和推送本仓库，不要将整个目录通过网页逐个上传；不要强制添加已忽略的文件。

其他人克隆后，需复制环境示例并配置自己的数据库凭据、模型环境变量。`Start.ps1` 读取的是运行者所在电脑的进程、用户或系统环境，仓库不会提供你的 API Key，也无法读取你电脑的环境变量。

课程保留前端直连模型方式：运行时浏览器仍可看到运行者自己的 Key；带 Key 构建的产物也可能包含它。因此构建目录不提交，公开部署时应改为后端调用模型。

## 重跑验收

先启动服务，在根目录运行：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B -X utf8 verify_runtime.py
cd frontend
npm test
npm run build
```

单元测试只使用内存数据库或内存状态。`verify_runtime.py` 会操作独立课程库，创建并清理专用测试用户，详情访问会正常增加浏览量；它不调用模型，也不清空其他数据库或 Redis。

## 课程说明与验收证据

1. [目录与数据隔离方案](docs/01-复刻目录与数据隔离方案.md)
2. [最小调整与验收清单](docs/02-最小调整与验收清单.md)
3. [课程与源码对应关系](docs/03-课程与源码对应关系.md)
4. [运行与验收记录](docs/04-运行与验收记录.md)：修正、测试命令、PDF 对照、截图和边界。

SQL 的 `related_news` 和 `ai_chat` 表随课程素材保留；当前推荐仍查询同分类新闻，聊天不写入数据库。收藏和历史页面沿用课程的第一页展示，接口支持分页。消息通知菜单是原素材的占位入口。修改密码沿用课程的令牌生命周期，不增加撤销旧令牌扩展。

部分新闻图片使用素材中的外链，网络不通或图源失效时可能显示加载失败；课件示例中也存在破图，未用虚构图片替换。素材新闻用于课程练习，不作为实时新闻真实性核验结果。
