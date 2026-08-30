import os
import re
import html
import yaml

CCBOOK_PATH = "latex_source"
MAIN_TEX = os.path.join(CCBOOK_PATH, "main.tex")
DOCS_DIR = "docs"
MKDOCS_YML = "mkdocs.yml"
TITLE_PATTERN = re.compile(r'\\(?:chapter|section)\*?\{([^}]+)\}')
BOOK_TITLE = "云计算原理与实践：以在线游戏为载体"
LICENSE_URL = "https://github.com/HNU-CloudComputing/CloudComputingMarkdown/blob/main/LICENSE"

def normalize_figures(content):
    """把 Pandoc 的独立图片统一转换为带编号、锚点和可见图注的 HTML figure。"""
    markdown_figure = re.compile(
        r'^!\[(.*?)\]\((\S+?)(?:\s+"[^"]*")?\)(?:\s*\{([^}\n]*)\})?[ \t]*$',
        flags=re.MULTILINE
    )

    def markdown_figure_replacer(match):
        caption = match.group(1).strip()
        src = html.escape(match.group(2), quote=True)
        attrs = match.group(3) or ""
        id_match = re.search(r'(?:^|\s)#([^\s]+)', attrs)
        figure_id = f' id="{html.escape(id_match.group(1), quote=True)}"' if id_match else ""
        escaped_caption = html.escape(caption)
        return (
            f'<figure{figure_id}>\n'
            f'<img src="{src}" alt="{escaped_caption}" style="max-width:100%; height:auto;" />\n'
            f'<figcaption>{escaped_caption}</figcaption>\n'
            f'</figure>'
        )

    content = markdown_figure.sub(markdown_figure_replacer, content)

    html_figure = re.compile(
        r'<figure\b([^>]*)>\s*(<img\b[^>]*?/?>)\s*<figcaption>(.*?)</figcaption>\s*</figure>',
        flags=re.DOTALL | re.IGNORECASE
    )
    figure_number = 0

    def html_figure_replacer(match):
        nonlocal figure_number
        figure_number += 1
        attrs, image, caption = match.groups()
        caption = re.sub(r'^图\s*\d+\s*[：:]\s*', '', caption.strip())
        return (
            f'<figure{attrs}>\n'
            f'{image}\n'
            f'<figcaption>图 {figure_number}：{caption}</figcaption>\n'
            f'</figure>'
        )

    return html_figure.sub(html_figure_replacer, content)

