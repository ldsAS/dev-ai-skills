# scripts/check_updates.py
import urllib.request
import json
import os
import sys

def get_latest_claude_version():
    url = "https://registry.npmjs.org/@anthropic-ai/claude-code/latest"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("version"), data.get("description", "")
    except Exception as e:
        print(f"Error fetching NPM data: {e}", file=sys.stderr)
        return None, None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    baseline_path = os.path.join(script_dir, "last_checked.json")
    
    # 載入基準版本資訊
    if os.path.exists(baseline_path):
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline = json.load(f)
    else:
        baseline = {"claude_code": "0.0.0"}

    old_version = baseline.get("claude_code", "0.0.0")
    new_version, desc = get_latest_claude_version()

    has_update = False
    report_lines = []

    if new_version and new_version != old_version:
        has_update = True
        report_lines.append(f"⚠️ 偵測到 Claude Code 版本更新！")
        report_lines.append(f"- 舊版本: {old_version}")
        report_lines.append(f"- 新版本: {new_version}")
        report_lines.append(f"- 描述: {desc}")
        report_lines.append(f"- NPM 連結: https://www.npmjs.com/package/@anthropic-ai/claude-code")
        report_lines.append("")
        
        # 更新基準值
        baseline["claude_code"] = new_version
    else:
        report_lines.append("✅ Claude Code 運作機制與路徑暫無異動。")
        report_lines.append(f"- 目前基準版本: {old_version}")

    # 輸出報告給 GitHub Actions 讀取
    print("\n".join(report_lines))

    # 如果有異動，寫回檔案中以更新基準點
    if has_update:
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
            
        # 印出警示訊號給 Shell grep 偵測
        print("\n[SIGNAL: UPDATE_DETECTED]")

if __name__ == "__main__":
    main()
