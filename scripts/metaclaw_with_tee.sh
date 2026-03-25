#!/bin/bash

clear

# ===================== 核心配置（改这里就行）=====================
# 定义你要生成的日志文件路径（和tee配合的目标日志）
LOG_FILE="/home/xkaiwen/workspace/metaclaw-test/logs/run_logs/run.log"
# =================================================================

# 检查日志文件路径是否为空
if [ -z "$LOG_FILE" ]; then
    echo "错误：请先设置 LOG_FILE 变量指定日志文件路径！"
    exit 1
fi

# 拆分目录和文件名（分离路径和文件名，方便创建父目录+生成_n后缀）
dir_path=$(dirname "$LOG_FILE")
file_name=$(basename "$LOG_FILE")

# 拆分文件名和扩展名（处理带后缀的文件，比如 app.log 拆成 app + .log）
file_base="${file_name%.*}"   # 文件名主体（无扩展名）
file_ext="${file_name#$file_base}"  # 扩展名（包含.，无扩展则为空）

# 第一步：创建父目录（如果不存在）
if ! mkdir -p "$dir_path"; then
    echo "错误：无法创建父目录 $dir_path"
    exit 1
fi

# 第二步：循环查找不存在的_n后缀文件名
final_log_file="$LOG_FILE"
n=1
while [ -e "$final_log_file" ]; do
    final_log_file="${dir_path}/${file_base}_${n}${file_ext}"
    n=$((n + 1))
done

# ===================== 核心计时逻辑 =====================
# 记录开始时间（纳秒级，避免秒级精度不够）
start_time=$(date +%s%N)

# ===================== 可选：直接整合tee命令（一键使用）=====================
# 把下面的 your_command 替换成你要执行的实际命令（比如 python app.py、./run.sh 等）

# source /home/xkaiwen/workspace/utils/apikey/unc_gpt.sh

/home/xkaiwen/miniconda3/envs/metaclaw/bin/metaclaw start 2>&1 | tee -a "$final_log_file"

# 记录结束时间，计算耗时（转成秒，保留3位小数）
end_time=$(date +%s%N)
elapsed_time=$(echo "scale=3; ($end_time - $start_time) / 1000000000" | bc)

# ===================== 写入计时结果到日志末尾 =====================
# 格式化计时信息，追加到日志文件
{
    echo ""
    echo "----------------------------------------"
    echo "命令执行完成！"
    echo "开始时间：$(date -d @$(echo "$start_time / 1000000000" | bc) '+%Y-%m-%d %H:%M:%S')"
    echo "结束时间：$(date -d @$(echo "$end_time / 1000000000" | bc) '+%Y-%m-%d %H:%M:%S')"
    echo "总耗时：${elapsed_time} 秒"
    echo "========================================"
    echo ""
} >> "$final_log_file"

# 终端也输出计时结果（可选，方便直观看到）
echo "----------------------------------------"
echo "命令执行完成！总耗时：${elapsed_time} 秒"
echo "全部信息已写入日志文件：$final_log_file"