# ==========================================
# 1. 深度清洗 Markdown 文件
# ==========================================
def process_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    source_heading_count = len(re.findall(r'^#{1,6}\s+', content, flags=re.MULTILINE))

    # 1. 修复被错误转义的双引号与反斜杠空格
    content = content.replace(r'\"', '"')
    content = content.replace(r'\ ', ' ')

    # 2. 核心修复：将 Pandoc 转换出来的 pseudocodebox / 伪代码环境转换为标准代码块
    # 匹配模式形如：::: pseudocodebox 或包含标题的伪代码容器
    def pseudocode_replacer(match):
        title = match.group(1).strip() if match.group(1) else ""
        code = match.group(2).strip()
        header = f"**{title}**\n\n" if title else ""
        return f"\n\n{header}```go\n{code}\n```\n\n"

    content = re.sub(
        r':::\s*(?:\{[^}]*\}|pseudocodebox)\s*(?:\{([^}]*)\})?\s*\n(.*?)\n:::',
        pseudocode_replacer,
        content,
        flags=re.DOTALL
    )

    # 统一 Pandoc 不同版本产生的图片结构，保留图编号、锚点和可见图注。
    content = normalize_figures(content)

    # 3. 彻底清理其他残留的 Pandoc Div 边界 (:::)
    content = re.sub(r'^:::.*$', '', content, flags=re.MULTILINE)

    # 4. 清理各类无用标签、外壳、图片属性以及 HTML 乱码
    # Pandoc 会把独立 LaTeX label 转成 []{#label ...}。保留为不可见锚点，
    # 避免通用属性清理只删掉 {#...} 后在页面留下可见的 []。
    content = re.sub(
        r'\[\s*\]\s*\{#([^\s}]+)[^}]*\}',
        lambda match: f'<span id="{html.escape(match.group(1), quote=True)}"></span>',
        content
    )
    content = re.sub(r'\s*\{#[^\}]+\}', '', content)
    content = re.sub(r'\{width=[^\}]+\}', '', content)
    content = re.sub(r'\s*\{=html\}', '', content)
    content = re.sub(r'\{reference-type="ref"[^\}]+\}', '', content)
    content = re.sub(r'\[\s*\]\(#[^\)]+\)', '', content)
    content = re.sub(r'\[(fig|tab|sec):[^\]]+\]', '', content)
    content = re.sub(r'如图\s+所示', '如图所示', content)
    content = re.sub(r'如表\s+所示', '如表所示', content)
    content = re.sub(r'附录\s+的', '附录中的', content)

    # 5. 智能区分代码块标题和表格标题
    content = re.sub(r'^:\s+([^\n]+)\n+(?=```)', r'**\1**\n\n', content, flags=re.MULTILINE)
    def caption_replacer(match):
        caption_text = match.group(1).strip()
        return f'\n\n<center style="color: #888; font-size: 0.9em;">表：{caption_text}</center>\n\n'
    content = re.sub(r'^:\s+([^\n]+)$', caption_replacer, content, flags=re.MULTILINE)

    # 6. 修复标准代码块
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

    # 7. 表格强制隔离
    def table_padder(match):
        return f"\n\n{match.group(1)}\n\n"
    content = re.sub(r'(^\|[^\n]*(?:\n\|[^\n]*)*)', table_padder, content, flags=re.MULTILINE)

    # 8. 只在普通正文中修复数学公式，避免把代码里的 SQL 占位符（如 $1）
    #    或 shell 变量误判为公式边界。行内公式不得跨行。
    def normalize_math(text):
        text = text.replace(r'\$', '___ESCAPED_DOLLAR___')

        def block_math_replacer(match):
            return f"\n\n$$\n{match.group(1).strip()}\n$$\n\n"

        def inline_math_replacer(match):
            cleaned = re.sub(r'\s+', ' ', match.group(1).strip())
            return f"${cleaned}$"

        text = re.sub(r'\$\$(.*?)\$\$', block_math_replacer, text, flags=re.DOTALL)
        text = re.sub(r'(?<!\$)\$([^\n\$]+?)\$(?!\$)', inline_math_replacer, text)
        return text.replace('___ESCAPED_DOLLAR___', r'\$')

    fenced_code = re.compile(r'(^```[^\n]*\n.*?^```[ \t]*$)', flags=re.MULTILINE | re.DOTALL)
    content_parts = fenced_code.split(content)
    content = ''.join(
        part if index % 2 else normalize_math(part)
        for index, part in enumerate(content_parts)
    )

    # 9. 修复图片路径与压缩空行
    content = content.replace("figures/figures/", "figures/")
    content = re.sub(r'\n{3,}', '\n\n', content)

    processed_heading_count = len(re.findall(r'^#{1,6}\s+', content, flags=re.MULTILINE))
    if processed_heading_count != source_heading_count:
        raise ValueError(
            f"标题数量在清洗过程中发生变化：{filepath} "
            f"({source_heading_count} -> {processed_heading_count})"
        )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# ==========================================
