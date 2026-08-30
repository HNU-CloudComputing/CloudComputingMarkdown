import os
import re
import html
import sys
from urllib.parse import quote
import yaml

CCBOOK_PATH = "latex_source"
MAIN_TEX = os.path.join(CCBOOK_PATH, "main.tex")
DOCS_DIR = "docs"
MKDOCS_YML = "mkdocs.yml"
TITLE_PATTERN = re.compile(r'\\(?:chapter|section)\*?\{([^}]+)\}')
BOOK_MAIN_TITLE = "云计算原理与实践"
BOOK_SUBTITLE = "以在线游戏为载体"
BOOK_TITLE = f"{BOOK_MAIN_TITLE}：{BOOK_SUBTITLE}"
LICENSE_URL = "https://github.com/HNU-CloudComputing/CloudComputingMarkdown/blob/main/LICENSE"
FIGURE_PUBLIC_BASE = "https://hnu-cloudcomputing.github.io/CloudComputingMarkdown/"
PDF_SITE_URL = "https://hnu-cloudcomputing.github.io/CloudComputingPDF/"
COURSE_SITE_URL = "https://hnu-cloudcomputing.github.io/cloudcompute-pages/"
EMPTY_FIGURE_REFERENCE_PATTERN = re.compile(
    r'\\?\[\s*\\?\]\s*\\?\(\s*\\?#fig:[^\n\)]+\\?\)'
)
EMPTY_CROSS_REFERENCE_PATTERN = re.compile(
    r'\\?\[\s*\\?\]\s*\\?\(\s*\\?#(?:sec|tab):[^\n\)]+\\?\)'
)

def extract_figure_label(text):
    """从带 Pandoc 转义或附加属性的字符串中提取规范 figure label。"""
    match = re.search(r'fig(?:\\?:)[A-Za-z0-9_:\\-]+', text)
    return match.group(0).replace("\\", "") if match else ""

def extract_cross_reference_label(text):
    """从 Pandoc 字符串中提取规范的 section/table label。"""
    match = re.search(r'(?:sec|tab)(?:\\?:)[A-Za-z0-9_:\\-]+', text)
    return match.group(0).replace("\\", "") if match else ""

def resolve_figure_src(src):
    """把构建输入中的相对图片路径转换为本站公开图片的绝对 URL。"""
    src = html.unescape(src.strip())
    if re.match(r'^(?:https?:|data:)', src, flags=re.IGNORECASE):
        return src

    while src.startswith("../"):
        src = src[3:]
    if src.startswith("./"):
        src = src[2:]

    if src.startswith("figures/"):
        return FIGURE_PUBLIC_BASE + quote(src, safe="/")
    return src

def extract_command_argument(text, command):
    """提取一个允许嵌套花括号的 LaTeX 命令参数。"""
    match = re.search(rf'\\{command}(?:\[[^\]]*\])?\s*\{{', text)
    if not match:
        return ""
    start = match.end()
    depth = 1
    for index in range(start, len(text)):
        if text[index] == "{" and text[index - 1] != "\\":
            depth += 1
        elif text[index] == "}" and text[index - 1] != "\\":
            depth -= 1
            if depth == 0:
                return text[start:index]
    return ""

def clean_latex_caption(caption):
    """把图注中的常见行内 LaTeX 命令转换为可显示纯文本。"""
    previous = None
    while previous != caption:
        previous = caption
        caption = re.sub(
            r'\\(?:textbf|textit|emph|texttt|underline)\{([^{}]*)\}',
            r'\1',
            caption
        )
    caption = re.sub(r'\\url\{([^{}]*)\}', r'\1', caption)
    caption = caption.replace(r'\%', '%').replace(r'\_', '_').replace('~', ' ')
    caption = re.sub(r'\s+', ' ', caption)
    return caption.strip()

def load_figure_metadata(filepath):
    """从对应 TeX 源文件读取图路径、label 与 caption，兼容旧版 Pandoc。"""
    stem = os.path.splitext(os.path.basename(filepath))[0]
    candidates = [
        os.path.join(CCBOOK_PATH, "section", f"{stem}.tex"),
        os.path.join(CCBOOK_PATH, "appendix", f"{stem}.tex"),
    ]
    tex_path = next((path for path in candidates if os.path.isfile(path)), None)
    if not tex_path:
        return {"by_label": {}, "by_path": {}}

    with open(tex_path, "r", encoding="utf-8") as source:
        tex = source.read()

    by_label = {}
    by_path = {}
    figure_number = 0
    blocks = re.findall(
        r'\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}',
        tex,
        flags=re.DOTALL
    )
    for block in blocks:
        image_match = re.search(
            r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',
            block
        )
        label_match = re.search(r'\\label\{([^}]+)\}', block)
        caption = clean_latex_caption(extract_command_argument(block, "caption"))
        if not image_match or not caption:
            continue
        figure_number += 1
        image_path = image_match.group(1).strip().lstrip("./")
        item = {
            "path": image_path,
            "label": label_match.group(1).strip() if label_match else "",
            "caption": caption,
            "number": figure_number,
        }
        by_path[image_path] = item
        if item["label"]:
            by_label[item["label"]] = item
    return {"by_label": by_label, "by_path": by_path}

