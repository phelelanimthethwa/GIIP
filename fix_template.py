import os

path = r"c:\Users\ACE\G\GIIR\templates\base.html"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "filename='css/style.css'" in line:
        start_idx = i
    # Look for "body {" but ensure it's the CSS rule, not something else. 
    # Usually it's "        body {" or similar.
    if "body {" in line and "{" in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Found anchors: Start {start_idx}, End {end_idx}")
    
    # Keep lines up to and including the CSS link
    new_lines = lines[:start_idx+1]
    
    # Insert new clean content
    new_content = [
        "\n",
        "    {% set primary_rgb = site_design.primary_color|replace('#', '')|string %}\n",
        "    {% if primary_rgb|length == 6 %}\n",
        "        {% set r = (primary_rgb[0:2]|int(base=16)) %}\n",
        "        {% set g = (primary_rgb[2:4]|int(base=16)) %}\n",
        "        {% set b = (primary_rgb[4:6]|int(base=16)) %}\n",
        "    {% else %}\n",
        "        {% set r, g, b = 0, 123, 255 %}\n",
        "    {% endif %}\n",
        "\n",
        "    <style>\n",
        "        /* CRITICAL LOGIN BUTTON POSTIONING */\n",
        "        @media (min-width: 769px) {\n",
        "            .nav-container {\n",
        "                position: relative !important;\n",
        "            }\n",
        "            /* Absolute positioning for login button on desktop */\n",
        "            .nav-links li:last-child {\n",
        "                position: absolute !important;\n",
        "                right: 0 !important;\n",
        "                top: 50% !important;\n",
        "                transform: translateY(-50%) !important;\n",
        "                margin: 0 !important;\n",
        "                z-index: 1002;\n",
        "            }\n",
        "        }\n",
        "\n",
        "        /* Mobile Reset */\n",
        "        @media (max-width: 768px) {\n",
        "            .nav-links li:last-child {\n",
        "                position: static !important;\n",
        "                transform: none !important;\n",
        "                margin-top: 1rem !important;\n",
        "                margin-left: 0 !important;\n",
        "            }\n",
        "        }\n",
        "\n",
        "        :root {\n",
        "            --primary-color: {{ site_design.primary_color }};\n",
        "            --primary-color-rgb: {{ r }}, {{ g }}, {{ b }};\n",
        "            --secondary-color: {{ site_design.secondary_color }};\n",
        "            --accent-color: {{ site_design.accent_color }};\n",
        "            --text-color: {{ site_design.text_color }};\n",
        "            --background-color: {{ site_design.background_color }};\n",
        "            --header-background: {{ site_design.header_background }};\n",
        "            --footer-background: {{ site_design.footer_background }};\n",
        "            --hero-text-color: {{ site_design.hero_text_color }};\n",
        "        }\n",
        "\n",
        "        " # Indentation for the following body {
    ]
    
    new_lines.extend(new_content)
    
    # Append the rest of the file starting from line with "body {"
    # We stripped the indentation in the last line of new_content to match?
    # Actually lines[end_idx] contains "        body {\n" presumably.
    # So we just append lines[end_idx:]
    
    new_lines.extend(lines[end_idx:])
    
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Successfully patched base.html")
    
else:
    print(f"Could not find anchors. start={start_idx}, end={end_idx}")
