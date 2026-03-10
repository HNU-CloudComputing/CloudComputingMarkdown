import os
import re

def fix_all_markdown_issues(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # ==========================================
    # 1. 修复反斜杠双引号 (将 \" 替换为 ")
    # ==========================================
    content = content.replace(r'\"', '"')

    # ==========================================
    # 2. 修复嵌套代码块和 Pandoc 代码块
    # ==========================================
    # 第一步：脱掉“俄罗斯套娃”的最外层 (如果有的话)
    # 把 ```json \n ``` {...} \n CODE \n ``` \n ``` 变成 ``` {...} \n CODE \n ```
    content = re.sub(
        r'```[a-zA-Z0-9]*\n(```\s*\{[^\}]*\})\n(.*?)\n```\n```', 
        r'\1\n\2\n```', 
        content, 
        flags=re.DOTALL
    )
    
    # 第二步：将 Pandoc 代码块转换为标准 Markdown 代码块
    # 优先提取 language="bash" 中的 bash
    content = re.sub(
        r'```\s*\{[^\}]*language="([^"]+)"[^\}]*\}\n(.*?)\n```', 
        r'```\1\n\2\n```', 
        content, 
        flags=re.DOTALL
    )
    # 如果没有 language 属性，尝试提取 .bash 这种格式作为语言
    content = re.sub(
        r'```\s*\{[^\}]*\.([a-zA-Z0-9_-]+)[^\}]*\}\n(.*?)\n```', 
        r'```\1\n\2\n```', 
        content, 
        flags=re.DOTALL
    )

    # ==========================================
    # 3. 自动修复第五章的两个复杂表格
    # ==========================================
    # 修复表 1：三种环境交付方式的对比
    table1_pandoc = r':::\s*\{#tab:env-delivery-comparison\}.*?:::'
    table1_md = """| | 手工安装 | 虚拟机 | 容器 |
| :--- | :--- | :--- | :--- |
| **环境一致性** | 差 | 好 | 好 |
| **资源开销** | 无额外开销 | 高（GB级） | 低（MB级） |
| **启动速度** | -- | 分钟级 | 秒级 |
| **可重复性** | 差 | 好 | 好 |
| **扩容效率** | 极低 | 低 | 高 |

<center id="tab:env-delivery-comparison" style="color: #888; font-size: 0.9em;">表 1：三种环境交付方式的对比</center>"""
    content = re.sub(table1_pandoc, table1_md, content, flags=re.DOTALL)

    # 修复表 2：Serverless与Kubernetes的场景化决策参考
    table2_pandoc = r':::\s*\{#tab:serverless-k8s-decision\}.*?:::'
    table2_md = """| 业务特征 | 推荐方案 | 主要原因 |
| :--- | :--- | :--- |
| **长连接实时交互** | Kubernetes | WebSocket/TCP长连接需要稳定连接驻留，容器常驻模型更匹配 |
| **有状态会话管理** | Kubernetes | 会话粘性、进程内状态与低抖动路由更容易在K8s中实现 |
| **低频触发式任务** | Serverless | 按调用计费可避免空闲资源浪费，成本可下降90%以上 |
| **不可预测突发流量** | Serverless | 自动弹性能力强，能快速扩缩并减少人工容量规划压力 |
| **定时批处理** | Serverless | 与事件调度天然契合，任务短平快且资源利用率高 |
| **延迟敏感 (<50ms)** | Kubernetes | 冷启动尾延迟风险较高，常驻实例更容易保障严格时延目标 |

<center id="tab:serverless-k8s-decision" style="color: #888; font-size: 0.9em;">表 2：Serverless与Kubernetes的场景化决策参考</center>"""
    content = re.sub(table2_pandoc, table2_md, content, flags=re.DOTALL)

    # ==========================================
    # 4. 清理残留的空标签 (例如单独占一行的 {#xxx})
    # ==========================================
    content = re.sub(r'^\{#[^\}]+\}\s*\n', '', content, flags=re.MULTILINE)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    target_dir = r".\\cloud-computing-book\\docs"
    
    print("开始执行全章节终极清洗...")
    count = 0
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                fix_all_markdown_issues(filepath)
                print(f"  [✓] 已深度清洗: {file}")
                count += 1
                
    print(f"\n清洗完成！共处理了 {count} 个文件。代码块和引号已恢复正常！")

if __name__ == "__main__":
    main()