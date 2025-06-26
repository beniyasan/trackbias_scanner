#!/usr/bin/env python3
import asyncio
import json
import sys
import re
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
from typing import Dict, List, Any


def extract_race_id(url: str) -> str:
    """Extract race_id from URL"""
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        race_id = query_params.get('race_id', [''])[0]
        return race_id
    except Exception:
        return "unknown"


def detect_race_type(url: str) -> str:
    """Detect if this is NAR (local) or JRA (central) racing"""
    if "nar.netkeiba.com" in url:
        return "nar"
    elif "race.netkeiba.com" in url:
        return "jra"
    else:
        return "unknown"


async def scrape_race_data(url: str) -> Dict[str, Any]:
    """
    Scrape race result data from netkeiba URL
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Set longer timeout
            page.set_default_timeout(60000)
            
            # Navigate to the page with longer timeout
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Detect race type and extract race_id
            race_type = detect_race_type(url)
            race_id = extract_race_id(url)
            
            # Extract race metadata
            race_info = await extract_race_info(page, race_type)
            
            # Extract race results
            horses_data = await extract_horses_data(page, race_type)
            
            # Extract corner passing order
            corner_data = await extract_corner_data(page)
            
            # Extract lap times
            lap_times = await extract_lap_times(page)
            
            # Create final data structure
            result = {
                "race_url": url,
                "race_id": race_id,
                "race_type": race_type,
                "race_info": race_info,
                "horses": horses_data,
                "corner_passing_order": corner_data,
                "lap_times": lap_times
            }
            
            return result
            
        finally:
            await browser.close()


async def extract_race_info(page, race_type: str) -> Dict[str, Any]:
    """Extract race metadata from the page header"""
    race_info = {}
    
    try:
        # Extract race name/title
        if race_type == "nar":
            race_title_selector = '.RaceName'
        else:  # JRA
            race_title_selector = '.RaceName'
        
        race_title_elem = await page.query_selector(race_title_selector)
        if race_title_elem:
            race_info["race_name"] = (await race_title_elem.inner_text()).strip()
        
        # Extract race details from RaceData01 section (distance, track condition)
        race_data_items = await page.query_selector_all('.RaceData01 span')
        
        for item in race_data_items:
            text = (await item.inner_text()).strip()
            
            # Distance extraction (e.g., "ダ1500m")
            if 'm' in text and ('ダ' in text or '芝' in text):
                race_info["distance"] = text
            # Track condition (e.g., "良", "稍重", "重", "不良")
            elif text in ['良', '稍重', '重', '不良']:
                race_info["track_condition"] = text
        
        # Extract class information from RaceData02 section
        race_data2_items = await page.query_selector_all('.RaceData02 span')
        for item in race_data2_items:
            text = (await item.inner_text()).strip()
            # Class information (e.g., "サラ系一般 A2", "G1", "オープン")
            if ('A' in text and any(char.isdigit() for char in text)) or \
               'サラ系' in text or text in ['新馬', '未勝利', '1勝クラス', '2勝クラス', '3勝クラス', 'オープン', 'G3', 'G2', 'G1']:
                race_info["race_class"] = text
        
        # Extract race number from RaceNum
        race_num_elem = await page.query_selector('.RaceNum')
        if race_num_elem:
            race_num_text = (await race_num_elem.inner_text()).strip()
            # Extract just the number part (e.g., "11R" -> "11")
            race_num_match = re.search(r'(\d+)R?', race_num_text)
            if race_num_match:
                race_info["race_number"] = race_num_match.group(1)
        
        # Extract date from page title (YYYY年MM月DD日 format)
        title_elem = await page.query_selector('title')
        if title_elem:
            title_text = (await title_elem.inner_text()).strip()
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title_text)
            if date_match:
                year, month, day = date_match.groups()
                race_info["race_date"] = f"{year}/{month.zfill(2)}/{day.zfill(2)}"
        
        # Fallback: try to extract from page title
        if not race_info.get("race_name"):
            title_elem = await page.query_selector('title')
            if title_elem:
                title_text = await title_elem.inner_text()
                race_info["page_title"] = title_text.strip()
        
    except Exception as e:
        print(f"Error extracting race info: {e}")
    
    return race_info


async def extract_horses_data(page, race_type: str) -> List[Dict[str, Any]]:
    """Extract individual horse data from the results table"""
    horses = []
    
    # Different selectors for NAR vs JRA
    if race_type == "nar":
        table_selector = 'table.RaceTable01.ResultMain'
        table_rows_selector = 'table.RaceTable01.ResultMain tbody tr'
    else:  # JRA or unknown
        table_selector = 'table.RaceTable01.RaceCommon_Table'
        table_rows_selector = 'table.RaceTable01.RaceCommon_Table tbody tr'
    
    # Wait for the results table to load with multiple attempts
    try:
        await page.wait_for_selector(table_selector, timeout=30000)
    except Exception:
        # Try alternative selectors
        try:
            if race_type == "nar":
                await page.wait_for_selector('table.RaceTable01', timeout=15000)
                table_rows_selector = 'table.RaceTable01 tbody tr'
            else:
                await page.wait_for_selector('table.RaceCommon_Table', timeout=15000)
                table_rows_selector = 'table.RaceCommon_Table tbody tr'
        except Exception as e:
            print(f"Could not find results table: {e}")
            return []
    
    # Find all table rows with horse data
    rows = await page.query_selector_all(table_rows_selector)
    
    for row in rows:
        try:
            # Get all cells in the row
            cells = await row.query_selector_all('td')
            
            # Different column structures for NAR vs JRA
            if race_type == "nar":
                # NAR: 着順, 枠, 馬番, 馬名, 性齢, 斤量, 騎手, タイム, 着差, 人気, 単勝オッズ, 後3F, 厩舎, 馬体重
                if len(cells) < 12:
                    continue
                time_index = 7
                last_3f_index = 11
                corner_passage_index = None
            else:
                # JRA: 着順, 枠, 馬番, 馬名, 性齢, 斤量, 騎手, タイム, 着差, 人気, 単勝オッズ, 後3F, コーナー通過順, 厩舎, 馬体重
                if len(cells) < 13:
                    continue
                time_index = 7
                last_3f_index = 11
                corner_passage_index = 12
            
            # Extract rank (着順) - first column
            rank_elem = await cells[0].query_selector('.Rank')
            rank = await rank_elem.inner_text() if rank_elem else ""
            
            # Extract frame number (枠番) - second column
            frame_elem = await cells[1].query_selector('div')
            frame = await frame_elem.inner_text() if frame_elem else ""
            
            # Extract horse number (馬番) - third column
            horse_num_elem = await cells[2].query_selector('div')
            horse_num = await horse_num_elem.inner_text() if horse_num_elem else ""
            
            # Extract horse name - fourth column
            horse_name_elem = await cells[3].query_selector('.Horse_Name a')
            horse_name = await horse_name_elem.inner_text() if horse_name_elem else ""
            
            # Extract time (タイム)
            time_elem = await cells[time_index].query_selector('.RaceTime')
            time = await time_elem.inner_text() if time_elem else ""
            
            # Extract last 3F (後3F)
            last_3f = await cells[last_3f_index].inner_text() if len(cells) > last_3f_index else ""
            
            # Extract corner passage order (for JRA only)
            corner_passage = ""
            if corner_passage_index and len(cells) > corner_passage_index:
                corner_passage_elem = await cells[corner_passage_index].query_selector('.PassageRate')
                corner_passage = await corner_passage_elem.inner_text() if corner_passage_elem else ""
            
            horse_data = {
                "rank": rank.strip(),
                "frame": frame.strip(),
                "horse_number": horse_num.strip(),
                "horse_name": horse_name.strip(),
                "time": time.strip(),
                "last_3f": last_3f.strip()
            }
            
            # Add corner passage for JRA
            if corner_passage:
                horse_data["corner_passage"] = corner_passage.strip()
            
            horses.append(horse_data)
            
        except Exception as e:
            print(f"Error extracting horse data: {e}")
            continue
    
    return horses


async def extract_corner_data(page) -> Dict[str, str]:
    """Extract corner passing order data"""
    corner_data = {}
    
    try:
        corner_rows = await page.query_selector_all('table.Corner_Num tr')
        
        for row in corner_rows:
            header = await row.query_selector('th strong')
            if header:
                corner_num = await header.inner_text()
                order_cell = await row.query_selector('td')
                if order_cell:
                    order_text = await order_cell.inner_text()
                    corner_data[f"corner_{corner_num}"] = order_text
                    
    except Exception as e:
        print(f"Error extracting corner data: {e}")
    
    return corner_data


async def extract_lap_times(page) -> Dict[str, List[str]]:
    """Extract lap time data"""
    lap_data = {}
    
    try:
        # Find the lap time table
        lap_table = await page.query_selector('table.Race_HaronTime')
        if lap_table:
            rows = await lap_table.query_selector_all('tbody tr')
            
            # Extract headers (distances)
            if len(rows) >= 1:
                headers = await rows[0].query_selector_all('th')
                distances = []
                for header in headers:
                    text = await header.inner_text()
                    distances.append(text)
                
                # Extract cumulative times
                if len(rows) >= 2:
                    cumulative_cells = await rows[1].query_selector_all('td')
                    cumulative_times = []
                    for cell in cumulative_cells:
                        text = await cell.inner_text()
                        cumulative_times.append(text)
                    
                    lap_data["distances"] = distances
                    lap_data["cumulative_times"] = cumulative_times
                
                # Extract interval times
                if len(rows) >= 3:
                    interval_cells = await rows[2].query_selector_all('td')
                    interval_times = []
                    for cell in interval_cells:
                        text = await cell.inner_text()
                        interval_times.append(text)
                    
                    lap_data["interval_times"] = interval_times
                    
    except Exception as e:
        print(f"Error extracting lap times: {e}")
    
    return lap_data


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scraper.py <race_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    try:
        print(f"Scraping data from: {url}")
        result = await scrape_race_data(url)
        
        # Extract race_id for filename
        race_id = result.get('race_id', 'unknown')
        
        # Save to JSON file with race_id in filename
        output_file = f"output/race_data_{race_id}.json"
        import os
        os.makedirs("output", exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"Data saved to: {output_file}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())