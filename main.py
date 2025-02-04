from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import sqlite3
from datetime import datetime
import schedule
import threading
import time

# Thay YOUR_BOT_TOKEN bằng token API của bạn
TOKEN = "8156843536:AAHSfCPba2XjcRdoFKEF378E2sp9WAMMY0Q"

# Kết nối cơ sở dữ liệu SQLite
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

# Tạo bảng lưu thông tin thu chi
cursor.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    description TEXT,
    amount REAL,
    type TEXT,
    created_at TEXT
)
''')
conn.commit()

# Lệnh /start: Chào mừng người dùng
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Xin chào! Tôi là bot quản lý thu chi.\n"
        "Bạn có thể sử dụng các lệnh sau để quản lý tài chính:\n"
        "• /add [thu/chi] [số tiền] [mô tả] - Thêm khoản thu/chi\n"
        "• /view - Xem tổng thu/chi hôm nay\n"
        "• /report - Xem báo cáo tổng thu/chi tháng này\n"
        "• /delete [ID] - Xóa khoản thu/chi\n"
    )

# Lệnh /add: Thêm khoản thu/chi
def add_expense(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    args = context.args

    if len(args) < 3:
        update.message.reply_text("⚠️ Vui lòng nhập đúng cú pháp: /add [thu/chi] [số tiền] [mô tả].")
        return

    try:
        type = args[0].lower()
        amount = float(args[1])
        description = " ".join(args[2:])
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if type not in ["thu", "chi"]:
            update.message.reply_text("⚠️ Loại phải là 'thu' hoặc 'chi'.")
            return

        cursor.execute('''
        INSERT INTO expenses (user_id, description, amount, type, created_at)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, description, amount, type, created_at))
        conn.commit()

        update.message.reply_text(
            f"✅ Đã ghi nhận: {type.upper()} {amount:,.0f} VND - {description} (Lúc: {created_at})."
        )

    except ValueError:
        update.message.reply_text("⚠️ Số tiền phải là một số hợp lệ.")

# Lệnh /view: Xem tổng thu/chi hôm nay
def view_today(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute('''
    SELECT type, SUM(amount) FROM expenses
    WHERE user_id = ? AND DATE(created_at) = ?
    GROUP BY type
    ''', (user_id, today))
    data = cursor.fetchall()

    if not data:
        update.message.reply_text("📅 Hôm nay bạn chưa có khoản thu/chi nào.")
        return

    message = "**📅 Tổng thu/chi hôm nay:**\n"
    for row in data:
        message += f"• {row[0].capitalize()}: {row[1]:,.0f} VND\n"
    update.message.reply_text(message, parse_mode="Markdown")

# Lệnh /report: Báo cáo tổng thu/chi tháng này
def report_monthly(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    current_month = datetime.now().strftime("%Y-%m")

    cursor.execute('''
    SELECT type, SUM(amount) FROM expenses
    WHERE user_id = ? AND strftime('%Y-%m', created_at) = ?
    GROUP BY type
    ''', (user_id, current_month))
    data = cursor.fetchall()

    if not data:
        update.message.reply_text("📊 Bạn chưa có khoản thu/chi nào trong tháng này.")
        return

    message = "**📊 Báo cáo thu/chi tháng này:**\n"
    for row in data:
        message += f"• {row[0].capitalize()}: {row[1]:,.0f} VND\n"
    update.message.reply_text(message, parse_mode="Markdown")

# Lệnh /delete: Xóa khoản thu/chi
def delete_expense(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    args = context.args

    if len(args) != 1 or not args[0].isdigit():
        update.message.reply_text("⚠️ Vui lòng nhập ID khoản chi cần xóa. Ví dụ: /delete 1")
        return

    expense_id = int(args[0])
    cursor.execute('''
    DELETE FROM expenses WHERE id = ? AND user_id = ?
    ''', (expense_id, user_id))
    conn.commit()

    if cursor.rowcount == 0:
        update.message.reply_text(f"⚠️ Không tìm thấy khoản thu/chi với ID {expense_id}.")
    else:
        update.message.reply_text(f"✅ Đã xóa khoản thu/chi với ID {expense_id}.")

# Tự động báo cáo tổng thu/chi mỗi ngày và cuối tháng
def daily_summary():
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT DISTINCT user_id FROM expenses")
    users = cursor.fetchall()

    for user in users:
        user_id = user[0]
        cursor.execute('''
        SELECT type, SUM(amount) FROM expenses
        WHERE user_id = ? AND DATE(created_at) = ?
        GROUP BY type
        ''', (user_id, today))
        data = cursor.fetchall()

        if data:
            message = "**📅 Báo cáo thu/chi hôm nay:**\n"
            for row in data:
                message += f"• {row[0].capitalize()}: {row[1]:,.0f} VND\n"
            updater.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")

def monthly_summary():
    current_month = datetime.now().strftime("%Y-%m")
    cursor.execute("SELECT DISTINCT user_id FROM expenses")
    users = cursor.fetchall()

    for user in users:
        user_id = user[0]
        cursor.execute('''
        SELECT type, SUM(amount) FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', created_at) = ?
        GROUP BY type
        ''', (user_id, current_month))
        data = cursor.fetchall()

        if data:
            message = "**📊 Báo cáo tổng thu/chi tháng này:**\n"
            for row in data:
                message += f"• {row[0].capitalize()}: {row[1]:,.0f} VND\n"
            updater.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")

# Lập lịch báo cáo tự động
def schedule_tasks():
    schedule.every().day.at("00:00").do(daily_summary)  # 7h sáng Việt Nam
    schedule.every().month.at("23:00").do(monthly_summary)

    while True:
        schedule.run_pending()
        time.sleep(1)

# Chạy bot
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("add", add_expense))
dispatcher.add_handler(CommandHandler("view", view_today))
dispatcher.add_handler(CommandHandler("report", report_monthly))
dispatcher.add_handler(CommandHandler("delete", delete_expense))

threading.Thread(target=schedule_tasks, daemon=True).start()
updater.start_polling()
updater.idle()
