import re
import os
import sys

def generate_html(md_path):
    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found.")
        return

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract Title
    title_match = re.search(r'^# (.*)', content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Study Materials"
    
    # Extract Header Image
    header_img_match = re.search(r'^!\[\]\((.*?)\)', content)
    header_img = header_img_match.group(1) if header_img_match else ""

    # Split content into segments (Paragraphs vs Study section)
    # We split by "## Paragraph X"
    segments = re.split(r'## Paragraph \d+', content)
    # The first segment is the title/intro, which we've mostly handled
    paragraphs = segments[1:]
    
    # Handle the footer (Learning & Practice)
    footer_match = re.search(r'## 🎓 (.*)', content, re.DOTALL)
    footer_content = footer_match.group(0) if footer_match else ""
    # Clean up the footer from the last paragraph if it's trapped there
    if paragraphs and "## 🎓" in paragraphs[-1]:
        paragraphs[-1] = paragraphs[-1].split("## 🎓")[0]

    html_template = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg-body: #f4f7f9;
            --bg-pane: #ffffff;
            --primary: #2563eb;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --accent: #3b82f6;
            --border: #e2e8f0;
            --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        }}
        
        body {{
            margin: 0;
            font-family: 'Inter', -apple-system, system-ui, sans-serif;
            background: var(--bg-body);
            color: var(--text-main);
            line-height: 1.6;
        }}

        .header {{
            background: #fff;
            padding: 60px 20px;
            text-align: center;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }}
        .header img {{ max-width: 800px; width: 100%; height: auto; border-radius: 12px; margin-bottom: 24px; box-shadow: var(--shadow); }}
        .header h1 {{ margin: 0; font-size: 2.5rem; font-weight: 800; letter-spacing: -0.025em; }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        }}

        .section-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
            align-items: start;
        }}

        .pane {{
            background: var(--bg-pane);
            padding: 40px;
            border-radius: 16px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .section-row:hover .pane {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        }}

        .left-pane {{ border-top: 6px solid var(--primary); }}
        .right-pane {{ border-top: 6px solid #10b981; background: #fcfdfd; }}

        .en-block {{ font-size: 1.25rem; font-weight: 500; color: #0f172a; margin-bottom: 20px; }}
        .cn-block {{ font-size: 1.1rem; color: #475569; border-top: 1px dashed var(--border); padding-top: 20px; }}
        
        .analysis-point {{ margin-bottom: 20px; }}
        .analysis-point strong {{ color: #059669; display: block; margin-bottom: 8px; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        .analysis-content {{ font-size: 1rem; color: #334155; }}
        
        .analysis-list {{ list-style: none; padding: 0; margin: 0; }}
        .analysis-list li {{ position: relative; padding-left: 20px; margin-bottom: 12px; }}
        .analysis-list li::before {{ content: "•"; position: absolute; left: 0; color: var(--primary); font-weight: bold; }}

        .inline-img {{ max-width: 100%; border-radius: 8px; margin: 20px 0; display: block; }}

        .footer {{
            background: #1e293b;
            color: #f8fafc;
            padding: 60px 40px;
            border-radius: 24px;
            margin: 60px 0;
        }}
        .footer h2, .footer h3 {{ color: #38bdf8; }}
        .footer hr {{ border: 0; border-top: 1px solid #334155; margin: 30px 0; }}

        @media (max-width: 1100px) {{
            .section-row {{ grid-template-columns: 1fr; }}
        }}

        code {{ background: #f1f5f9; padding: 0.2em 0.4em; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.9em; color: #e11d48; }}
    </style>
</head>
<body>
    <div class="header">
        {header_tag}
        <h1>{title}</h1>
    </div>
    
    <div class="container">
        {rows_html}
        
        <div class="footer">
            {footer_html}
        </div>
    </div>
</body>
</html>
    """

    def md_to_html_simple(text):
        # Convert simple markdown bits to HTML
        text = re.sub(r'\\*\\*(.*?)\\*\\*', r'<strong>\\1</strong>', text)
        text = re.sub(r'`(.*?)`', r'<code>\\1</code>', text)
        # Handle images: ![](path)
        text = re.sub(r'!\[\]\((.*?)\)', r'<img src="\\1" class="inline-img">', text)
        return text

    header_tag = f'<img src="{header_img}">' if header_img else ""
    rows_html = ""

    for i, section in enumerate(paragraphs):
        # Split into text and analysis
        parts = section.split("### 深度解析")
        if len(parts) < 2: continue
        
        text_content = parts[0].strip()
        analysis_content = parts[1].strip()
        
        # Parse Text Content (EN and CN)
        # Find images in text content first
        text_imgs = re.findall(r'!\[\]\((.*?)\)', text_content)
        clean_text = re.sub(r'!\[\]\((.*?)\)', '', text_content).strip()
        
        # Split remaining text into EN and CN (usually by first double newline or long stretch of text)
        # A more reliable way: find the first block that looks like English, then the rest is CN
        # For simplicity, we split by double newline
        text_blocks = [b.strip() for b in clean_text.split('\\n\\n') if b.strip()]
        en_text = text_blocks[0] if len(text_blocks) > 0 else ""
        cn_text = text_blocks[1] if len(text_blocks) > 1 else ""
        
        img_tags = "".join([f'<img src="{img}" class="inline-img">' for img in text_imgs])

        # Parse Analysis Content
        # We look for the 6 points: 词汇, 短语, 语法, 语态, 句法, 句子结构与组成成分
        points = ["词汇", "短语", "语法", "语态", "句法", "句子结构与组成成分"]
        analysis_blocks_html = ""
        
        for point in points:
            # Match "- **Point**: ... up to next point or end"
            pattern = rf'- \\*\\*{point}\\*\\*:?\\s*(.*?)(?=\\n- \\*\\*|$)'
            match = re.search(pattern, analysis_content, re.DOTALL)
            if match:
                point_detail = match.group(1).strip()
                # Convert sub-bullets
                detail_html = point_detail.replace('\\n  - ', '<li>').replace('\\n- ', '<li>')
                if '<li>' in detail_html:
                    detail_html = f'<ul class="analysis-list">{detail_html}</ul>'
                else:
                    detail_html = detail_html.replace('\\n', '<br>')
                
                analysis_blocks_html += f'''
                <div class="analysis-point">
                    <strong>{point}</strong>
                    <div class="analysis-content">{md_to_html_simple(detail_html)}</div>
                </div>
                '''

        rows_html += f'''
        <div class="section-row">
            <div class="pane left-pane">
                {img_tags}
                <div class="en-block">{md_to_html_simple(en_text)}</div>
                <div class="cn-block">{md_to_html_simple(cn_text)}</div>
            </div>
            <div class="pane right-pane">
                <div class="analysis-container">
                    {analysis_blocks_html}
                </div>
            </div>
        </div>
        '''

    # Clean up footer
    footer_html = md_to_html_simple(footer_content)
    footer_html = footer_html.replace('\\n', '<br>').replace('### ', '<h3>').replace('## ', '<h2>')

    final_content = html_template.format(
        title=title,
        header_tag=header_tag,
        rows_html=rows_html,
        footer_html=footer_html
    )

    output_path = md_path.replace("index.md", "interactive.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"Refined Interactive HTML generated at: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 study_viewer_gen.py <path_to_index.md>")
    else:
        generate_html(sys.argv[1])
