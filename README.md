# AI 掘金头条课程复刻

本项目是下载源码与课程物料整合后的 AI 掘金头条独立运行版本，原本位于课程工作区的 `day06-00`。保留老师的 FastAPI 分层、Vue/Vant 页面和前端流式问答流程；模型默认配置为 DeepSeek，也保留课程千问入口。

仓库包含后端、前端、SQL 建表与课程初始数据、环境配置示例和启动脚本。首次克隆需要安装依赖、准备 MySQL/Redis 并初始化数据库；完成后可以通过 `Start.cmd` 启动。仓库不包含作者的 API Key、本机数据库密码或运行中的数据库实例。

## 已验证状态

2026-10-03 已完成前后端安装、独立 SQL 导入和运行联调：17 项后端回归测试、13 项前端回归测试、63 项真实 HTTP 断言通过，覆盖全部 17 个业务接口。浏览器已验证注册、登录、新闻分类与详情、相关推荐、收藏、历史、简介更新，以及 DeepSeek 真实流式回复。审查后的并发登录、并发历史写入和分类返回问题已专项验证。

页面已对照第三章第 30 页、第四章第 2 页、第五章第 2 页、第六章第 17 页的实际截图。保留课程主要布局与原始新闻素材；动态浏览量、账号信息、回复内容会变化，不声明与老师最终源码逐字一致。

## 首次克隆与运行（Windows）

以下命令在 PowerShell 中执行。项目启动脚本已在 Windows 验证；不要直接在 Linux/macOS 上执行这些 Windows 脚本。

### 1. 准备环境与服务

- Git：用于克隆源码。
- Python 3.11：本项目验证版本为 3.11.9。确认 `python --version` 指向 Python 3.11。
- Node.js 与 npm：本项目验证版本为 Node 24.13.0；锁定的 Vite 依赖要求 Node `^20.19.0 || >=22.12.0`。确认 `node --version`、`npm --version` 可执行。
- MySQL：准备可连接的实例，默认地址 `127.0.0.1:3306`。初始化账号须具备创建 `news_app_day06_00` 数据库、建表和写入数据的权限。
- Redis：准备可连接的本地实例，默认地址 `127.0.0.1:6379`、逻辑库 0。当前缓存客户端没有密码配置入口，按本地无密码实例配置。缓存键使用 `day06_00:` 前缀。

`Start.cmd` 只启动前后端，MySQL 和 Redis 需要提前启动。新闻数据使用 MySQL SQL，不能用 SQLite 文件替代。

### 2. 克隆并复制配置示例

```powershell
git clone https://github.com/xinshuoxinshuo11-netizen/fastapi-ai-news.git
cd fastapi-ai-news
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
```

如果仓库仍为私有，需要使用获授权的 GitHub 账号克隆。后续命令都从克隆得到的项目根目录执行。

打开根目录 `.env`，把 `DATABASE_URL` 中的用户名、密码改为你自己的 MySQL 凭据，数据库名保留为 `news_app_day06_00`。数据库尚不存在时，下一步初始化脚本会创建它。若密码包含 `@`、`:`、`/` 等 URL 特殊字符，需要对密码部分做 URL 编码。根据自己的 Redis 地址修改 `REDIS_HOST`、`REDIS_PORT`、`REDIS_DB`。

`frontend/.env.local` 默认连接本机后端 `http://127.0.0.1:19000`，使用 DeepSeek 端点和 `deepseek-chat`。先使用默认端口即可。

