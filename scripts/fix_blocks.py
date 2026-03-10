import os
import re

def fix_markdown_formatting(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复嵌套的“俄罗斯套娃”代码块 (上一个脚本的后遗症)
    # 将 ```json \n ``` {.go ...} \n code \n ``` \n ``` 剥离成干净的 ```go \n code \n ```
    nested_code_pattern = re.compile(r'```json\n```\s*\{\.?([a-zA-Z0-9_\-]+)[^\}]*\}\n(.*?)\n```\n```', re.DOTALL)
    content = nested_code_pattern.sub(r'```\1\n\2\n```', content)

    # 2. 修复纯 Pandoc 格式的代码块
    # 将 ``` {.go style="codeblock" language="go"} 转换为标准 ```go
    pandoc_code_pattern = re.compile(r'```\s*\{\.?([a-zA-Z0-9_\-]+)[^\}]*\}\n(.*?)\n```', re.DOTALL)
    content = pandoc_code_pattern.sub(r'```\1\n\2\n```', content)

    # 3. 再次深度清理可能残留的交叉引用标签 (防止漏网之鱼)
    content = re.sub(r'\{reference-type="ref"[^\}]+\}', '', content)
    content = re.sub(r'(#+.*?)\s+\{#[^\}]+\}', r'\1', content)

    # 4. 修复图片路径 (确保都是 /)
    def fix_slash(match):
        alt = match.group(1)
        path = match.group(2).replace('\\', '/')
        return f'![{alt}]({path})'
    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', fix_slash, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    target_dir = r".\\cloud-computing-book\\docs"
    
    print("开始修复代码块和排版...")
    count = 0
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                fix_markdown_formatting(filepath)
                print(f"  [✓] 已修复: {file}")
                count += 1
                
    print(f"\n修复完成！共处理了 {count} 个文件。请刷新网页查看效果！")

if __name__ == "__main__":
    main()