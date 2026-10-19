# 美股觀察清單自動掃描

每天約南澳當地 09:00 由 GitHub Actions「Update Watchlist Signals」執行。已處理 ACST/ACDT 夏令時間切換，但 GitHub 排程可能延遲，無法保證整點完成。也可到 Actions → Update Watchlist Signals → Run workflow 立即觸發。

原本 watchlist.html 的 11 個主題組保持不變；程式直接從網頁讀取股票代號，不另外維護重複清單。使用 SEC EDGAR 8-K 申報資料及 Google News RSS。RSS 只接受經設定的可信媒體及新聞稿通訊社，仍屬「待核實的線索」；SEC 只驗證文件類型，不代表核實內容或財務影響。新訊號一律用 🟡，不自動推薦買賣。

watchlist-signals.json 保留舊訊號並排除重複事件；watchlist-status.json 顯示最後掃描時間、成功來源數、新增數量、來源異常。若所有來源失敗則不覆蓋舊資料，工作流程標示失敗。

此工具無法保證不漏報；免費新聞 RSS 可能受限制、滯後，SEC 可能阻擋存取。請在投資決策前閱讀原始公告。測試方式：python -m unittest discover -s tests -v。
