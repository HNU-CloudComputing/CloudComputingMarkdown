import os
import re

def fix_escaped_quotes(content):
    return content.replace(r'\"', '"')

def convert_grid_tables(content):
    def replacer(match):
        tab_id = match.group(1).replace('#', '') 
        grid_text = match.group(2)
        caption = match.group(3).strip()
        lines = grid_text.strip().split('\n')
        
        if lines and lines[0].startswith('+'):
            col_indices = [i for i, c in enumerate(lines[0]) if c == '+']
            if len(col_indices) < 2: return match.group(0)
                
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
                # 关键修复：前后加上 \n\n，强制与正文隔开，MkDocs 才能正确识别表格
                return f'\n\n{table_str}\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n\n'
                
        return f'\n\n{grid_text}\n\n<center id="{tab_id}" style="color: #888; font-size: 0.9em;">表：{caption}</center>\n\n'

    pattern = re.compile(r':::\s*\{(#tab:[^\}]+)\}\n(.*?)\n\s*:\s*(.*?)\n:::', re.DOTALL)
    return pattern.sub(replacer, content)

def clean_code_blocks(content):
    # 前后加上 \n\n，防止代码块和正文粘连
    content = re.sub(r'```[a-zA-Z0-9_-]*\s*\n(```[^\n]*\n.*?)\n```\s*\n```', r'\n\n\1\n```\n\n', content, flags=re.DOTALL)
    
    def replacer_curly(match):
        attr, code = match.group(1), match.group(2)
        lang_match = re.search(r'language="([^"]+)"', attr)
        if lang_match:
            lang = lang_match.group(1)
        else:
            class_match = re.search(r'\.([a-zA-Z0-9_-]+)', attr)
            lang = class_match.group(1) if class_match and 'numberLines' not in attr else ""
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
        code = match.group(2).strip()
        return f"\n\n```{lang}\n{code}\n```\n\n"
    
    content = re.sub(r'^\[\s*[^\]]*language=([a-zA-Z0-9_-]+)[^\]]*\]\s*\n(.*?)(?=\n{2,}|\n:::|\Z)', 
                     replacer_plaintext, content, flags=re.MULTILINE | re.DOTALL)
    
    content = re.sub(r'^:::\s*tcolorbox\s*\n', '', content, flags=re.MULTILINE)
    return content

def fix_math_formulas(content):
    content = content.replace(r'\$', '___ESCAPED_DOLLAR___')
    def replacer(match):
        block_math, inline_math = match.group(1), match.group(2)
        if block_math is not None:
            return f"\n\n$$\n{block_math.strip()}\n$$\n\n"
        elif inline_math is not None:
            cleaned = re.sub(r'\s+', ' ', inline_math.strip().replace('\n', ' '))
            return f"${cleaned}$"
    content = re.sub(r'\$\$(.*?)\$\$|\$([^\$]+?)\$', replacer, content, flags=re.DOTALL)
    return content.replace('___ESCAPED_DOLLAR___', r'\$')

def final_cleanup(content):
    content = re.sub(r'^\{#[^\}]+\}\s*\n', '', content, flags=re.MULTILINE)
    return re.sub(r'\n{3,}', '\n\n', content)

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
    target_dir = "docs" 
    print("🚀 开始执行云端 Markdown 深度清洗流水线...")
    if not os.path.exists(target_dir):
        print(f"⚠️ 未找到 {target_dir} 目录，请检查路径。")
        return

    count = 0
    for root, dirs, files in os.walk(target_dir):
        if file.endswith(".md"):
            process_markdown_file(os.path.join(root, file))
            print(f"  [✓] 成功处理: {file}")
            count += 1
            
    print(f"\n🎉 共深度清洗了 {count} 个文件。")

if __name__ == "__main__":
    main()