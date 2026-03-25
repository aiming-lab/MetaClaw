import os
import sys

def replace_in_file(file_path, old_str, new_str):
    """
    替换文件中的指定字符串
    
    Args:
        file_path: 文件路径
        old_str: 要替换的旧字符串
        new_str: 替换后的新字符串
    """
    try:
        # 以文本模式读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否需要替换
        if old_str not in content:
            print(f"[无需修改] {file_path}")
            return
        
        # 执行替换
        new_content = content.replace(old_str, new_str)
        
        # 覆盖写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"[已修改] {file_path}")
    
    except Exception as e:
        print(f"[处理失败] {file_path}: {str(e)}")

def find_and_replace_recursive(root_dir, old_str, new_str):
    """
    递归查找指定目录下的questions.json文件并替换字符串
    
    Args:
        root_dir: 根目录路径
        old_str: 要替换的旧字符串
        new_str: 替换后的新字符串
    """
    # 遍历目录树
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            # 筛选questions.json文件
            if filename == 'questions.json':
                file_path = os.path.join(dirpath, filename)
                replace_in_file(file_path, old_str, new_str)

if __name__ == "__main__":
    # 定义要替换的字符串
    OLD_STRING = "eval/scripts/check"
    NEW_STRING = "scripts/check"
    
    # 获取目标目录（支持命令行参数，默认当前目录）
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = os.getcwd()
    
    # 验证目录是否存在
    if not os.path.isdir(target_dir):
        print(f"错误：目录 '{target_dir}' 不存在！")
        sys.exit(1)
    
    print(f"开始递归处理目录：{target_dir}")
    print(f"替换内容：'{OLD_STRING}' -> '{NEW_STRING}'")
    print("-" * 50)
    
    # 执行递归查找和替换
    find_and_replace_recursive(target_dir, OLD_STRING, NEW_STRING)
    
    print("-" * 50)
    print("处理完成！")