import streamlit as st
import pandas as pd
import time
import json
from datetime import datetime
from typing import Dict, List
from company_subsidiaries import (
    get_subsidiaries_hierarchy,
    print_hierarchy,
    save_hierarchy_to_file
)

# Page config
st.set_page_config(
    page_title="Company Subsidiary Research Tool",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

def format_hierarchy_for_display(hierarchy: Dict, level: int = 0) -> List[Dict]:
    display_data = []
    for company, data in hierarchy.get("subsidiaries", {}).items():
        display_data.append({
            "Company": company,
            "Level": level,
            "Indent": "  " * level + "├── " if level > 0 else "",
            "Has_Subsidiaries": len(data.get("subsidiaries", {})) > 0
        })
        if data.get("subsidiaries"):
            child_data = format_hierarchy_for_display(data, level + 1)
            display_data.extend(child_data)
    return display_data

def create_download_content(hierarchy: Dict) -> str:
    content = []
    content.append(f"SUBSIDIARY HIERARCHY FOR: {hierarchy['company']}")
    content.append(f"Total companies found: {hierarchy['total_companies_found']}")
    content.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    content.append("="*60)
    def add_level(data, indent=0):
        prefix = "  " * indent
        for company, info in data.get("subsidiaries", {}).items():
            content.append(f"{prefix}├── {company}")
            if info.get("subsidiaries"):
                add_level(info, indent + 1)
    add_level(hierarchy)
    return "\n".join(content)

def main():
    st.title("🏢 Company Subsidiary Research Tool")
    company_name = st.text_input("Enter Company Name", placeholder="e.g., Microsoft Corporation")
    max_depth = st.slider("Max Depth", 1, 10, 3)
    delay = st.slider("Delay Between Searches (s)", 1, 10, 3)
    max_workers = st.slider("Max Workers", 1, 5, 2)

    if st.button("🔍 Start Search"):
        with st.spinner("Searching..."):
            start = time.time()
            hierarchy = get_subsidiaries_hierarchy(company_name, max_depth, delay, max_workers)
            elapsed = time.time() - start

            st.success(f"Search completed in {elapsed:.1f}s, found {hierarchy['total_companies_found']} companies")
            st.json(hierarchy)

            st.download_button("📄 Download as TXT",
                               create_download_content(hierarchy),
                               file_name=f"{company_name}_subsidiary_hierarchy.txt")

            st.download_button("📋 Download as JSON",
                               json.dumps(hierarchy, indent=2),
                               file_name=f"{company_name}_subsidiary_hierarchy.json")

if __name__ == "__main__":
    main()
