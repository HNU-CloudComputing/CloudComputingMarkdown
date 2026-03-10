import os
import re

def fix_escaped_quotes(content):
    return content.replace(r'\"', '"')

# ==========================================
# 新增：图片与引用标签“净水器”
# ==========================================
def clean_figure_tags(content):
    # 清理图片外壳 ::: figure* content = re.sub(r':::\s*figure\*?\s*\n', '', content)
    # 清理图片属性标签 (例如 {width="1\linewidth"} 或 {#fig:...})
    content = re.sub(r'\{width=[^\}]+\}', '', content)
    content = re.sub(r'\{#fig:[^\}]+\}', '', content)
    content = re.sub(r'\{reference-type="ref"[^\}]+\}', '', content)
    # 清理紧跟在图片后面的属性 ![alt](url){#fig...} -> ![alt](url)
    content = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)\s*\{[^\}]+\}', r'![\1](\2)', content)
    return content

# ==========================================
# 升级：双核表格解析引擎 (支持 Grid 和 Simple)
# ==========================================
def convert_tables(content):
    def replacer(match):
        tab_id = match.group(1).replace('#', '') 
        grid_text = match.group(2)
        caption = match.group(3).strip()
        lines = grid_text.strip().split('\n')
        
        # 核心 1：解析 Grid Table (+---+格式)
        if lines and lines[0].startswith('+'):
            col_indices = [i for i, c in enumerate(lines[0]) if c == '+']
            if len(col_indices) >= 2:
                rows = []
                curr_row = [""] * (len(col_indices) - 1)
                for line in lines:
                    if line.startswith('+'):
                        if any(c.strip() for c in curr_row):
                            rows.append([c.strip() for c in curr_row])
                        curr_row = [""] * (len(col_indices) - 1)
                    elif line.startswith('|'):
                        for i in range(len(col_indices) - 1):
                            start, end = col_indices[i] + 1, col_indices[i+1]
                            cell = line[start:end].strip()
                            if cell:
                                curr_row[i] = curr_row[i] + "<br>" + cell if curr_row[i] else cell
                if rows:
                    pipe_lines = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join(["---"] * (len(col_indices) - 1)) + "|"]
                    for r in rows[1:]:
                        pipe_lines.append("| " + " | ".join(r) + " |")
                    table_str = "\n".join(pipe_lines)
                    return f'\n\n{table_str}\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n\n'

        # 核心 2：解析 Simple Table (--- 格式，解决第五章表格问题)
        sep_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^[\s\-]+$', line) and '-' in line:
                sep_idx = i
                break
        
        if sep_idx != -1:
            col_spans = [(m.start(), m.end()) for m in re.finditer(r'-+', lines[sep_idx])]
            def extract_cols(line_str):
                cols = []
                for start, end in col_spans:
                    s, e = max(0, start - 2), min(len(line_str), end + 2)
                    cols.append(line_str[s:e].strip())
                return cols
            
            headers = extract_cols(lines[sep_idx-1]) if sep_idx > 0 else [""] * len(col_spans)
            pipe_lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(col_spans)) + "|"]
            for line in lines[sep_idx+1:]:
                if line.strip():
                    pipe_lines.append("| " + " | ".join(extract_cols(line)) + " |")
            
            table_str = "\n".join(pipe_lines)
            return f'\n\n{table_str}\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n\n'

        return f'\n\n{grid_text}\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n\n'

    pattern = re.compile(r':::\s*\{(#tab:[^\}]+)\}\n(.*?)\n\s*:\s*(.*?)\n:::', re.DOTALL)
    return pattern.sub(replacer, content)

# ==========================================
# 代码块修复引擎
# ==========================================
def clean_code_blocks(content):
    content = re.sub(r'```[a-zA-Z0-9_-]*\s*\n(```[^\n]*\n.*?)\n```\s*\n```', r'\n\n\1\n```\n\n', content, flags=re.DOTALL)
    
    def replacer_curly(match):
        attr, code = match.group(1), match.group(2)
        lang_match = re.search(r'language="([^"]+)"', attr)
        lang = lang_match.group(1) if lang_match else (re.search(r'\.([a-zA-Z0-9_-]+)', attr).group(1) if re.search(r'\.([a-zA-Z0-9_-]+)', attr) and 'numberLines' not in attr else "")
        return f"\n\n```{lang}\n{code}\n```\n\n"
    content = re.sub(r'```\s*\{([^\n]+)\}\n(.*?)\n```', replacer_curly, content, flags=re.DOTALL)

    def replacer_square(match):
        attr, code = match.group(1), match.group(2)
        lang_match = re.search(r'language=([a-zA-Z0-9_-]+)', attr)
        lang = lang_match.group(1) if lang_match else ""
        return f"\n\n```{lang}\n{code}\n```\n\n"
    content = re.sub(r'```\s*\[([^\n]+)\]\n(.*?)\n```', replacer_square, content, flags=re.DOTALL)

    def replacer_plaintext(match):
        lang = match.group(1)
        return f"\n\n```{lang}\n{match.group(2).strip()}\n```\n\n"
    content = re.sub(r'^\[\s*[^\]]*language=([a-zA-Z0-9_-]+)[^\]]*\]\s*\n(.*?)(?=\n{2,}|\n:::|\Z)', replacer_plaintext, content, flags=re.MULTILINE | re.DOTALL)
    
    # 清理所有没用的 :::
    content = re.sub(r'^:::\s*tcolorbox\s*\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'\n:::\s*\n', '\n\n', content)
    return content

# ==========================================
# 数学公式修复引擎
# ==========================================
def fix_math_formulas(content):
    content = content.replace(r'\$', '___ESCAPED_DOLLAR___')
    def replacer(match):
        block_math, inline_math = match.group(1), match.group(2)
        if block_math is not None:
            return f"\n\n$$\n{block_math.strip()}\n$$\n\n"
        elif inline_math is not None:
            return f"${re.sub(r's+', ' ', inline_math.strip().replace(chr(10), ' '))}$"
    content = re.sub(r'\$\$(.*?)\$\$|\$([^\$]+?)\$', replacer, content, flags=re.DOTALL)
    return content.replace('___ESCAPED_DOLLAR___', r'\$')

def final_cleanup(content):
    content = re.sub(r'^\{#[^\}]+\}\s*\n', '', content, flags=re.MULTILINE)
    return re.sub(r'\n{3,}', '\n\n', content)

def process_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content = fix_escaped_quotes(content)
    content = clean_figure_tags(content)   # 新增：优先清理图片和引用
    content = convert_tables(content)      # 升级：双核解析表格
    content = clean_code_blocks(content)
    content = fix_math_formulas(content)
    content = final_cleanup(content)

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