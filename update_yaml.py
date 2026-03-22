import os
import re
import yaml

def strip_markers(s):
    # s is the value part of a YAML line, e.g., "'\\b[0-9]+\\b'" or "\\b[0-9]+\\b"
    s = s.strip()
    if not s:
        return s
    
    # Detect original quotes
    quote = None
    if s.startswith("'") and s.endswith("'"):
        quote = "'"
        content = s[1:-1]
    elif s.startswith('"') and s.endswith('"'):
        quote = '"'
        content = s[1:-1]
    else:
        content = s

    # Strip markers
    while True:
        if content.startswith('\\b'):
            content = content[2:]
        elif content.startswith('^'):
            content = content[1:]
        else:
            break
    while True:
        if content.endswith('\\b'):
            content = content[:-2]
        elif content.endswith('$'):
            content = content[:-1]
        else:
            break
            
    if quote:
        return f"{quote}{content}{quote}"
    else:
        # If it was unquoted, check if it needs quoting now.
        # YAML values starting with [, {, *, &, !, |, >, -, ?, :, @, `, % are special.
        if any(content.startswith(c) for c in ['[', '{', '*', '&', '!', '|', '>', '-', '?', ':', '@', '`', '%']):
            return f"'{content}'"
        return content

def process_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    parts = re.split(r'^patterns:', content, flags=re.MULTILINE)
    if len(parts) < 2:
        return False
    
    header = parts[0]
    patterns_section = "patterns:" + "patterns:".join(parts[1:])
    
    entries = re.split(r'^(  - id:)', patterns_section, flags=re.MULTILINE)
    
    new_patterns_section_parts = [entries[0]]
    for i in range(1, len(entries), 2):
        sep = entries[i]
        entry_content = entries[i+1]
        full_entry = sep + entry_content
        
        # 1. Strip pattern:
        full_entry = re.sub(r'^(\s+pattern: )(.*)$', lambda m: f"{m.group(1)}{strip_markers(m.group(2))}", full_entry, flags=re.MULTILINE)
        
        # 2. Strip python:
        full_entry = re.sub(r'^(\s+python: )(.*)$', lambda m: f"{m.group(1)}{strip_markers(m.group(2))}", full_entry, flags=re.MULTILINE)
        
        # 3. Strip go:
        full_entry = re.sub(r'^(\s+go: )(.*)$', lambda m: f"{m.group(1)}{strip_markers(m.group(2))}", full_entry, flags=re.MULTILINE)
        
        # 4. Add match_type if not present
        if 'match_type:' not in full_entry:
            # Look for langs or go
            go_match = re.search(r'^(\s+go: )(.*)$', full_entry, flags=re.MULTILINE)
            if go_match:
                line = go_match.group(0)
                indent = len(re.match(r'^\s*', line).group(0))
                insertion = f"\n{' ' * (indent - 2)}match_type: \"exactly_matches\""
                insertion_point = go_match.end()
                full_entry = full_entry[:insertion_point] + insertion + full_entry[insertion_point:]
            else:
                pattern_match = re.search(r'^(\s+pattern: )(.*)$', full_entry, flags=re.MULTILINE)
                if pattern_match:
                    indent = len(re.match(r'^\s*', pattern_match.group(0)).group(0))
                    insertion = f"\n{' ' * indent}match_type: \"exactly_matches\""
                    insertion_point = pattern_match.end()
                    full_entry = full_entry[:insertion_point] + insertion + full_entry[insertion_point:]

        new_patterns_section_parts.append(full_entry)
        
    new_content = header + "".join(new_patterns_section_parts)
    
    try:
        yaml.safe_load(new_content)
    except Exception as e:
        print(f"Error validating {file_path}: {e}")
        return False

    with open(file_path, 'w') as f:
        f.write(new_content)
    return True

def main():
    regex_dir = 'regex'
    files_processed = 0
    for root, dirs, files in os.walk(regex_dir):
        for file in files:
            if file.endswith('.yml'):
                if process_file(os.path.join(root, file)):
                    files_processed += 1
    print(f"Processed {files_processed} files.")

if __name__ == '__main__':
    main()
