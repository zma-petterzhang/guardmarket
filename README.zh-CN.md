# GuardMarket：供 AI 调用的电商与数据技能

[English](README.md) · [125 个技能文档](https://zma-petterzhang.github.io/guardmarket/) · [安装包](https://github.com/zma-petterzhang/guardmarket/releases) · [MCP Registry 登记](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.zma-petterzhang%2Fguardmarket/versions/0.3.0) · [各客户端配置](examples/README.md)

本仓库提供独立 MCP 客户端、插件描述文件和 125 个真实实现技能的公开参数文档。技能覆盖电商计算、库存分析、CSV、JSON、文本、日期、数学、统计、编码、数据校验和单位换算。

**v0.3.0 已正式公开发布：**仓库、[安装包](https://github.com/zma-petterzhang/guardmarket/releases/tag/v0.3.0)和 130 页文档站均可访问。MCPB 安装包已于 2026-09-26 登记到 [MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.zma-petterzhang%2Fguardmarket/versions/0.3.0)，名称为 `io.github.zma-petterzhang/guardmarket`，当前状态为 `active`。这是安装包元数据登记；OpenAI、Claude 的插件目录审核仍需单独完成。

**执行服务、账号和计费由单独运行的 GuardMarket 后台提供。** 安装这个包不会自动获得服务器或钱包。公开文档站不能执行技能；这里也不宣称已发布 PyPI、已部署公网生产服务或已获得 GPT / Claude 目录审核。示例全部使用合成数据，不包含本机账号。

## 安装

**桌面安装包：**从 [v0.3.0 Release](https://github.com/zma-petterzhang/guardmarket/releases/tag/v0.3.0) 下载 `guardmarket-mcp-0.3.0.mcpb`，核对 `SHA256SUMS`，在支持 **MCPB 0.4 / uv 运行时**的客户端中打开。宿主会管理所需 Python；安装界面填写实际后台地址，消费 API Key 可留空以浏览技能。旧版 MCPB 客户端请用下面的 wheel / stdio 方式。安装包只包含接入客户端，不包含后台服务器。

需要 Python 3.11 及以上。客户端只使用 Python 标准库。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install "git+https://github.com/zma-petterzhang/guardmarket.git@v0.3.0"
.venv/bin/guardmarket-mcp --version
```

没有 Git 可以直接下载 [v0.3.0 的 wheel 安装包](https://github.com/zma-petterzhang/guardmarket/releases/tag/v0.3.0)，与同一版本的 `SHA256SUMS` 核对 SHA-256，再运行 `python -m pip install /安装包绝对路径/guardmarket_mcp-0.3.0-py3-none-any.whl`。Windows 的虚拟环境程序位于 `.venv\Scripts\`。

配置 `GUARDMARKET_URL` 为实际后台地址，例如本机 `http://127.0.0.1:8787`。公网只接受 HTTPS；HTTP 仅允许数字形式的回环地址，不允许跳转或代理转发凭据。

## 调用流程

1. `market.search` 搜索已发布技能，免费且无需 API Key。
2. `market.describe` 查看准确的技能 ID、版本、参数、输出、外部影响和当前价格。
3. `market.invoke` 在用户授权后调用，必须带 `max_price_micros` 价格上限和 `idempotency_key` 幂等键。
4. `market.wallet` 查看余额；`market.receipt` 查询自己的调用回执。

付费和账户查询功能需要后台账户创建的消费 API Key。通过 `GUARDMARKET_API_KEY` 环境变量提供，或在 macOS/Linux 用 `--key-file` 指向本人所有、权限为 `0600` 的普通文件。不要把密钥写入仓库或发送到聊天。

每 1 元等于 1,000,000 micros。目录中的 ¥0.01 是演示价格；实际价格、币种及测试/生产模式以后台返回为准。测试模式仅使用模拟资金。成功执行才结算；结果不确定时资金可能仍被预留。超时后只能用**原幂等键和完全相同的参数**重试。

## 常见用途

- 给定商品价格、数量、优惠和税率，计算购物车总额。
- 校验并归一化提供的商品、链接、邮箱和文本数据。
- 转换 CSV / JSON，转义电子表格公式。
- 根据提供的库存数据计算补货建议。
- 对提供的日期、数字和单位执行确定性计算。

技能不会自动获取实时税率、汇率或物流价格。原始 125 个技能只处理用户输入；第三方技能的网络访问或外部影响应先从 `market.describe` 中查看。

## 在 GPT、Claude、Qwen 中使用

[接入指南](examples/README.md) 包含 Claude Desktop / Code、Qwen Code / Agent、Codex 配置，以及便携插件和兼容描述文件。ChatGPT 或 Claude 网页端还需要公网 HTTPS MCP 服务及授权配置，不能把 GitHub 仓库网址当成执行接口。

公开仓库、独立技能页、站点地图和 `llms.txt` 可以提供可检索内容；MCP Registry 的有效记录让支持该注册表的工具目录可以获取安装信息。它们不保证搜索引擎收录、模型自动推荐或自动安装。OpenAI、Claude 插件目录还需要各自的发布者验证与平台审核。

[Registry 发布工作流已成功](https://github.com/zma-petterzhang/guardmarket/actions/runs/36233530790)，登记指向固定的 v0.3.0 安装包与校验和。后续 `main` 分支的文档更新不会替换已发布版本。

开发验证命令、发版流程和技术限制见 [English README](README.md)。
