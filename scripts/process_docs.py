import os
import re

def auto_convert_grid_table(match):
    """核心引擎：自动将 Pandoc 的 ASCII 网格表转换为 MkDocs 管道表"""
    tab_id = match.group(1).replace('#', '')  # 提取 ID，例如 tab:architecture_evolution
    grid_text = match.group(2)
    caption = match.group(3).strip()          # 提取表格标题
    
    lines = grid_text.strip().split('\n')
    
    # 验证是否为标准网格表 (以 + 开头)
    if lines and lines[0].startswith('+'):
        # 通过寻找 '+' 的位置来确定列宽和边界
        col_indices = [i for i, c in enumerate(lines[0]) if c == '+']
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
                        # 如果同一个格子有多行内容，用 <br> 连接
                        curr_row[i] = curr_row[i] + "<br>" + cell if curr_row[i] else cell
        
        # 组装为标准 Markdown 管道表
        if rows:
            pipe = ["| " + " | ".join(rows[0]) + " |", "|" + "---|".join([""] * len(col_indices))]
            for r in rows[1:]:
                pipe.append("| " + " | ".join(r) + " |")
            
            table_str = "\n".join(pipe)
            return f'{table_str}\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n'
            
    # 如果不是网格表（兜底方案），仅清理外壳并保留标题
    return f'{grid_text}\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n'


def process_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复转义引号
    content = content.replace(r'\"', '"')

    # 2. 自动解析与转换表格
    content = re.sub(r':::\s*\{(#tab:[^\}]+)\}\n(.*?)\n\s*:\s*(.*?)\n:::', auto_convert_grid_table, content, flags=re.DOTALL)

    # 3. 修复代码块
    content = re.sub(r'```[a-zA-Z0-9_-]*\s*\n(```[^\n]*\n.*?)\n```\s*\n```', r'\1\n```', content, flags=re.DOTALL)
    def clean_pandoc_header(match):
        attr = match.group(1)
        code = match.group(2)
        lang = re.search(r'language="([^"]+)"', attr)
        lang = lang.group(1) if lang else (re.search(r'\.([a-zA-Z0-9_-]+)', attr).group(1) if re.search(r'\.([a-zA-Z0-9_-]+)', attr) and 'numberLines' not in attr else "")
        return f"```{lang}\n{code}\n```"
    content = re.sub(r'```\s*\{([^\n]+)\}\n(.*?)\n```', clean_pandoc_header, content, flags=re.DOTALL)

    # 4. 修复数学公式
    content = content.replace(r'\$', '___ESCAPED_DOLLAR___')
    def math_replacer(match):
        if match.group(1): return f"\n\n$$\n{match.group(1).strip()}\n$$\n\n"
        if match.group(2): return f"${re.sub(r'\\s+', ' ', match.group(2).strip().replace(chr(10), ' '))}$"
    content = re.sub(r'\$\$(.*?)\$\$|\$([^\$]+?)\$', math_replacer, content, flags=re.DOTALL)
    content = content.replace('___ESCAPED_DOLLAR___', r'\$')

    # 5. 清理孤儿锚点
    content = re.sub(r'^\{#[^\}]+\}\s*\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'\n{3,}', '\n\n', content) # 压缩多余空行

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    # 注意：这里改成了相对路径，完美适配 GitHub Actions 的云服务器环境！
    target_dir = "docs" 
    print("🚀 开始执行全自动云端清洗流水线...")
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".md"):
                process_markdown_file(os.path.join(root, file))
                print(f"  [✓] 已处理: {file}")

if __name__ == "__main__":
    main()