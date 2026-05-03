
# hmv-stats-scraper

用于抓取 HackMyVM 成就数据并保存为 CSV 文件。

## 使用方法

1. 安装依赖：
	```bash
	pip install -r requirements.txt
	```

2. 运行脚本：
	```bash
	python scraper.py
	```
   
	可选参数：
	- `--start` 指定起始ID
	- `--output` 指定输出CSV路径（默认：data/achievements.csv）
	- `--empty-limit` 连续空页面停止（默认：3）
	- `-v` 显示详细信息

## 用途

- 自动化收集 HackMyVM 成就信息
- 可集成到 GitHub Action 定时任务

## 结果文件

- 数据保存于 `data/achievements.csv`
