#!/usr/bin/env python3
"""
Web Search Utility for Simple Signal CLI
Allows searching DuckDuckGo and the web with a premium, styled terminal output.
Can be run standalone or imported as a module.
"""

import json
import os
import sys
import re
import urllib.request
import urllib.parse
import threading
import time
from html.parser import HTMLParser

# Try to load theme configuration
THEME_NAME = "dark"
THEME = {
    "prompt_color": "\033[1;38;5;111m",  # Lavender/blue
    "text_color": "\033[38;5;253m",      # Off-white
    "user_color": "\033[38;5;244m",      # Slate gray
    "accent_color": "\033[38;5;111m",    # Lavender/blue
    "separator": "─" * 60,
    "success": "✅ ",
    "info": "ℹ️ ",
    "error": "❌ ",
    "warning": "⚠️ "
}

if os.path.exists("config.json"):
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            THEME_NAME = config.get("output", {}).get("theme", "dark")
    except Exception:
        pass

# Import CLIInterface themes if available to match CLI colors exactly
try:
    from ai_cli import CLIInterface
    if THEME_NAME in CLIInterface.THEMES:
        THEME = CLIInterface.THEMES[THEME_NAME]
except ImportError:
    pass


class SearchSpinner:
    """A search spinner that runs in a background thread"""
    def __init__(self, message: str = "Searching the web..."):
        self.message = message
        self.stop_event = threading.Event()
        self.thread = None
        self.accent = THEME.get("accent_color", "")
        self.text_color = THEME.get("text_color", "")

    def _spin(self):
        chars = ["/", "-", "\\", "|"]
        reset = "\033[0m"
        i = 0
        while not self.stop_event.is_set():
            char = chars[i % len(chars)]
            sys.stdout.write(f"\r{self.accent}🔍 {self.text_color}{self.message} {char}{reset}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        # Clear the spinner line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.stop_event.set()
            self.thread.join(timeout=1.0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class DDGHTMLParser(HTMLParser):
    """HTML Parser for DuckDuckGo static search page"""
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_result = None
        self.current_field = None  # 'title' or 'snippet'
        self.nesting_level = 0
        self.result_nesting = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_attr = attrs_dict.get("class", "")
        class_list = class_attr.split()
        
        # Check if entering a result body container
        if tag == "div" and "result" in class_list:
            self.current_result = {"title": "", "url": "", "snippet": ""}
            self.result_nesting = self.nesting_level
            
        self.nesting_level += 1
        
        if self.current_result is not None:
            # Result link and title
            if tag == "a" and "result__a" in class_list:
                self.current_field = "title"
                href = attrs_dict.get("href", "")
                self.current_result["url"] = self.clean_url(href)
            # Result snippet summary
            elif (tag == "a" or tag == "div") and "result__snippet" in class_list:
                self.current_field = "snippet"

    def handle_endtag(self, tag):
        self.nesting_level -= 1
        if self.current_result is not None:
            if self.nesting_level <= self.result_nesting:
                title_str = self.current_result["title"].strip()
                url_str = self.current_result["url"].strip()
                snippet_str = self.current_result["snippet"].strip()
                
                # Double-decode check to remove double HTML escaping if any
                title_clean = self.unescape_html_entities(title_str)
                snippet_clean = self.unescape_html_entities(snippet_str)
                
                if title_clean and url_str:
                    self.results.append({
                        "title": title_clean,
                        "url": url_str,
                        "snippet": snippet_clean
                    })
                self.current_result = None
            if tag == "a" or tag == "div":
                self.current_field = None

    def handle_data(self, data):
        if self.current_result is not None and self.current_field:
            self.current_result[self.current_field] += data

    def clean_url(self, url):
        """Extract the destination URL from DuckDuckGo redirect URL"""
        if "/l/?" in url:
            try:
                parsed = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed.query)
                if "uddg" in qs:
                    return qs["uddg"][0]
            except Exception:
                pass
        return url

    def unescape_html_entities(self, text):
        """Decodes standard HTML entities manually for double safety"""
        import html
        return html.unescape(text)


def search_ddg(query: str, num_results: int = 5) -> list:
    """
    Search DuckDuckGo using standard library urllib.
    Returns a list of dictionaries with 'title', 'url', and 'snippet'.
    """
    url = "https://html.duckduckgo.com/html/"
    data = urllib.parse.urlencode({"q": query}).encode("utf-8")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10.0) as response:
            html_content = response.read().decode("utf-8")
            parser = DDGHTMLParser()
            parser.feed(html_content)
            return parser.results[:num_results]
    except Exception as e:
        # Return empty list on failure, print details to stderr if verbose
        return []


