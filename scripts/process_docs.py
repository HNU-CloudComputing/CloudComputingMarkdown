import os
import re

def process_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复被错误转义的双引号
    content = content.replace(r'\"', '"')

    # 2. 清理各类无用标签、外壳和图片属性
    # 【核心修复】：彻底清理所有 Pandoc 产生的块级边界，绝不留患
    content = re.sub(r'^:::\s*[a-zA-Z0-9_\*]*\s*\n', '', content, flags=re.MULTILINE)
    
    content = re.sub(r'\s*\{#[^\}]+\}', '', content)
    content = re.sub(r'\{width=[^\}]+\}', '', content)

    # 清理交叉引用残留
    content = re.sub(r'\{reference-type="ref"[^\}]+\}', '', content)
    content = re.sub(r'\[\s*\]\(#[^\)]+\)', '', content)
    content = re.sub(r'\[(fig|tab|sec):[^\]]+\]', '', content)
    content = re.sub(r'如图\s+所示', '如图所示', content)
    content = re.sub(r'如表\s+所示', '如表所示', content)
    content = re.sub(r'附录\s+的', '附录中的', content)

    # 3. 智能区分代码块标题和表格标题
    # 【核心修复】：如果是 tcolorbox 产生的代码块标题，转为漂亮的加粗文字
    content = re.sub(r'^:\s+([^\n]+)\n+(?=```)', r'**\1**\n\n', content, flags=re.MULTILINE)
    
    # 剩下的才是真正的表格标题，严格限制冒号后面必须有空格，杜绝误伤
    def caption_replacer(match):
        caption_text = match.group(1).strip()
        return f'\n<center style="color: #888; font-size: 0.9em;">表：{caption_text}</center>\n'
    content = re.sub(r'^:\s+([^\n]+)$', caption_replacer, content, flags=re.MULTILINE)

    # 4. 修复代码块 (支持所有格式)
    content = re.sub(r'```[a-zA-Z0-9_-]*\s*\n(```[^\n]*\n.*?)\n```\s*\n```', r'\n\n\1\n```\n\n', content, flags=re.DOTALL)

    def code_replacer(match):
        attr, code = match.group(1), match.group(2)
        lang_match = re.search(r'language="?([a-zA-Z0-9_-]+)"?', attr)
        lang = lang_match.group(1) if lang_match else ""
        if not lang:
            class_match = re.search(r'\.([a-zA-Z0-9_-]+)', attr)
            lang = class_match.group(1) if class_match and 'numberLines' not in attr else ""
        return f"\n\n```{lang}\n{code}\n```\n\n"
    content = re.sub(r'```\s*[\{\[](.*?)[\}\]]\n(.*?)\n```', code_replacer, content, flags=re.DOTALL)

    def plaintext_code_replacer(match):
        lang = match.group(1)
        code = match.group(2).strip()
        return f"\n\n```{lang}\n{code}\n```\n\n"
    content = re.sub(r'^\[\s*[^\]]*language=([a-zA-Z0-9_-]+)[^\]]*\]\s*\n(.*?)(?=\n{2,}|\n:::|\Z)',
                     plaintext_code_replacer, content, flags=re.MULTILINE | re.DOTALL)

    # 5. 精准修复数学公式
    content = content.replace(r'\$', '___ESCAPED_DOLLAR___')
    def math_replacer(match):
        block_math, inline_math = match.group(1), match.group(2)
        if block_math is not None:
            return f"\n\n$$\n{block_math.strip()}\n$$\n\n"
        elif inline_math is not None:
            cleaned = inline_math.strip().replace('\n', ' ')
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return f"${cleaned}$"
    content = re.sub(r'\$\$(.*?)\$\$|\$([^\$]+?)\$', math_replacer, content, flags=re.DOTALL)
    content = content.replace('___ESCAPED_DOLLAR___', r'\$')

    # 6. 压缩多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    target_dir = "docs"
    print("🚀 开始执行云端 Markdown 深度清洗流水线...")
    if not os.path.exists(target_dir):
        print(f"⚠️ 未找到 {target_dir} 目录，请检查路径。")
        return

    count = 0
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".md"):
                process_markdown_file(os.path.join(root, file))
                print(f"  [✓] 成功处理: {file}")
                count += 1

    print(f"\n🎉 共清洗了 {count} 个文件。")

if __name__ == "__main__":
    main()