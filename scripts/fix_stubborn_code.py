import os
import re

def fix_stubborn_code_blocks(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # ==========================================
    # 1. 彻底扒掉“俄罗斯套娃”的最外层
    # 无论内层是什么格式，只要被包在两个 ``` 里面，就把外层扒掉
    # ==========================================
    content = re.sub(
        r'```[a-zA-Z0-9_-]*\s*\n(```[^\n]*\n.*?)\n```\s*\n```',
        r'\1\n```',
        content,
        flags=re.DOTALL
    )

    # ==========================================
    # 2. 将 Pandoc 的复杂属性转换为标准的 Markdown 语言标记
    # 这次正则表达式直接匹配到行尾 ([^\n]+)，无视里面的 \color{gray} 大括号干扰
    # ==========================================
    def clean_pandoc_header(match):
        attr_line = match.group(1) # 例如: .numberLines .bash language="bash" ...
        code_body = match.group(2)
        
        # 尝试提取正确的编程语言名称
        lang = ""
        lang_match = re.search(r'language="([^"]+)"', attr_line)
        if lang_match:
            lang = lang_match.group(1)
        else:
            class_match = re.search(r'\.([a-zA-Z0-9_-]+)', attr_line)
            if class_match and class_match.group(1) != 'numberLines':
                lang = class_match.group(1)
                
        # 组装成纯净的代码块，例如 ```bash \n 代码内容 \n ```
        return f"```{lang}\n{code_body}\n```"

    content = re.sub(
        r'```\s*\{([^\n]+)\}\n(.*?)\n```',
        clean_pandoc_header,
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    target_dir = r".\\cloud-computing-book\\docs"
    
    print("开始精准清理顽固代码块...")
    count = 0
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                fix_stubborn_code_blocks(filepath)
                print(f"  [✓] 已修复: {file}")
                count += 1
                
    print(f"\n清理完成！共处理了 {count} 个文件。代码块终于清爽了！")

if __name__ == "__main__":
    main()