def normalize_figures(content, metadata=None):
    """把 Pandoc 的独立图片统一转换为带编号、锚点和可见图注的 HTML figure。"""
    metadata = metadata or {"by_label": {}, "by_path": {}}
    by_label = metadata.get("by_label", {})
    by_path = metadata.get("by_path", {})

    def find_metadata(label, src):
        if label and label in by_label:
            return by_label[label]
        normalized_src = html.unescape(src).strip()
        while normalized_src.startswith("../"):
            normalized_src = normalized_src[3:]
        normalized_src = normalized_src.lstrip("./")
        return by_path.get(normalized_src)

    def build_figure(caption, src, label=""):
        item = find_metadata(label, src)
        if (not caption.strip() or caption.strip().lower() in {"image", "figure", "fig"}) and item:
            caption = item["caption"]
        if not label and item:
            label = item["label"]
        escaped_caption = html.escape(caption.strip())
        escaped_src = html.escape(resolve_figure_src(src), quote=True)
        figure_id = f' id="{html.escape(label, quote=True)}"' if label else ""
        return (
            f'<figure{figure_id}>\n'
            f'<img src="{escaped_src}" alt="{escaped_caption}" style="max-width:100%; height:auto;" />\n'
            f'<figcaption>{escaped_caption}</figcaption>\n'
            f'</figure>'
        )

    legacy_labeled_figure = re.compile(
        r'^!\[(.*?)\]\((\S+?)(?:\s+"[^"]*")?\)(?:\s*\{([^}\n]*)\})?[ \t]*\n'
        r'(?:[ \t]*\n)*\[\]\{#([^\s}]+)[^}]*\}[ \t]*$',
        flags=re.MULTILINE
    )

    def legacy_labeled_figure_replacer(match):
        caption, src, _, label = match.groups()
        return build_figure(caption, src, label)

    content = legacy_labeled_figure.sub(legacy_labeled_figure_replacer, content)

    markdown_figure = re.compile(
        r'^!\[(.*?)\]\((\S+?)(?:\s+"[^"]*")?\)(?:\s*\{([^}\n]*)\})?[ \t]*$',
        flags=re.MULTILINE
    )

    def markdown_figure_replacer(match):
        caption = match.group(1).strip()
        src = match.group(2)
        attrs = match.group(3) or ""
        id_match = re.search(r'(?:^|\s)#([^\s]+)', attrs)
        label = id_match.group(1) if id_match else ""
        return build_figure(caption, src, label)

    content = markdown_figure.sub(markdown_figure_replacer, content)

    html_figure = re.compile(
        r'<figure\b([^>]*)>\s*(<img\b[^>]*?/?>)\s*<figcaption>(.*?)</figcaption>\s*</figure>',
        flags=re.DOTALL | re.IGNORECASE
    )
    figure_number = 0
    figure_numbers = {}

    def html_figure_replacer(match):
        nonlocal figure_number
        figure_number += 1
        attrs, image, caption = match.groups()
        image = re.sub(
            r'(\bsrc=["\'])(.*?)(["\'])',
            lambda src_match: (
                src_match.group(1)
                + html.escape(resolve_figure_src(src_match.group(2)), quote=True)
                + src_match.group(3)
            ),
            image,
            count=1,
            flags=re.IGNORECASE
        )
        caption = re.sub(r'^图\s*\d+\s*[：:]\s*', '', caption.strip())
        id_match = re.search(r'\bid=["\']([^"\']+)["\']', attrs, flags=re.IGNORECASE)
        if id_match:
            figure_numbers[id_match.group(1)] = figure_number
        return (
            f'<figure{attrs}>\n'
            f'{image}\n'
            f'<figcaption style="font-size:0.85em; font-style:normal; color:#666; '
            f'text-align:center; margin-top:0.5rem;">图 {figure_number}：{caption}</figcaption>\n'
            f'</figure>'
        )

    content = html_figure.sub(html_figure_replacer, content)

    def empty_figure_reference_replacer(match):
        label = extract_figure_label(match.group(0))
        if not label:
            return match.group(0)
        number = figure_numbers.get(label)
        if not number and label in by_label:
            number = by_label[label].get("number")
        if not number:
            print(
                "UNRESOLVED_FIGURE_REFERENCE "
                f"raw={match.group(0)!r} label={label!r} "
                f"figure_ids={sorted(figure_numbers)!r} "
                f"tex_labels={sorted(by_label)!r}",
                file=sys.stderr,
                flush=True
            )
        return f'[{number}](#{label})' if number else match.group(0)

    return EMPTY_FIGURE_REFERENCE_PATTERN.sub(empty_figure_reference_replacer, content)