def highlight_query_terms(text: str, query: str) -> str:
    """Highlights query words in the result snippet/title using bright styling"""
    # Exclude tiny words and short search syntax
    words = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 2]
    # Remove duplicates and sort from longest to shortest
    words = sorted(list(set(words)), key=len, reverse=True)
    
    highlight = "\033[1;38;5;220m"  # Bold yellow
    reset = "\033[0m"
    
    for word in words:
        pattern = re.compile(r'\b(' + re.escape(word) + r')\b', re.IGNORECASE)
        # Apply style keeping the original case
        text = pattern.sub(f"{highlight}\\1{reset}", text)
        
    return text


def format_hyperlink(text: str, url: str) -> str:
    """Formats a URL for clean display (clickable in most modern terminals)"""
    return url


def display_results(results: list, query: str):
    """Pretty print the search results inside the terminal console"""
    accent = THEME.get("accent_color", "")
    text_color = THEME.get("text_color", "")
    reset = "\033[0m"
    
    if not results:
        print(f"\n{THEME.get('error', '❌ ')} No results found or web request failed.")
        return

    print(f"\n{accent}{THEME.get('success', '✅ ')} Found {len(results)} web results for: {reset}{THEME.get('prompt_color', '')}{query}{reset}\n")
    print(accent + THEME["separator"] + reset)
    
    for idx, r in enumerate(results, 1):
        title = r["title"]
        url = r["url"]
        snippet = r["snippet"]
        
        # Highlight search terms
        highlighted_title = highlight_query_terms(title, query)
        highlighted_snippet = highlight_query_terms(snippet, query)
        
        # Format hyperlink URL
        clickable_url = format_hyperlink(url, url)
        
        # Index & Title
        print(f"  {accent}{idx}.{reset} \033[1;38;5;255m{highlighted_title}{reset}")
        # Link
        print(f"     {accent}Link:{reset} \033[4;38;5;75m{clickable_url}{reset}")
        # Snippet
        if snippet:
            print(f"     {text_color}{highlighted_snippet}{reset}")
        print(accent + THEME["separator"] + reset)
    print()


def main():
    """Main CLI entry point for standalone usage"""
    # Fix Windows console UTF-8 issues
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
            # Initialize Windows Virtual Terminal ANSI support
            os.system('')
        except Exception:
            pass

    # Command line argument check
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        with SearchSpinner(f"Searching web for: '{query}'..."):
            results = search_ddg(query)
        display_results(results, query)
        return

    # No arguments: enter interactive shell mode
    accent = THEME.get("accent_color", "")
    reset = "\033[0m"
    
    print("\n" + accent + THEME["separator"] + reset)
    print(f"{THEME.get('success', '✅ ')}  " + accent + "Simple Signal Web Search Utility" + reset)
    print(f"{THEME.get('info', 'ℹ️ ')}   " + accent + f"Active theme: {THEME_NAME}" + reset)
    print(accent + THEME["separator"] + reset)
    print(f"\n{THEME.get('info', 'ℹ️ ')} Type your query and press Enter to search.")
    print(f"{THEME.get('info', 'ℹ️ ')} Type 'exit' or 'quit' or press Ctrl+C to exit.\n")

    while True:
        try:
            query = input(f"{THEME.get('user_color', '')}Search Query:{reset} ").strip()
            if not query:
                continue
            if query.lower() in ["quit", "exit", "q"]:
                print(f"\n{THEME.get('info', 'ℹ️ ')} Exiting search utility. Goodbye!\n")
                break
                
            with SearchSpinner(f"Searching web for: '{query}'..."):
                results = search_ddg(query)
            display_results(results, query)
            
        except KeyboardInterrupt:
            print(f"\n\n{THEME.get('warning', '⚠️ ')} Search cancelled. Exiting...\n")
            break


if __name__ == "__main__":
    main()
