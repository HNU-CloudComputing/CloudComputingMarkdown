import os
import re

def fix_math_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 保护原本就被转义的普通美元符号（例如 \$100）防止被误伤
    content = content.replace(r'\$', '___ESCAPED_DOLLAR___')

    # 2. 核心替换逻辑
    def math_replacer(match):
        block = match.group(1)
        inline = match.group(2)
        
        if block is not None:
            # 处理块级公式 $$...$$：清理首尾空白，并强制它上下各有一行空行
            math_content = block.strip()
            return f"\n\n$$\n{math_content}\n$$\n\n"
            
        elif inline is not None:
            # 处理行内公式 $...$：严格去除内部首尾的空格，并将多行意外折断的公式压缩为单行
            inline_content = inline.strip()
            inline_content = inline_content.replace('\n', ' ')
            inline_content = re.sub(r'\s+', ' ', inline_content)
            return f"${inline_content}$"

    # 匹配 $$...$$ 或 $...$
    # 注意：使用 re.DOTALL 使得 .*? 可以匹配跨行的公式内容
    pattern = r'\$\$(.*?)\$\$|\$([^\$]+?)\$'
    content = re.sub(pattern, math_replacer, content, flags=re.DOTALL)

    # 3. 还原被保护的转义美元符号
    content = content.replace('___ESCAPED_DOLLAR___', r'\$')

    # 4. 清理替换过程中可能产生的过多的连串空行 (将3个以上的换行符压缩为2个)
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    target_dir = r".\\cloud-computing-book\\docs"
    
    print("开始修复数学公式格式...")
    count = 0
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                fix_math_in_file(filepath)
                print(f"  [✓] 已修复: {file}")
                count += 1
                
    print(f"\n修复完成！共处理了 {count} 个文件。请刷新网页查看完美的数学公式！")

if __name__ == "__main__":
    main()