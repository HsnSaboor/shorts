import logging
import re
from typing import List, Dict
import xml.etree.ElementTree as ET
from lxml import html, etree
import random
from playwright.async_api import async_playwright, PlaywrightTimeoutError

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36"
]

RESOLUTIONS = [
    {"width": 1024, "height": 768},
    {"width": 1280, "height": 720},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1600, "height": 900}
]

BROWSERS = ["chromium"]

async def extract_video_data(video_id):
    logging.info(f"Extracting video data for video ID: {video_id}")
    async with async_playwright() as p:
        browser_type = random.choice(BROWSERS)
        browser = await getattr(p, browser_type).launch(
            headless=True,
            args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--disable-extensions", "--disable-plugins"]
        )

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport=random.choice(RESOLUTIONS),
            locale="en-US",
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True
        )

        await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["video", "audio", "font"] else route.continue_())

        page = await context.new_page()

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        await page.goto(video_url, wait_until="domcontentloaded", timeout=60000)

        if "m.youtube.com" in page.url:
            await page.goto(video_url.replace("m.youtube.com", "www.youtube.com"), wait_until="networkidle")

        expand_selector = 'tp-yt-paper-button#expand'

        try:
            await page.wait_for_selector(expand_selector, timeout=20000)
            expand_button = await page.query_selector(expand_selector)
            if expand_button:
                await expand_button.click()
        except PlaywrightTimeoutError:
            logging.warning("Expand button not found.")

        await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        await page.wait_for_timeout(8000)

        content = await page.content()
        tree = html.fromstring(content)

async def extract_heatmap_svgs(page):
    try:
        await page.wait_for_load_state('networkidle')
        logging.info("Network idle state reached")
    except Exception as e:
        logging.error(f"Timeout waiting for network idle: {e}")
        return f"Timeout waiting for network idle: {e}"

    try:
        await page.wait_for_selector('div.ytp-heat-map-container', state='hidden', timeout=30000)
    except Exception as e:
        logging.error(f"Timeout waiting for heatmap container: {e}")
        return f"Timeout waiting for heatmap container: {e}"

    heatmap_container = await page.query_selector('div.ytp-heat-map-container')
    if heatmap_container:
        heatmap_container_html = await heatmap_container.inner_html()
    else:
        return "Heatmap container not found"

    tree = html.fromstring(heatmap_container_html)
    heatmap_elements = tree.xpath('//div[@class="ytp-heat-map-chapter"]/svg')

    if not heatmap_elements:
        return "Heatmap SVG not found"

    total_width = sum(get_pixel_value(elem.attrib['width']) for elem in heatmap_elements)
    total_height = max(get_pixel_value(elem.attrib['height']) for elem in heatmap_elements)

    combined_svg = etree.Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': f'{total_width}px',
        'height': f'{total_height}px',
        'viewBox': f'0 0 {total_width} {total_height}'
    })

    current_x = 0
    for elem in heatmap_elements:
        width = get_pixel_value(elem.attrib['width'])
        height = get_pixel_value(elem.attrib['height'])

        group = etree.SubElement(combined_svg, 'g', {
            'transform': f'translate({current_x}, 0)'
        })

        for child in elem.getchildren():
            group.append(child)

        current_x += width

    combined_svg_str = etree.tostring(combined_svg, pretty_print=True).decode('utf-8')

    if not combined_svg_str or combined_svg_str.strip() == "":
        logging.error("Combined SVG heatmap content is empty or None")
        return "Combined SVG heatmap content is empty or None"

    return combined_svg_str

def get_pixel_value(value):
    if 'px' in value:
        return int(value.replace('px', ''))
    elif '%' in value:
        return int(float(value.replace('%', '')) * 10)
    else:
        raise ValueError(f"Unsupported width/height format: {value}")

def parse_svg_heatmap(heatmap_svg, video_duration_seconds, svg_width=1000, svg_height=1000):
    if not heatmap_svg or heatmap_svg.strip() == "":
        logging.error("SVG heatmap content is empty or None")
        return []
    try:
        tree = ET.ElementTree(ET.fromstring(heatmap_svg))
        root = tree.getroot()
    except ET.ParseError as e:
        logging.error(f"Failed to parse SVG heatmap: {e}")
        logging.error(f"SVG content: {heatmap_svg}")
        return []
    heatmap_points = []
    for g in root.findall('.//{http://www.w3.org/2000/svg}g'):
        for defs in g.findall('.//{http://www.w3.org/2000/svg}defs'):
            for path in defs.findall('.//{http://www.w3.org/2000/svg}path'):
                d_attr = path.attrib.get('d', '')
                coordinates = re.findall(r'[MC]([^MC]+)', d_attr)
                for segment in coordinates:
                    points = segment.strip().replace(',', ' ').split()
                    for i in range(0, len(points), 2):
                        x = float(points[i])
                        y = float(points[i + 1])
                        duration_seconds = (x / svg_width) * video_duration_seconds
                        attention = 100 - (y / svg_height) * 100
                        heatmap_points.append({'Attention': attention, 'duration': duration_seconds})
    return heatmap_points

def analyze_heatmap_data(heatmap_points: List[Dict[str, float]], threshold: float = 1.35) -> Dict[str, any]:
    if not heatmap_points or not all(isinstance(point, dict) and 'Attention' in point and 'duration' in point for point in heatmap_points):
        return {}
    total_attention = sum(point['Attention'] for point in heatmap_points)
    average_attention = total_attention / len(heatmap_points)
    significant_rises = []
    significant_falls = []
    rise_start = None
    fall_start = None
    for i, point in enumerate(heatmap_points):
        attention = point['Attention']
        duration = point['duration']
        if attention > average_attention + threshold:
            if rise_start is None:
                rise_start = duration
            if i == len(heatmap_points) - 1 or heatmap_points[i + 1]['Attention'] <= average_attention + threshold:
                significant_rises.append({'start': rise_start, 'end': duration})
                rise_start = None
        if attention < average_attention - threshold:
            if fall_start is None:
                fall_start = duration
            if i == len(heatmap_points) - 1 or heatmap_points[i + 1]['Attention'] >= average_attention - threshold:
                significant_falls.append({'start': fall_start, 'end': duration})
                fall_start = None
    return {
        'average_attention': average_attention,
        'significant_rises': significant_rises,
        'significant_falls': significant_falls,
        'total_rises': len(significant_rises),
        'total_falls': len(significant_falls)
    }