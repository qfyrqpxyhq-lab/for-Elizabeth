import os
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Состояния для ConversationHandler
LAST_PERIOD, CYCLE_LENGTH = range(2)

class CycleTracker:
    def __init__(self):
        self.user_data = {}
    
    def calculate_dates(self, last_period, cycle_length=28):
        """Расчет всех важных дат цикла"""
        next_period = last_period + timedelta(days=cycle_length)
        ovulation = next_period - timedelta(days=14)
        fertile_start = ovulation - timedelta(days=5)
        fertile_end = ovulation
        pms_start = next_period - timedelta(days=7)
        
        return {
            'next_period': next_period,
            'ovulation': ovulation,
            'fertile_start': fertile_start,
            'fertile_end': fertile_end,
            'pms_start': pms_start
        }

tracker = CycleTracker()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['📅 Добавить цикл', '📊 Текущий цикл'],
        ['🔮 Прогноз', 'ℹ️ Помощь']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = """
🌸 *Трекер менструального цикла*

Я помогу отслеживать:
• Даты менструации 📅
• Овуляцию 🥚
• Фертильные дни 👶
• ПМС период 🌙

*Для начала нажмите "📅 Добавить цикл"*

⚠️ *Информационный характер. Консультируйтесь с врачом.*
    """
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📅 *Введите дату последних месячных в формате ДД.ММ.ГГГГ*\n\nНапример: 15.12.2024",
        parse_mode='Markdown'
    )
    return LAST_PERIOD

async def last_period_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        date_str = update.message.text
        last_period = datetime.strptime(date_str, '%d.%m.%Y')
        context.user_data['last_period'] = last_period
        
        await update.message.reply_text(
            "📊 *Какова длина вашего цикла?*\n\nВведите число дней (по умолчанию 28):",
            parse_mode='Markdown'
        )
        return CYCLE_LENGTH
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат! Используйте ДД.ММ.ГГГГ")
        return LAST_PERIOD

async def cycle_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cycle_len = int(update.message.text) if update.message.text.isdigit() else 28
        last_period = context.user_data['last_period']
        
        dates = tracker.calculate_dates(last_period, cycle_len)
        
        response = f"""
📋 *Ваш цикл рассчитан:*

🗓 *Последние месячные:* {last_period.strftime('%d.%m.%Y')}
📅 *Следующие месячные:* {dates['next_period'].strftime('%d.%m.%Y')}
🥚 *Овуляция:* {dates['ovulation'].strftime('%d.%m.%Y')}
👶 *Фертильные дни:* {dates['fertile_start'].strftime('%d.%m.%Y')} - {dates['fertile_end'].strftime('%d.%m.%Y')}
🌙 *ПМС период:* с {dates['pms_start'].strftime('%d.%m.%Y')}
        """
        
        await update.message.reply_text(response, parse_mode='Markdown')
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text("❌ Ошибка. Попробуйте снова.")
        return ConversationHandler.END

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'last_period' not in context.user_data:
        await update.message.reply_text("❌ Сначала добавьте данные через '📅 Добавить цикл'")
        return
    
    last_period = context.user_data['last_period']
    cycle_len = context.user_data.get('cycle_length', 28)
    dates = tracker.calculate_dates(last_period, cycle_len)
    
    today = datetime.now().date()
    days_until_period = (dates['next_period'].date() - today).days
    
    stats_text = f"""
📈 *Текущий цикл:*

✅ *Последние месячные:* {last_period.strftime('%d.%m.%Y')}
📅 *Следующие месячные:* {dates['next_period'].strftime('%d.%m.%Y')}
⏳ *До следующих:* {days_until_period} дней

🥚 *Овуляция:* {dates['ovulation'].strftime('%d.%m.%Y')}
👶 *Фертильное окно:* {dates['fertile_start'].strftime('%d.%m.%Y')} - {dates['fertile_end'].strftime('%d.%m.%Y')}
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
ℹ️ *Помощь*

*Как пользоваться:*
1. Нажмите "📅 Добавить цикл"
2. Введите дату последних месячных
3. Получите расчет на текущий цикл

*Команды:*
📊 Текущий цикл - показать расчеты
🔮 Прогноз - следующие даты

💖 *Берегите свое здоровье!*
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    application = Application.builder().token(os.environ['BOT_TOKEN']).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(📅 Добавить цикл)$'), start_tracking)],
        states={
            LAST_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, last_period_date)],
            CYCLE_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, cycle_length)],
        },
        fallbacks=[]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex('^(📊 Текущий цикл)$'), show_stats))
    application.add_handler(MessageHandler(filters.Regex('^(ℹ️ Помощь)$'), help_command))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
