# -*- coding: utf-8 -*-
"""
Master Builder for ENCYCLOPEDIE_TOME_2_SYSTEME_DUAL_HFT_ET_ONNX_VOLATILITE.md
Assembles all 7 encyclopedic modules into the target documentation files.
"""
import os
import sys

# Add parts directory to path
parts_dir = os.path.join(os.path.dirname(__file__), 'encyclopedia_parts')
if parts_dir not in sys.path:
    sys.path.insert(0, parts_dir)

import sec_header
import sec_part1
import sec_part2
import sec_part3
import sec_part4
import sec_part5
import sec_part6

def build():
    parts = [
        sec_header.get_content().strip(),
        sec_part1.get_content().strip(),
        sec_part2.get_content().strip(),
        sec_part3.get_content().strip(),
        sec_part4.get_content().strip(),
        sec_part5.get_content().strip(),
        sec_part6.get_content().strip()
    ]
    
    full_text = "\n\n---\n\n".join(parts) + "\n"
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_docs = os.path.normpath(os.path.join(base_dir, "..", "..", "docs", "ENCYCLOPEDIE_TOME_2_SYSTEME_DUAL_HFT_ET_ONNX_VOLATILITE.md"))
    target_brain = r"C:\Users\CHRIST\.gemini\antigravity\brain\5397a900-270a-4ff8-9f78-dac9b4fe3b2d\ENCYCLOPEDIE_TOME_2_SYSTEME_DUAL_HFT_ET_ONNX_VOLATILITE.md"
    
    # Write to project docs
    os.makedirs(os.path.dirname(target_docs), exist_ok=True)
    with open(target_docs, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f"Written: {target_docs} ({len(full_text)} characters, {len(full_text.encode('utf-8'))} bytes)")
    
    # Write to brain artifacts
    os.makedirs(os.path.dirname(target_brain), exist_ok=True)
    with open(target_brain, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f"Written: {target_brain}")

if __name__ == '__main__':
    build()
