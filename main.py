from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import sqlite3
from datetime import datetime
import os

# Token của bot Telegram
TOKEN = os.getenv("TOKEN")  # Lấy token từ biến môi trường trên Render

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

# Lưu chi tiêu và hiển thị tổng chi tháng
def save_expense(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    text = update.message.text.strip()
    try:
        parts = text.split()
        if len(parts) < 2:
            raise ValueError
        
        if parts[0].replace('k', '').replace('K', '').isdigit():
            amount = parts[0]
            category = " ".join(parts[1:])
        elif parts[-1].replace('k', '').replace('K', '').isdigit():
            category = " ".join(parts[:-1])
            amount = parts[-1]
        else:
            raise ValueError
        
        if amount.lower().endswith('k'):
            amount = float(amount[:-1]) * 1000
        else:
            amount = float(amount)
        
        cursor.execute("INSERT INTO expenses (user_id, category, amount, date) VALUES (?, ?, ?, DATE('now'))",
                       (user_id, category, amount))
        conn.commit()

        cursor.execute('''
        SELECT SUM(amount) FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', DATE('now'))
        ''', (user_id,))
        total_monthly = cursor.fetchone()[0] or 0

        update.message.reply_text(
            f"✅ Đã ghi nhận khoản chi: {int(amount):,} VND vào danh mục '{category}'.\n"
            f"📊 Tổng chi tháng hiện tại: {int(total_monthly):,} VND."
        )
    except ValueError:
        update.message.reply_text(
            "⚠️ Sai định dạng! Vui lòng nhập theo cú pháp:\n"
            "`Số tiền Danh mục` hoặc `Danh mục Số tiền`\n"
            "Ví dụ:\n"
            "`100k Ăn uống`\n"
            "`Ăn uống 100k`",
            parse_mode="Markdown"
        )

# Báo cáo tổng chi tháng
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

# Lệnh /view: Xem chi tiêu ngày/tháng
def view_expenses(update: Update, context: CallbackContext):
    # Hàm đã thêm ở trên
    pass

# Cấu hình Webhook
PORT = int(os.environ.get("PORT", "8443"))
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("report", report))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, save_expense))

updater.start_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN
)
updater.bot.set_webhook(f"https://tienphuongti-uhoangbot.onrender.com/{TOKEN}")
updater.idle()