### 3. 安装依赖并初始化数据库

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe init_db.py
Set-Location frontend
npm ci
Set-Location ..
```

`init_db.py` 使用仓库中的 `sql/database.day06-00.sql`，首次导入应输出 **8 张表、8 个分类、403 条新闻、1 个用户**。这是课程初始数据，不是作者本机新增账号、收藏或历史的备份。初始化只允许使用 `news_app_day06_00`；已有表时跳过 SQL 导入，再检查和迁移唯一约束。具体规则见下方“数据与环境”。

不要导入 `sql/database.sql` 来替代这一步，它是保留的素材原件。前端使用 `npm ci` 安装锁定依赖，无需复制作者的 `node_modules`。

### 4. 配置自己的模型 Key（使用 AI 问答时）

如果只是查看新闻、注册登录、收藏和浏览历史，可以先跳过模型配置。AI 问答需要你自己的有效 Key：

```powershell
# 仅对当前 PowerShell 会话及其启动的子进程生效。
$env:DEEPSEEK_API_KEY = '填写你自己的 API Key'
.\Start.cmd
```

也可以在 Windows 用户环境变量中配置 `DEEPSEEK_API_KEY`，再启动项目；`Start.ps1` 会读取进程、用户、系统环境。修改模型配置或 Key 后，需要停止并重新启动服务。课程采用前端直连模型，运行时浏览器会收到你自己的 Key；详细边界见下方“模型配置”。

### 5. 打开页面确认

访问 [首页](http://127.0.0.1:5176) 和 [接口文档](http://127.0.0.1:19000/docs)。首次 SQL 导入后可以使用课程测试账号 `admin` / `123456` 登录，也可以注册自己的账号。尝试新闻分类、详情、收藏与历史；配置模型 Key 后再验证 AI 问答。

如果跳过模型配置，直接执行 `.\Start.cmd` 即可启动普通业务功能。

## 日常启动与停止

完成上述首次配置后，在项目根目录双击 **Start.cmd**，或在 PowerShell 中运行：

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

`sql/database.sql` 保留素材原件；`sql/database.day06-00.sql` 修改两处库名，并为令牌的用户 ID、历史的用户与新闻组合添加唯一约束。首次初始化为 8 张表、8 个分类、403 条新闻、1 个 admin 用户。验收产生的随机用户及浏览器专用注册用户已清理，admin 的测试收藏、历史和正常浏览量变化可供查看。

数据库与 Redis 配置在根目录 `.env`；前端配置在 `frontend/.env.local`。示例文件不包含真实密钥，新机器按上方“首次克隆与运行”配置自己的环境。

`init_db.py` 只允许初始化 `news_app_day06_00`；目标库已有表时跳过 SQL 导入，然后执行唯一约束迁移。旧数据库也可单独运行 `.\.venv\Scripts\python.exe migrate_constraints.py`。迁移若发现重复令牌或历史，会先备份到已被 Git 忽略的 `logs/`，再保留同组最新记录；时间相同时保留 ID 最大的一条。迁移前先停止本项目服务，完成后重新启动。部分导入或已有异常表结构需要人工核对，脚本不会自动清库。

## 模型配置

前端环境示例默认使用 DeepSeek 端点和 `deepseek-chat`。`Start.ps1` 会依次读取当前进程、用户环境、系统环境里的 `DEEPSEEK_API_KEY`，无须将密钥写入源码。作者本机已在浏览器发送测试问题并收到真实回复；克隆者需要用自己的账号配置再次验证。

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

## 首次运行常见问题

- **数据库连接失败或 `Access denied`**：确认 MySQL 已启动，`.env` 中的地址、账号、密码正确，账号具备所需权限。确认没有把示例中的“用户名”“密码”原样保留。
- **数据库不存在或缺表**：从项目根目录运行 `.\.venv\Scripts\python.exe init_db.py`；脚本不自动清空已存在的异常数据库，部分导入失败时需要先核对现有表。
- **Redis 连接失败**：确认 Redis 地址、端口和启动状态。新闻缓存操作失败时会回退到数据库查询，但不能据此认定缓存功能已验证。
- **找不到 Python/Node，或 Vite 提示版本不支持**：确认它们已加入 PATH，并符合上方版本条件；`.venv` 与 `frontend/node_modules` 需要在克隆者自己的电脑重新安装。
- **PowerShell 提示脚本被禁止执行**：双击 `Start.cmd` / `Stop.cmd`，它们会为本次脚本调用设置执行策略。
- **端口被占用或页面无法打开**：确认 `19000`、`5176` 没有被其他程序占用，查看 `logs/backend.err.log`、`logs/frontend.err.log`。后端与前端必须都启动。
- **AI 提示 Key 未配置或调用失败**：检查自己的环境变量、模型端点、模型名及账号调用权限；修改后停止并重新启动。模型请求由浏览器直接发起，网络或浏览器跨域限制也可能影响调用。

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
