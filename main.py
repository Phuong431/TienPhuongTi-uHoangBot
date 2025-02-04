from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import sqlite3
from datetime import datetime, timedelta
import schedule
import threading
import time

# Thay YOUR_BOT_TOKEN bằng token API của bạn
TOKEN = "8156843536:AAHSfCPba2XjcRdoFKEF378E2sp9WAMMY0Q"

# Kết nối database
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

# Tạo bảng lưu chi tiêu
cursor.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category TEXT,
    amount REAL,
    date TEXT
)
''')
conn.commit()

# Lệnh /start: Chào mừng người dùng
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Xin chào! Tôi là bot quản lý chi tiêu.\n"
        "Bạn có thể nhập chi tiêu theo cú pháp sau:\n"
        "• `Số tiền Danh mục` (vd: `100k Ăn uống`)\n"
        "• `Danh mục Số tiền` (vd: `Ăn uống 100k`)\n\n"
        "Các lệnh khác:\n"
        "/help - Hướng dẫn chi tiết\n"
        "/report - Báo cáo tổng chi tháng\n"
        "/view YYYY-MM-DD - Báo cáo chi tiêu ngày\n"
        "/view YYYY-MM - Báo cáo chi tiêu tháng\n"
        "/delete - Xóa khoản chi (ID/ngày/tháng)"
    )

# Lệnh /help: Hướng dẫn sử dụng chi tiết
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📌 **Hướng dẫn sử dụng bot quản lý chi tiêu:**\n"
        "1. **Nhập khoản chi:**\n"
        "   • `Số tiền Danh mục` (vd: `100k Ăn uống`)\n"
        "   • `Danh mục Số tiền` (vd: `Ăn uống 100k`)\n\n"
        "2. **Xem báo cáo:**\n"
        "   • `/report` - Báo cáo tổng chi tháng hiện tại\n"
        "   • `/view YYYY-MM-DD` - Xem khoản chi trong một ngày cụ thể\n"
        "   • `/view YYYY-MM` - Xem khoản chi trong một tháng cụ thể\n\n"
        "3. **Xóa khoản chi:**\n"
        "   • `/delete ID` - Xóa một khoản chi theo ID\n"
        "   • `/delete YYYY-MM-DD` - Xóa tất cả khoản chi trong ngày\n"
        "   • `/delete YYYY-MM` - Xóa tất cả khoản chi trong tháng\n\n"
        "4. **Tự động báo cáo:**\n"
        "   • Bot sẽ tự động gửi báo cáo hàng ngày vào lúc 7h sáng.\n"
        "   • Bot sẽ gửi báo cáo tổng chi tháng vào ngày cuối cùng của tháng, lúc 23h."
    )

# Lưu chi tiêu và hiển thị tổng chi tháng
def save_expense(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    text = update.message.text.strip()
    
    try:
        # Tách số tiền và danh mục
        parts = text.split()
        if len(parts) < 2:
            raise ValueError
        
        # Kiểm tra số tiền và danh mục
        if parts[0].replace('k', '').replace('K', '').isdigit():
            amount = parts[0]
            category = " ".join(parts[1:])
        elif parts[-1].replace('k', '').replace('K', '').isdigit():
            category = " ".join(parts[:-1])
            amount = parts[-1]
        else:
            raise ValueError
        
        # Xử lý đơn vị K/k
        if amount.lower().endswith('k'):
            amount = float(amount[:-1]) * 1000
        else:
            amount = float(amount)
        
        # Lưu vào cơ sở dữ liệu
        cursor.execute("INSERT INTO expenses (user_id, category, amount, date) VALUES (?, ?, ?, DATE('now'))",
                       (user_id, category, amount))
        conn.commit()

        # Tính tổng chi của tháng
        cursor.execute('''
        SELECT SUM(amount) FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', DATE('now'))
        ''', (user_id,))
        total_monthly = cursor.fetchone()[0] or 0

        # Phản hồi thành công
        update.message.reply_text(
            f"✅ Đã ghi nhận khoản chi: {int(amount):,} VND vào danh mục '{category}'.\n"
            f"📊 Tổng chi tháng hiện tại: {int(total_monthly):,} VND."
        )
    except:
        # Phản hồi khi nhập sai định dạng
        update.message.reply_text(
            "⚠️ Sai định dạng! Vui lòng nhập theo cú pháp:\n"
            "`Số tiền Danh mục` hoặc `Danh mục Số tiền`\n"
            "Ví dụ:\n"
            "`100k Ăn uống`\n"
            "`Ăn uống 100k`",
            parse_mode="Markdown"
        )

# Báo cáo tổng chi tháng hiện tại
def report(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    cursor.execute('''
    SELECT category, amount, date FROM expenses
    WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', DATE('now'))
    ''', (user_id,))
    data = cursor.fetchall()
    
    if not data:
        update.message.reply_text("📊 Bạn chưa có khoản chi tiêu nào trong tháng này.")
        return
    
    report_text = "**📊 Báo cáo chi tiêu tháng này:**\n"
    total_spent = 0

    for row in data:
        category, amount, date = row
        report_text += f"• {category} ({date}): {int(amount):,} VND\n"
        total_spent += amount
    
    report_text += f"\n**Tổng chi tháng này:** {int(total_spent):,} VND"
    update.message.reply_text(report_text, parse_mode="Markdown")