def restore_empty_figure_references(content, metadata):
    """在 Pandoc 属性清理后，用 TeX 元数据恢复残留的空图引用。"""
    by_label = metadata.get("by_label", {})
    html_numbers = {
        label: int(number)
        for label, number in re.findall(
            r'<figure\b[^>]*\bid=["\']([^"\']+)["\'][^>]*>.*?'
            r'<figcaption[^>]*>\s*图\s*(\d+)\s*[：:]',
            content,
            flags=re.DOTALL | re.IGNORECASE
        )
    }

    def replacer(match):
        label = extract_figure_label(match.group(0))
        if not label:
            return match.group(0)
        item = by_label.get(label)
        number = html_numbers.get(label)
        if not number and item:
            number = item.get("number")
        return f'[{number}](#{label})' if number else match.group(0)

    return EMPTY_FIGURE_REFERENCE_PATTERN.sub(replacer, content)

def restore_cross_document_references(content):
    """恢复按章独立转换时 Pandoc 无法解析的跨文件引用。"""
    def replacer(match):
        label = extract_cross_reference_label(match.group(0))
        if not label:
            return match.group(0)

        chapter_match = re.fullmatch(r'sec:chapter(\d+)', label)
        if chapter_match:
            number = chapter_match.group(1)
            return f'[{number}](sec{number}.md)'
        if label == 'sec:appendix-lab-guide':
            return '[B](AppendixB.md)'
        if label == 'tab:serverless-k8s-decision':
            return '[“Serverless 与 Kubernetes 的场景化决策参考”](sec5.md)'
        return match.group(0)

    return EMPTY_CROSS_REFERENCE_PATTERN.sub(replacer, content)

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
    figure_metadata = load_figure_metadata(filepath)
    content = normalize_figures(content, figure_metadata)

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
    content = restore_empty_figure_references(content, figure_metadata)
    content = restore_cross_document_references(content)
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

    remaining_empty_figure_refs = EMPTY_FIGURE_REFERENCE_PATTERN.findall(content)
    if remaining_empty_figure_refs:
        raise ValueError(
            f"仍存在未恢复编号的空图引用：{filepath} "
            f"({len(remaining_empty_figure_refs)} 处；"
            f"首条原始内容={remaining_empty_figure_refs[0]!r})"
        )

    remaining_cross_document_refs = EMPTY_CROSS_REFERENCE_PATTERN.findall(content)
    if remaining_cross_document_refs:
        raise ValueError(
            f"仍存在未恢复的跨文件引用：{filepath} "
            f"({len(remaining_cross_document_refs)} 处)"
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
    index_content = f"""---
hide:
  - navigation
  - toc
---

<div class="course-home">
  <section class="course-home-hero" aria-labelledby="course-home-title">
    <div class="course-home-kicker">湖南大学 · 云计算课程教材</div>
    <div class="course-home-hero-grid">
      <div>
        <h1 id="course-home-title">{BOOK_MAIN_TITLE}</h1>
        <p class="course-home-subtitle">{BOOK_SUBTITLE}</p>
        <p class="course-home-lead">以在线游戏为贯穿案例，从网络通信、单机并发和分布式协同逐步进入云原生部署与核心原理。</p>
        <div class="course-home-actions">
          <a class="course-home-button course-home-button-primary" href="{PDF_SITE_URL}">阅读 PDF 版</a>
          <a class="course-home-button course-home-button-secondary" href="{COURSE_SITE_URL}">返回课程主页</a>
        </div>
      </div>
      <dl class="course-home-meta">
        <div><dt>课程性质</dt><dd>本科专业选修课</dd></div>
        <div><dt>内容结构</dt><dd>前言 · 六章 · 两份附录</dd></div>
        <div><dt>阅读方式</dt><dd>网页正文与配套 PDF</dd></div>
        <div><dt>编写单位</dt><dd>湖南大学 HNU GuoLab</dd></div>
      </dl>
    </div>
  </section>

  <section class="course-home-path" aria-labelledby="course-home-path-title">
    <header class="course-home-path-heading">
      <span>LEARNING PATH</span>
      <h2 id="course-home-path-title">从在线原型到云平台</h2>
      <p>课程以系统规模增长为线索，每一阶段都由上一阶段暴露的工程问题推动。</p>
    </header>
    <div class="course-home-path-grid">
      <article><span>01</span><h3>建立在线闭环</h3><p>从单机程序进入客户端—服务器架构，完成连接、消息、裁决与状态同步。</p></article>
      <article><span>02</span><h3>提升单机能力</h3><p>通过 goroutine、同步机制、连接池和对象复用控制并发与尾延迟。</p></article>
      <article><span>03</span><h3>扩展多机系统</h3><p>引入分片、路由、跨节点协同、复制与共识，处理容量和故障问题。</p></article>
      <article><span>04</span><h3>交给平台治理</h3><p>使用容器与 Kubernetes 统一交付、调度、扩缩容和故障恢复。</p></article>
    </div>
  </section>

  <section class="course-home-section" aria-labelledby="course-home-chapters">
    <header class="course-home-section-heading">
      <span>COURSE READER</span>
      <h2 id="course-home-chapters">课程内容</h2>
      <p>按照课程进度逐章阅读；前言说明全书的教学主线，六章正文对应课程的核心知识结构。</p>
    </header>
    <div class="course-home-grid">
"""

    for ch in chapters:
        title = html.escape(ch["full_title"])
        key = os.path.splitext(ch["file"])[0]
        if "intro" in key.lower():
            index_label = "导读"
            meta = "前言"
        else:
            num_match = re.search(r'\d+', key)
            index_label = f"{int(num_match.group(0)):02d}" if num_match else "章节"
            meta = "课程章节"
        index_content += f"""      <a class="course-home-card" href="{key}/">
        <span class="course-home-index">{index_label}</span>
        <span class="course-home-card-copy"><strong>{title}</strong><small>{meta} · 网页阅读</small></span>
        <span class="course-home-arrow" aria-hidden="true">→</span>
      </a>
"""

    index_content += """    </div>
  </section>
"""

    if appendices:
        index_content += """  <section class="course-home-section course-home-section-compact" aria-labelledby="course-home-appendix">
    <header class="course-home-section-heading">
      <span>SUPPLEMENTARY MATERIAL</span>
      <h2 id="course-home-appendix">附录</h2>
    </header>
    <div class="course-home-grid course-home-grid-appendix">
"""
        for ap in appendices:
            title = html.escape(ap["full_title"])
            key = os.path.splitext(ap["file"])[0]
            letter = key.replace("Appendix", "").replace("appendix", "") or "附录"
            index_content += f"""      <a class="course-home-card" href="{key}/">
        <span class="course-home-index">{html.escape(letter)}</span>
        <span class="course-home-card-copy"><strong>{title}</strong><small>补充材料 · 网页阅读</small></span>
        <span class="course-home-arrow" aria-hidden="true">→</span>
      </a>
"""
        index_content += """    </div>
  </section>
"""

    index_content += f"""  <section class="course-home-information" aria-label="教材与版权信息">
    <div class="course-home-editorial">
      <span class="course-home-section-label">EDITORIAL TEAM</span>
      <h2>编者信息</h2>
      <dl>
        <div><dt>核心编者与架构设计</dt><dd><a href="https://grzy.hnu.edu.cn/site/index/chenguo">陈果</a>、徐方林、胡文举、庞海鑫、谢先衍、贺臻、张道平</dd></div>
        <div><dt>所属单位</dt><dd>湖南大学 HNU GuoLab</dd></div>
        <div><dt>联系邮箱</dt><dd><a href="mailto:guochen@hnu.edu.cn">guochen@hnu.edu.cn</a>、<a href="mailto:xfl825@hnu.edu.cn">xfl825@hnu.edu.cn</a>、<a href="mailto:ashionial@hnu.edu.cn">ashionial@hnu.edu.cn</a></dd></div>
      </dl>
    </div>
    <div class="course-home-license">
      <span class="course-home-section-label">COPYRIGHT AND USE</span>
      <h2>版权与使用说明</h2>
      <p class="course-home-copyright">Copyright © 2026 GuoLab. All Rights Reserved.</p>
      <p>本项目中的文档、示例代码和架构图表均受版权保护。公开内容可用于个人学习、学术研究和非商业教育实践；未经书面许可，不得用于商业产品、付费课程、培训项目或商业出版物。完整条款请参阅 <a href="{LICENSE_URL}">LICENSE</a>。</p>
    </div>
  </section>
</div>
"""
            
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
