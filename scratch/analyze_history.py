import os
import shutil
import sqlite3
import tempfile
import urllib.parse
from datetime import datetime, timedelta

def get_chrome_history():
    local_app_data = os.environ.get('LOCALAPPDATA')
    if not local_app_data:
        print("LOCALAPPDATA not found")
        return
        
    history_path = os.path.join(local_app_data, 'Google', 'Chrome', 'User Data', 'Default', 'History')
    if not os.path.exists(history_path):
        print(f"Chrome Default History not found at {history_path}")
        user_data_dir = os.path.join(local_app_data, 'Google', 'Chrome', 'User Data')
        if os.path.exists(user_data_dir):
            print("Checking other profiles...")
            for d in os.listdir(user_data_dir):
                if os.path.exists(os.path.join(user_data_dir, d, 'History')):
                    print(f"History found in profile: {d}")
        return
    
    temp_dir = tempfile.gettempdir()
    temp_history = os.path.join(temp_dir, 'chrome_history_copy.sqlite')
    try:
        shutil.copy2(history_path, temp_history)
        print("Successfully copied history db to temp dir.")
    except Exception as e:
        print(f"Failed to copy history file: {e}")
        return
        
    try:
        conn = sqlite3.connect(temp_history)
        c = conn.cursor()
        
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        epoch_diff = 11644473600000000
        one_week_ago_chrome = int(one_week_ago.timestamp() * 1000000) + epoch_diff
        print(f"Querying for visits after {one_week_ago} (Chrome Time: {one_week_ago_chrome})")

        c.execute("PRAGMA table_info(visits)")
        columns = [row[1] for row in c.fetchall()]
        has_duration = 'visit_duration' in columns

        query = f"""
        SELECT 
            urls.url, 
            COUNT(visits.id) as visit_count,
            {"SUM(visits.visit_duration)" if has_duration else "0"} as total_duration
        FROM urls
        JOIN visits ON urls.id = visits.url
        WHERE visits.visit_time > {one_week_ago_chrome}
        GROUP BY urls.url
        """
        
        c.execute(query)
        results = c.fetchall()
        
        domain_stats = {}
        
        for url, count, duration in results:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc
            if not domain:
                continue
            
            if domain not in domain_stats:
                domain_stats[domain] = {'count': 0, 'duration_ms': 0}
                
            domain_stats[domain]['count'] += count
            if duration:
                domain_stats[domain]['duration_ms'] += duration / 1000.0

        sorted_domains = sorted(domain_stats.items(), key=lambda x: (x[1]['duration_ms'], x[1]['count']), reverse=True)
        
        print("\nTop 20 Domains:")
        print(f"{'Domain':<40} | {'Visits':<8} | {'Estimated Time Spent':<20}")
        print("-" * 75)
        for domain, stats in sorted_domains[:20]:
            count = stats['count']
            duration_ms = stats['duration_ms']
            if duration_ms > 0:
                seconds = duration_ms / 1000.0
                if seconds > 3600:
                    time_str = f"{seconds/3600:.1f} hours"
                elif seconds > 60:
                    time_str = f"{seconds/60:.1f} minutes"
                else:
                    time_str = f"{seconds:.1f} seconds"
            else:
                time_str = "Unknown"
                
            print(f"{domain:<40} | {count:<8} | {time_str:<20}")
            
    except Exception as e:
        print("Error reading db:", e)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    get_chrome_history()