# 2. 动态解析 LaTeX 结构与标题 (导航精简短标题)
# ==========================================
def parse_structure():
    if not os.path.exists(MAIN_TEX):
        return [], []
    
    with open(MAIN_TEX, "r", encoding="utf-8") as f:
        main_content = f.read()

    inputs = re.findall(r'\\input\{([^}]+)\}', main_content)
    chapters, appendices = [], []
    cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    
    for item in inputs:
        item = item.strip()
        if "preamble" in item:
            continue
            
        tex_rel = item if item.endswith(".tex") else f"{item}.tex"
        tex_full = os.path.join(CCBOOK_PATH, tex_rel)
        
        if os.path.exists(tex_full):
            with open(tex_full, "r", encoding="utf-8") as tf:
                content = tf.read()
                match = TITLE_PATTERN.search(content)
                raw_title = match.group(1).strip() if match else os.path.splitext(os.path.basename(item))[0]
                clean_title = re.sub(r'\\[a-zA-Z]+(\{[^}]*\})?', '', raw_title).replace('\\', ' ').strip()
                clean_title = re.sub(r'\s+', ' ', clean_title)
                
                base_name = os.path.splitext(os.path.basename(item))[0]
                md_target = f"{base_name}.md"

                if "intro" in base_name.lower():
                    short_title = "前言"
                elif "sec" in base_name.lower():
                    num_match = re.search(r'\d+', base_name)
                    if num_match:
                        idx = int(num_match.group(0)) - 1
                        cn = cn_nums[idx] if idx < len(cn_nums) else str(idx + 1)
                        short_title = f"第{cn}章"
                    else:
                        short_title = clean_title.split()[0]
                elif "appendix" in base_name.lower():
                    app_letter = base_name.replace("Appendix", "").replace("appendix", "")
                    short_title = f"附录 {app_letter}" if app_letter else "附录"
                else:
                    short_title = clean_title.split()[0]
                
                info = {
                    "full_title": clean_title,
                    "short_title": short_title,
                    "file": md_target
                }
                if "appendix" in item.lower():
                    appendices.append(info)
                else:
                    chapters.append(info)
                    
    return chapters, appendices

# ==========================================
# 3. 动态更新 docs/index.md 与 mkdocs.yml 的 nav
# ==========================================
def update_index_and_nav(chapters, appendices):
    index_content = f"# ☁️ {BOOK_TITLE}\n\n"
    index_content += "这是由 **GuoLab** 倾力编写的教科书在线阅读版。以下为最新章节导航：\n\n"
    index_content += "### 📖 章节目录\n\n"
    for ch in chapters:
        index_content += f"- [**{ch['full_title']}**]({ch['file']})\n"
    
    if appendices:
        index_content += "\n### 📑 附录内容\n\n"
        for ap in appendices:
            index_content += f"- [**{ap['full_title']}**]({ap['file']})\n"

    index_content += """

## 编者信息

- **核心编者与架构设计：** [陈果](https://grzy.hnu.edu.cn/site/index/chenguo)、徐方林、胡文举、庞海鑫、谢先衍、贺臻、张道平
- **所属单位：** 湖南大学 HNU GuoLab
- **联系邮箱：** `guochen@hnu.edu.cn`、`xfl825@hnu.edu.cn`、`ashionial@hnu.edu.cn`

## 版权与使用说明

Copyright © 2026 GuoLab. All Rights Reserved.

本项目中的文档、示例代码和架构图表均受版权保护。公开内容可用于个人学习、学术研究和非商业教育实践；未经书面许可，不得用于商业产品、付费课程、培训项目或商业出版物。完整条款请参阅 [LICENSE]({license_url})。
""".format(license_url=LICENSE_URL)
            
    with open(os.path.join(DOCS_DIR, "index.md"), "w", encoding="utf-8") as f:
        f.write(index_content)

    if os.path.exists(MKDOCS_YML):
        with open(MKDOCS_YML, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        nav = [{"首页": "index.md"}]
        for ch in chapters:
            nav.append({ch["short_title"]: ch["file"]})
            
        if appendices:
            app_nav = []
            for ap in appendices:
                app_nav.append({ap["short_title"]: ap["file"]})
            nav.append({"附录": app_nav})

        config["nav"] = nav

        with open(MKDOCS_YML, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)

def main():
    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith(".md") and file != "index.md":
                process_markdown_file(os.path.join(root, file))
    chapters, appendices = parse_structure()
    update_index_and_nav(chapters, appendices)

if __name__ == "__main__":
    main()
