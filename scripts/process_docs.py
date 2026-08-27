import os
import re
import yaml

CCBOOK_PATH = "latex_source"
MAIN_TEX = os.path.join(CCBOOK_PATH, "main.tex")
DOCS_DIR = "docs"
MKDOCS_YML = "mkdocs.yml"
TITLE_PATTERN = re.compile(r'\\(?:chapter|section)\*?\{([^}]+)\}')

def process_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复转义双引号与反斜杠
    content = content.replace(r'\"', '"')
    content = content.replace(r'\ ', ' ')

    # 2. 清理 Pandoc Div 边界 (:::)
    content = re.sub(r'^:::.*$', '', content, flags=re.MULTILINE)

    # 3. 清理标签与乱码
    content = re.sub(r'\s*\{#[^\}]+\}', '', content)
    content = re.sub(r'\{width=[^\}]+\}', '', content)
    content = re.sub(r'\s*\{=html\}', '', content)
    content = re.sub(r'\{reference-type="ref"[^\}]+\}', '', content)
    content = re.sub(r'\[\s*\]\(#[^\)]+\)', '', content)
    content = re.sub(r'\[(fig|tab|sec):[^\]]+\]', '', content)
    content = re.sub(r'如图\s+所示', '如图所示', content)
    content = re.sub(r'如表\s+所示', '如表所示', content)
    content = re.sub(r'附录\s+的', '附录中的', content)

    # 4. 修复标题与代码块
    content = re.sub(r'^:\s+([^\n]+)\n+(?=```)', r'**\1**\n\n', content, flags=re.MULTILINE)
    content = re.sub(r'^:\s+([^\n]+)$', r'\n\n<center style="color: #888; font-size: 0.9em;">表：\1</center>\n\n', content, flags=re.MULTILINE)
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

    # 5. 表格隔离与公式修复
    content = re.sub(r'(^\|[^\n]*(?:\n\|[^\n]*)*)', r'\n\n\1\n\n', content, flags=re.MULTILINE)
    content = content.replace(r'\$', '___ESCAPED_DOLLAR___')
    def math_replacer(match):
        b, i = match.group(1), match.group(2)
        return f"\n\n$$\n{b.strip()}\n$$\n\n" if b else f"${re.sub(r'\s+', ' ', i.strip().replace(chr(10), ' '))}$"
    content = re.sub(r'\$\$(.*?)\$\$|\$([^\$]+?)\$', math_replacer, content, flags=re.DOTALL)
    content = content.replace('___ESCAPED_DOLLAR___', r'\$')

    content = content.replace("figures/figures/", "figures/")
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

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
                # 清洗 LaTeX 指令并去掉反斜杠
                clean_title = re.sub(r'\\[a-zA-Z]+(\{[^}]*\})?', '', raw_title).replace('\\', ' ').strip()
                clean_title = re.sub(r'\s+', ' ', clean_title)
                
                base_name = os.path.splitext(os.path.basename(item))[0]
                md_target = f"{base_name}.md"

                # 生成导航栏专用短标题
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

def update_index_and_nav(chapters, appendices):
    # 1. 首页继续使用完整标题展示
    index_content = "# ☁️ 云计算技术实践课程在线文档\n\n"
    index_content += "这是由 **GuoLab** 倾力编写的教科书在线阅读版。以下为最新章节导航：\n\n"
    index_content += "### 📖 章节目录\n\n"
    for ch in chapters:
        index_content += f"- [**{ch['full_title']}**]({ch['file']})\n"
    
    if appendices:
        index_content += "\n### 📑 附录内容\n\n"
        for ap in appendices:
            index_content += f"- [**{ap['full_title']}**]({ap['file']})\n"
            
    with open(os.path.join(DOCS_DIR, "index.md"), "w", encoding="utf-8") as f:
        f.write(index_content)

    # 2. 导航栏采用精简短标题 (首页 / 前言 / 第一章 ... / 附录)
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
        print("✅ 已成功重构精简导航栏与完整主页目录")

def main():
    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith(".md") and file != "index.md":
                process_markdown_file(os.path.join(root, file))
    chapters, appendices = parse_structure()
    update_index_and_nav(chapters, appendices)

if __name__ == "__main__":
    main()