import time
import threading
from typing import Dict, List, Set
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

# ---------------------------------
# Playwright Utilities
# ---------------------------------
def create_browser_context(playwright):
    """Create a new browser context with stealth-like settings."""
    browser = playwright.chromium.launch(headless=True, args=[
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-gpu"
    ])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 768}
    )
    return browser, context

def get_subsidiaries_single_search(company_name: str) -> List[str]:
    """Search Google for subsidiaries using Playwright."""
    query = quote_plus(f"{company_name} Subsidiary")
    url = f"https://www.google.com/search?q={query}"

    with sync_playwright() as p:
        browser, context = create_browser_context(p)
        page = context.new_page()
        try:
            page.goto(url, timeout=30000)
            page.wait_for_selector("#search", timeout=10000)

            elems = page.query_selector_all("a[data-entityname]")
            names = []
            for e in elems:
                val = e.get_attribute("data-entityname")
                if val and val.strip():
                    names.append(val.strip())

            return list(dict.fromkeys(names))  # dedupe
        except Exception as e:
            print(f"Error searching for {company_name}: {str(e)}")
            return []
        finally:
            context.close()
            browser.close()

# ---------------------------------
# Hierarchical Search
# ---------------------------------
def get_subsidiaries_hierarchy(company_name: str, max_depth: int = 10,
                               delay_between_searches: float = 3.0, max_workers: int = 2) -> Dict:
    """
    Get hierarchical subsidiaries for a company using multithreading with Playwright.
    """
    print(f"Starting hierarchical subsidiary research for: {company_name}")

    searched_companies: Set[str] = set()
    searched_lock = threading.Lock()

    hierarchy = {
        "company": company_name,
        "subsidiaries": {},
        "total_companies_found": 0
    }

    def search_single_company(company: str, current_depth: int) -> tuple:
        with searched_lock:
            company_lower = company.lower().strip()
            if company_lower in searched_companies:
                return company, [], True
            searched_companies.add(company_lower)

        print(f"Level {current_depth}: Searching for subsidiaries of '{company}'...")
        time.sleep(delay_between_searches)

        subsidiaries = get_subsidiaries_single_search(company)
        return company, subsidiaries, False

    def search_level(companies_to_search: List[str], current_depth: int) -> Dict:
        if current_depth > max_depth or not companies_to_search:
            return {}

        level_results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_company = {
                executor.submit(search_single_company, company, current_depth): company
                for company in companies_to_search
            }
            for future in as_completed(future_to_company):
                try:
                    company, subsidiaries, already_searched = future.result()
                    if already_searched:
                        continue

                    level_results[company] = {"subsidiaries": {}}
                    if subsidiaries:
                        if current_depth < max_depth:
                            next_level_results = search_level(subsidiaries, current_depth + 1)
                            level_results[company]["subsidiaries"] = next_level_results
                        else:
                            for sub in subsidiaries:
                                level_results[company]["subsidiaries"][sub] = {"subsidiaries": {}}
                except Exception as e:
                    print(f"Error searching for company: {e}")
        return level_results

    hierarchy["subsidiaries"] = search_level([company_name], 1)

    def count_companies(node):
        count = 1
        for _, data in node.get("subsidiaries", {}).items():
            count += count_companies(data)
        return count

    if hierarchy["subsidiaries"]:
        hierarchy["total_companies_found"] = (
            count_companies({"subsidiaries": hierarchy["subsidiaries"]}) - 1
        )
    return hierarchy

# ---------------------------------
# Utilities
# ---------------------------------
def print_hierarchy(hierarchy: Dict, indent: int = 0):
    prefix = "  " * indent
    if indent == 0:
        print("\n" + "="*60)
        print(f"SUBSIDIARY HIERARCHY FOR: {hierarchy['company']}")
        print(f"Total companies found: {hierarchy['total_companies_found']}")
        print("="*60)

    for company, data in hierarchy["subsidiaries"].items():
        print(f"{prefix}├── {company}")
        if data["subsidiaries"]:
            print_hierarchy(data, indent + 1)

def save_hierarchy_to_file(hierarchy: Dict, filename: str = None):
    if filename is None:
        filename = f"{hierarchy['company']}_subsidiary_hierarchy.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"SUBSIDIARY HIERARCHY FOR: {hierarchy['company']}\n")
        f.write(f"Total companies found: {hierarchy['total_companies_found']}\n")
        f.write("="*60 + "\n\n")

        def write_level(data, indent=0):
            prefix = "  " * indent
            for company, info in data["subsidiaries"].items():
                f.write(f"{prefix}├── {company}\n")
                if info["subsidiaries"]:
                    write_level(info, indent + 1)
        write_level(hierarchy)
    print(f"\nHierarchy saved to: {filename}")

if __name__ == "__main__":
    company = input("Enter Company Name: ").strip()
    hierarchy = get_subsidiaries_hierarchy(company, max_depth=3, delay_between_searches=2, max_workers=2)
    print_hierarchy(hierarchy)
    save_hierarchy_to_file(hierarchy)
