import os
import re

# ==========================================
# 步骤 1：修复被错误转义的双引号
# ==========================================
def fix_escaped_quotes(content):
    return content.replace(r'\"', '"')

# ==========================================
# 步骤 2：自动将 Pandoc 的网格表格转为 MkDocs 管道表格
# ==========================================
def convert_grid_tables(content):
    def replacer(match):
        tab_id = match.group(1).replace('#', '')  # 提取 ID，例如 tab:architecture_evolution
        grid_text = match.group(2)
        caption = match.group(3).strip()          # 提取表格标题
        
        lines = grid_text.strip().split('\n')
        
        # 验证是否为标准网格表 (以 + 开头)
        if lines and lines[0].startswith('+'):
            col_indices = [i for i, c in enumerate(lines[0]) if c == '+']
            if len(col_indices) < 2:
                return match.group(0)
                
            rows = []
            curr_row = [""] * (len(col_indices) - 1)
            
            for line in lines:
                if line.startswith('+'): # 遇到边界线，保存上一行的数据
                    if any(c.strip() for c in curr_row):
                        rows.append([c.strip() for c in curr_row])
                    curr_row = [""] * (len(col_indices) - 1)
                elif line.startswith('|'): # 遇到数据行，提取内容
                    for i in range(len(col_indices) - 1):
                        start, end = col_indices[i] + 1, col_indices[i+1]
                        cell = line[start:end].strip()
                        if cell:
                            # 单元格内换行用 <br> 拼接
                            curr_row[i] = curr_row[i] + "<br>" + cell if curr_row[i] else cell
            
            # 组装为标准 Markdown 管道表
            if rows:
                pipe_lines = []
                # 拼接表头
                pipe_lines.append("| " + " | ".join(rows[0]) + " |")
                # 拼接分隔符
                pipe_lines.append("|" + "|".join(["---"] * (len(col_indices) - 1)) + "|")
                # 拼接数据行
                for r in rows[1:]:
                    pipe_lines.append("| " + " | ".join(r) + " |")
                
                table_str = "\n".join(pipe_lines)
                caption_str = f'\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n'
                return table_str + caption_str
                
        # 兜底：如果不是网格表，原样返回并清理外壳
        return f'{grid_text}\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n'

    pattern = re.compile(r':::\s*\{(#tab:[^\}]+)\}\n(.*?)\n\s*:\s*(.*?)\n:::', re.DOTALL)
    return pattern.sub(replacer, content)

# ==========================================
# 步骤 3：修复嵌套和带有复杂属性的代码块
# ==========================================
def clean_code_blocks(content):
    # 先剥离俄罗斯套娃的外层 (```json ... ```)
    content = re.sub(r'```[a-zA-Z0-9_-]*\s*\n(```[^\n]*\n.*?)\n```\s*\n```', r'\1\n```', content, flags=re.DOTALL)
    
    def replacer(match):
        attr = match.group(1)
        code = match.group(2)
        lang = ""
        
        # 尝试提取 language="bash"
        lang_match = re.search(r'language="([^"]+)"', attr)
        if lang_match:
            lang = lang_match.group(1)
        else:
            # 尝试提取 .bash
            class_match = re.search(r'\.([a-zA-Z0-9_-]+)', attr)
            if class_match and 'numberLines' not in attr:
                lang = class_match.group(1)
                
        return f"```{lang}\n{code}\n```"

    return re.sub(r'```\s*\{([^\n]+)\}\n(.*?)\n```', replacer, content, flags=re.DOTALL)

# ==========================================
# 步骤 4：精准修复数学公式 (解决之前的语法报错)
# ==========================================
def fix_math_formulas(content):
    content = content.replace(r'\$', '___ESCAPED_DOLLAR___')
    
    def replacer(match):
        block_math = match.group(1)
        inline_math = match.group(2)
        
        if block_math is not None:
            # 块级公式：强制换行
            cleaned = block_math.strip()
            return f"\n\n$$\n{cleaned}\n$$\n\n"
        elif inline_math is not None:
            # 行内公式：清理空格，压缩为单行 (注意：把正则替换移到了 f-string 外部！)
            cleaned = inline_math.strip()
            cleaned = cleaned.replace('\n', ' ')
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return f"${cleaned}$"

    content = re.sub(r'\$\$(.*?)\$\$|\$([^\$]+?)\$', replacer, content, flags=re.DOTALL)
    content = content.replace('___ESCAPED_DOLLAR___', r'\$')
    return content

# ==========================================
# 步骤 5：最后清理孤儿锚点和多余空行
# ==========================================
def final_cleanup(content):
    # 删除单行的 {#id} 残留
    content = re.sub(r'^\{#[^\}]+\}\s*\n', '', content, flags=re.MULTILINE)
    # 压缩多余的空行 (3个以上压缩为2个)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content

# ==========================================
# 主流程：依次调用所有清洗管道
# ==========================================
def process_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content = fix_escaped_quotes(content)
    content = convert_grid_tables(content)
    content = clean_code_blocks(content)
    content = fix_math_formulas(content)
    content = final_cleanup(content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    target_dir = "docs" # 适配 GitHub Actions 的相对路径
    print("🚀 开始执行云端 Markdown 深度清洗流水线...")
    
    # 确保目录存在
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
                
    print(f"\n🎉 完美收工！共深度清洗了 {count} 个文件。")

if __name__ == "__main__":
    main()