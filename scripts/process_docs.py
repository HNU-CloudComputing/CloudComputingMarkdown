import os
import re
import yaml

CCBOOK_PATH = "latex_source"
MAIN_TEX = os.path.join(CCBOOK_PATH, "main.tex")
DOCS_DIR = "docs"
MKDOCS_YML = "mkdocs.yml"
TITLE_PATTERN = re.compile(r'\\(?:chapter|section)\*?\{([^}]+)\}')

# ==========================================
# 1. 深度清洗 Markdown 文件（完全保留你的原始代码）
# ==========================================
def process_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复被错误转义的双引号
    content = content.replace(r'\"', '"')

    # 2. 彻底清理所有的 Pandoc Div 边界 (:::)
    content = re.sub(r'^:::.*$', '', content, flags=re.MULTILINE)

    # 3. 清理各类无用标签、外壳、图片属性以及 HTML 乱码
    content = re.sub(r'\s*\{#[^\}]+\}', '', content)
    content = re.sub(r'\{width=[^\}]+\}', '', content)
    content = re.sub(r'\s*\{=html\}', '', content)
    content = re.sub(r'\{=html\}', '', content)

    # 清理交叉引用残留
    content = re.sub(r'\{reference-type="ref"[^\}]+\}', '', content)
    content = re.sub(r'\[\s*\]\(#[^\)]+\)', '', content)
    content = re.sub(r'\[(fig|tab|sec):[^\]]+\]', '', content)
    content = re.sub(r'如图\s+所示', '如图所示', content)
    content = re.sub(r'如表\s+所示', '如表所示', content)
    content = re.sub(r'附录\s+的', '附录中的', content)

    # 4. 智能区分代码块标题和表格标题
    content = re.sub(r'^:\s+([^\n]+)\n+(?=```)', r'**\1**\n\n', content, flags=re.MULTILINE)
    def caption_replacer(match):
        caption_text = match.group(1).strip()
        return f'\n\n<center style="color: #888; font-size: 0.9em;">表：{caption_text}</center>\n\n'
    content = re.sub(r'^:\s+([^\n]+)$', caption_replacer, content, flags=re.MULTILINE)

    # 5. 修复代码块
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
    content = re.sub(r'^\[\s*[^\]]*language=([a-zA-Z0-9_-]+)[^\]]*\]\s*\n(.*?)(?=\n{2,}|\Z)', plaintext_code_replacer, content, flags=re.MULTILINE | re.DOTALL)

    # 6. 表格强制隔离
    def table_padder(match):
        return f"\n\n{match.group(1)}\n\n"
    content = re.sub(r'(^\|[^\n]*(?:\n\|[^\n]*)*)', table_padder, content, flags=re.MULTILINE)

    # 7. 精准修复数学公式
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

    # 8. 修复图片可能多了一层目录的问题
    content = content.replace("figures/figures/", "figures/")

    # 9. 压缩多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# ==========================================
# 2. 动态解析 LaTeX 结构与标题 (生成完整标题与导航短标题)
# ==========================================
def parse_structure():
    if not os.path.exists(MAIN_TEX):
        print(f"⚠️ 未找到 {MAIN_TEX}，跳过动态目录生成")
        return [], []
    
    with open(MAIN_TEX, "r", encoding="utf-8") as f:
        main_content = f.read()

    inputs = re.findall(r'\\input\{([^}]+)\}', main_content)
    chapters = []
    appendices = []
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
                # 清洗 LaTeX 宏指令与反斜杠
                clean_title = re.sub(r'\\[a-zA-Z]+(\{[^}]*\})?', '', raw_title).replace('\\', ' ').strip()
                clean_title = re.sub(r'\s+', ' ', clean_title)
                
                base_name = os.path.splitext(os.path.basename(item))[0]
                md_target = f"{base_name}.md"

                # 提取导航栏专用的短标题 (前言 / 第一章 / 附录 A 等)
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
    # 1. 动态生成 index.md (主页使用完整标题展示)
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
    print("✅ 已动态更新 docs/index.md")

    # 2. 动态更新 mkdocs.yml 中的 nav (导航栏使用短标题)
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
        print("✅ 已根据最新 LaTeX 目录动态重写 mkdocs.yml 的 nav 导航")

# ==========================================
# 4. 流水线主入口
# ==========================================
def main():
    print("🚀 第一步：执行 Markdown 深度清洗流水线...")
    count = 0
    for root, dirs, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith(".md") and file != "index.md":
                process_markdown_file(os.path.join(root, file))
                count += 1
    print(f"🎉 清洗完成，共处理了 {count} 个章节文件。")

    print("\n🚀 第二步：动态提取 LaTeX 结构并更新主页与侧边栏...")
    chapters, appendices = parse_structure()
    update_index_and_nav(chapters, appendices)
    print("🎉 全部构建准备工作完成！")

if __name__ == "__main__":
    main()