import os
import re

def clean_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 拔除标题末尾的锚点 {#id}
    # 例如：### 从网络游戏到在线系统工程 {#subsubsec:从网络游戏到云计算项目} -> ### 从网络游戏到在线系统工程
    content = re.sub(r'(#+.*?)\s+\{#[^}]+\}', r'\1', content)

    # 2. 清除正文中的交叉引用残留 {reference-type="ref" ...}
    # 例如：如图 [1](#fig:chapter1-fig5){reference-type="ref"...} 所示 -> 如图 [1](#fig:chapter1-fig5) 所示
    content = re.sub(r'\{reference-type="ref"[^}]+\}', '', content)

    # 3. 将 Pandoc 的 HTML <figure> 图片框转换为干净的标准 Markdown 语法
    # 提取 src 和 figcaption，变成 ![图注](图片路径)
    figure_pattern = re.compile(
        r'<figure[^>]*>\s*<img\s+src="([^"]+)"[^>]*/>\s*<figcaption>(.*?)</figcaption>\s*</figure>',
        re.IGNORECASE | re.DOTALL
    )
    content = figure_pattern.sub(r'![\2](\1)', content)

    # 4. 将 ::: tcolorbox 转换为标准的 Markdown 代码块
    # 因为您的示例中 tcolorbox 里装的是 JSON，所以这里自动标记为 json 语言
    tcolorbox_pattern = re.compile(r':::\s*tcolorbox\s*(.*?)\s*:::', re.DOTALL)
    content = tcolorbox_pattern.sub(r'```json\n\1\n```', content)

    # 5. 确保所有 Markdown 图片的路径使用的是正斜杠 (/)
    def fix_slash(match):
        alt = match.group(1)
        path = match.group(2).replace('\\', '/')
        return f'![{alt}]({path})'
    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', fix_slash, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    # 指向您 MkDocs 项目的 docs 文件夹
    target_dir = r".\\cloud-computing-book\\docs"
    
    print("开始清洗 Markdown 文件...")
    count = 0
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                clean_markdown_file(filepath)
                print(f"  [✓] 已修复: {file}")
                count += 1
                
    print(f"\n清洗完成！共处理了 {count} 个文件。现在您可以运行 mkdocs serve 预览了。")

if __name__ == "__main__":
    main()