# 每日CS预印本推送工具

- 爬取 arXiv 与 OpenReview 最新计算机相关预印本
- 按 CCF 推荐分类进行方向归类
- 总结摘要、改进方法/算法、实验效果（DeepSeek API 可选）
- 如检测到在审，列出会议名称与对应 CCF 等级
- 本地每日推送：用户选择兴趣领域（≤5），每日推送 5–10 篇

## 运行
1. 安装依赖：
```
pip install -r requirements.txt
```
2. 可选：设置 DeepSeek 虚拟 KEY（用于摘要结构化增强）：
```
set DEEPSEEK_API_KEY=sk-your-virtual-key
```
3. 选择兴趣方向并生成一次报告：
```
python main.py --areas "人工智能,计算机网络" --max 8 --out daily_report.html
```
生成文件：`daily_report.html`

## 说明
- arXiv 使用 Atom API（export.arxiv.org/api/query）进行检索与解析
- OpenReview 用于补充会议信息；默认仅解析 arXiv 评论中的“在审/投稿至”提示
- CCF 映射文件：getnewcspapers/venue/ccf_venues.json
- 分类 taxonomy：getnewcspapers/config/ccf_taxonomy.yaml
 
## Web 与 Docker
1. 启动 Web 服务：
```
uvicorn getnewcspapers.webapp.app:app --host 0.0.0.0 --port 8000
```
访问：http://localhost:8000/ ，管理员默认账号与密码：admin / admin

2. 开启邮件推送：
- 请直接修改代码文件 `getnewcspapers/delivery/emailer.py` 中的 `SMTP_CONFIG` 字典配置您的邮箱信息（Host, Port, User, Password 等）。
- 配置完成后，如果使用 Docker，需要重新构建镜像：
  ```
  docker build -t getnewcspapers:v2 .
  ```

3. Docker 运行：
```
docker run -d -p 8000:8000 --name getnewcspapers_v2 getnewcspapers:v2
```
应用：http://localhost:8000/

SMTP 示例（QQ邮箱）：
在 `emailer.py` 中配置：
```python
SMTP_CONFIG = {
    "SMTP_HOST": "smtp.qq.com",
    "SMTP_PORT": 465,
    "SMTP_USER": "你的QQ号@qq.com",
    "SMTP_PASS": "你的QQ邮箱授权码",
    "SMTP_SSL": True,
    "SMTP_STARTTLS": False, # SSL开启时通常不需要STARTTLS
    # ...
}
```

4. DeepSeek API 调用位置与接口：getnewcspapers/summarize/llm_summarizer.py，OpenAI 兼容 ChatCompletions，模型 deepseek-chat
5. 推送排序规则：先按 CCF 等级 A/B/C，再按发表时间越早越先
