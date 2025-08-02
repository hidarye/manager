import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

from database import create_tables, SessionLocal, Channel, ScheduledPost, BotSettings
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

# Global scheduler
scheduler = AsyncIOScheduler()

class TelegramChannelBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.user_states: Dict[int, Dict] = {}
        
    def get_user_state(self, user_id: int) -> Dict:
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        return self.user_states[user_id]
    
    def clear_user_state(self, user_id: int):
        if user_id in self.user_states:
            del self.user_states[user_id]

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_USER_ID:
            await update.message.reply_text("⚠️ غير مصرح لك باستخدام هذا البوت")
            return
            
        keyboard = [
            [InlineKeyboardButton("📝 إنشاء منشور جديد", callback_data="create_post")],
            [InlineKeyboardButton("📋 إدارة القنوات", callback_data="manage_channels")],
            [InlineKeyboardButton("⏰ المنشورات المجدولة", callback_data="scheduled_posts")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🤖 مرحباً بك في بوت إدارة القنوات

📌 الميزات المتاحة:
• إنشاء ونشر المنشورات
• دعم الماركداون والأزرار التفاعلية
• جدولة المنشورات
• إدارة متعددة القنوات
• حذف تلقائي للمنشورات
• إعدادات مخصصة لكل قناة

اختر ما تريد القيام به:
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if user_id != ADMIN_USER_ID:
            await query.edit_message_text("⚠️ غير مصرح لك باستخدام هذا البوت")
            return
            
        data = query.data
        
        if data == "create_post":
            await self.start_post_creation(query)
        elif data == "manage_channels":
            await self.show_channels_menu(query)
        elif data == "scheduled_posts":
            await self.show_scheduled_posts(query)
        elif data == "settings":
            await self.show_settings_menu(query)
        elif data == "add_channel":
            await self.add_channel_prompt(query)
        elif data.startswith("remove_channel_"):
            channel_id = data.split("_", 2)[2]
            await self.confirm_remove_channel(query, channel_id)
        elif data.startswith("confirm_remove_"):
            channel_id = data.split("_", 2)[2]
            await self.remove_channel(query, channel_id)
        elif data.startswith("channel_settings_"):
            channel_id = data.split("_", 2)[2]
            await self.show_channel_settings(query, channel_id)
        elif data == "back_to_main":
            await self.start(update, context)
        elif data == "post_content":
            await self.request_post_content(query)
        elif data == "post_buttons":
            await self.request_post_buttons(query)
        elif data == "skip_buttons":
            await self.skip_buttons(query)
        elif data == "select_channels":
            await self.show_channel_selection(query)
        elif data.startswith("toggle_channel_"):
            channel_id = data.split("_", 2)[2]
            await self.toggle_channel_selection(query, channel_id)
        elif data == "confirm_channels":
            await self.show_scheduling_options(query)
        elif data == "post_now":
            await self.set_post_now(query)
        elif data == "schedule_post":
            await self.request_schedule_time(query)
        elif data == "no_auto_delete":
            await self.set_no_auto_delete(query)
        elif data == "set_auto_delete":
            await self.request_auto_delete_time(query)
        elif data == "post_settings":
            await self.show_post_settings(query)
        elif data.startswith("toggle_"):
            setting = data.split("_", 1)[1]
            if setting in ["silent", "pin"]:
                await self.toggle_post_setting(query, setting)
            elif setting.startswith("header_"):
                channel_id = setting.split("_", 1)[1]
                await self.toggle_channel_header(query, channel_id)
            elif setting.startswith("footer_"):
                channel_id = setting.split("_", 1)[1]
                await self.toggle_channel_footer(query, channel_id)
        elif data.startswith("edit_header_"):
            channel_id = data.split("_", 2)[2]
            await self.edit_channel_header(query, channel_id)
        elif data.startswith("edit_footer_"):
            channel_id = data.split("_", 2)[2]
            await self.edit_channel_footer(query, channel_id)
        elif data == "finalize_post":
            await self.finalize_post(query)

    async def start_post_creation(self, query):
        """Start the post creation process"""
        user_id = query.from_user.id
        self.clear_user_state(user_id)
        state = self.get_user_state(user_id)
        state['creating_post'] = True
        state['post_data'] = {
            'content': '',
            'buttons': [],
            'selected_channels': [],
            'scheduled_time': None,
            'auto_delete_time': None,
            'silent': False,
            'pin_message': False
        }
        
        keyboard = [
            [InlineKeyboardButton("📝 إدخال النص", callback_data="post_content")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
📝 إنشاء منشور جديد

ابدأ بإدخال محتوى المنشور. يمكنك استخدام:
• **نص عريض**
• *نص مائل*
• `كود`
• [رابط](URL)
• وجميع تنسيقات الماركداون الأخرى
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def request_post_content(self, query):
        """Request post content from user"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['waiting_for'] = 'content'
        
        await query.edit_message_text(
            "📝 أرسل محتوى المنشور الآن:\n\n"
            "💡 يمكنك استخدام تنسيق الماركداون\n"
            "مثال: **عريض** *مائل* `كود` [رابط](https://example.com)"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.effective_user.id
        if user_id != ADMIN_USER_ID:
            return
            
        state = self.get_user_state(user_id)
        waiting_for = state.get('waiting_for')
        
        if waiting_for == 'content':
            await self.handle_post_content(update)
        elif waiting_for == 'buttons':
            await self.handle_post_buttons(update)
        elif waiting_for == 'schedule_time':
            await self.handle_schedule_time(update)
        elif waiting_for == 'auto_delete_time':
            await self.handle_auto_delete_time(update)
        elif waiting_for == 'channel_forward':
            await self.handle_channel_forward(update)
        elif waiting_for == 'header_text':
            await self.handle_header_text(update)
        elif waiting_for == 'footer_text':
            await self.handle_footer_text(update)

    async def handle_post_content(self, update: Update):
        """Handle post content input"""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        
        content = update.message.text
        state['post_data']['content'] = content
        state['waiting_for'] = None
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة أزرار", callback_data="post_buttons")],
            [InlineKeyboardButton("⏭️ تخطي الأزرار", callback_data="skip_buttons")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        preview_text = f"✅ تم حفظ المحتوى:\n\n{content[:200]}{'...' if len(content) > 200 else ''}\n\n"
        preview_text += "هل تريد إضافة أزرار تفاعلية؟"
        
        await update.message.reply_text(preview_text, reply_markup=reply_markup)

    async def request_post_buttons(self, query):
        """Request inline buttons from user"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['waiting_for'] = 'buttons'
        
        text = """
🔘 إضافة أزرار تفاعلية

أرسل الأزرار بالتنسيق التالي:
نص الزر | رابط الزر
نص الزر | رابط الزر

مثال:
موقعنا | https://example.com
تواصل معنا | https://t.me/username

💡 لإضافة أزرار في نفس الصف، اتركهم في نفس السطر مفصولين بـ |
مثال:
زر1 | link1 | زر2 | link2
        """
        
        await query.edit_message_text(text)

    async def handle_post_buttons(self, update: Update):
        """Handle inline buttons input"""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        
        buttons_text = update.message.text
        buttons = self.parse_buttons(buttons_text)
        
        if not buttons:
            await update.message.reply_text("❌ تنسيق الأزرار غير صحيح. حاول مرة أخرى.")
            return
            
        state['post_data']['buttons'] = buttons
        state['waiting_for'] = None
        
        await self.show_channel_selection(update)

    def parse_buttons(self, text: str) -> List[List[Dict]]:
        """Parse button text into button structure"""
        try:
            buttons = []
            lines = text.strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                    
                row = []
                parts = line.split('|')
                
                i = 0
                while i < len(parts) - 1:
                    button_text = parts[i].strip()
                    button_url = parts[i + 1].strip()
                    
                    if button_text and button_url:
                        row.append({'text': button_text, 'url': button_url})
                    
                    i += 2
                
                if row:
                    buttons.append(row)
            
            return buttons
        except:
            return []

    async def skip_buttons(self, query):
        """Skip buttons and proceed to channel selection"""
        await self.show_channel_selection(query)

    async def show_channel_selection(self, query_or_update):
        """Show channel selection for posting"""
        if hasattr(query_or_update, 'edit_message_text'):
            query = query_or_update
            user_id = query.from_user.id
        else:
            update = query_or_update
            user_id = update.effective_user.id
        
        state = self.get_user_state(user_id)
        
        db = SessionLocal()
        try:
            channels = db.query(Channel).all()
            
            if not channels:
                text = "❌ لا توجد قنوات مضافة. أضف قنوات أولاً من قائمة إدارة القنوات."
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if hasattr(query_or_update, 'edit_message_text'):
                    await query.edit_message_text(text, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(text, reply_markup=reply_markup)
                return
            
            selected_channels = state['post_data'].get('selected_channels', [])
            keyboard = []
            
            for channel in channels:
                status = "✅" if channel.channel_id in selected_channels else "⬜"
                button_text = f"{status} {channel.channel_name}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"toggle_channel_{channel.channel_id}")])
            
            keyboard.append([InlineKeyboardButton("✅ تأكيد الاختيار", callback_data="confirm_channels")])
            keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "📋 اختر القنوات للنشر فيها:\n\n✅ = محدد\n⬜ = غير محدد"
            
            if hasattr(query_or_update, 'edit_message_text'):
                await query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)
                
        finally:
            db.close()

    async def toggle_channel_selection(self, query, channel_id: str):
        """Toggle channel selection"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        selected_channels = state['post_data'].get('selected_channels', [])
        
        if channel_id in selected_channels:
            selected_channels.remove(channel_id)
        else:
            selected_channels.append(channel_id)
        
        state['post_data']['selected_channels'] = selected_channels
        await self.show_channel_selection(query)

    async def show_scheduling_options(self, query):
        """Show scheduling options"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        
        if not state['post_data'].get('selected_channels'):
            await query.answer("❌ يجب اختيار قناة واحدة على الأقل", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("🚀 النشر الآن", callback_data="post_now")],
            [InlineKeyboardButton("⏰ جدولة المنشور", callback_data="schedule_post")],
            [InlineKeyboardButton("🔙 العودة", callback_data="select_channels")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "⏰ متى تريد نشر المنشور؟"
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def set_post_now(self, query):
        """Set post to be published now"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['post_data']['scheduled_time'] = None
        
        await self.show_auto_delete_options(query)

    async def request_schedule_time(self, query):
        """Request schedule time from user"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['waiting_for'] = 'schedule_time'
        
        text = """
⏰ أدخل وقت الجدولة

التنسيق المطلوب:
YYYY-MM-DD HH:MM

مثال:
2024-12-25 15:30

أو يمكنك كتابة:
- "غداً 15:30"
- "بعد ساعة"
- "بعد 30 دقيقة"
        """
        
        await query.edit_message_text(text)

    async def handle_schedule_time(self, update: Update):
        """Handle schedule time input"""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        
        time_text = update.message.text.strip()
        scheduled_time = self.parse_datetime(time_text)
        
        if not scheduled_time:
            await update.message.reply_text("❌ تنسيق الوقت غير صحيح. حاول مرة أخرى.")
            return
        
        if scheduled_time <= datetime.now():
            await update.message.reply_text("❌ لا يمكن جدولة منشور في الماضي. حاول مرة أخرى.")
            return
        
        state['post_data']['scheduled_time'] = scheduled_time
        state['waiting_for'] = None
        
        await self.show_auto_delete_options(update)

    def parse_datetime(self, text: str) -> Optional[datetime]:
        """Parse datetime from text"""
        try:
            # Try standard format first
            if len(text.split()) == 2:
                return datetime.strptime(text, "%Y-%m-%d %H:%M")
            
            # Handle relative times
            now = datetime.now()
            text_lower = text.lower()
            
            if "غداً" in text_lower or "غدا" in text_lower:
                time_part = text_lower.split()[-1]
                hour, minute = map(int, time_part.split(':'))
                return now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)
            
            if "بعد ساعة" in text_lower:
                return now + timedelta(hours=1)
            
            if "بعد" in text_lower and "دقيقة" in text_lower:
                minutes = int(''.join(filter(str.isdigit, text)))
                return now + timedelta(minutes=minutes)
            
            return None
        except:
            return None

    async def show_auto_delete_options(self, query_or_update):
        """Show auto delete options"""
        keyboard = [
            [InlineKeyboardButton("🚫 بدون حذف تلقائي", callback_data="no_auto_delete")],
            [InlineKeyboardButton("⏰ تحديد وقت الحذف", callback_data="set_auto_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🗑️ هل تريد حذف المنشور تلقائياً بعد فترة معينة؟"
        
        if hasattr(query_or_update, 'edit_message_text'):
            await query_or_update.edit_message_text(text, reply_markup=reply_markup)
        else:
            await query_or_update.message.reply_text(text, reply_markup=reply_markup)

    async def set_no_auto_delete(self, query):
        """Set no auto delete"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['post_data']['auto_delete_time'] = None
        
        await self.show_post_settings(query)

    async def request_auto_delete_time(self, query):
        """Request auto delete time"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['waiting_for'] = 'auto_delete_time'
        
        text = """
⏰ متى تريد حذف المنشور تلقائياً؟

أمثلة:
- "بعد ساعة"
- "بعد 30 دقيقة"
- "بعد يوم"
- "2024-12-25 18:00"
        """
        
        await query.edit_message_text(text)

    async def handle_auto_delete_time(self, update: Update):
        """Handle auto delete time input"""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        
        time_text = update.message.text.strip()
        
        # Calculate delete time based on scheduled time or now
        base_time = state['post_data'].get('scheduled_time') or datetime.now()
        delete_time = self.parse_relative_time(time_text, base_time)
        
        if not delete_time:
            await update.message.reply_text("❌ تنسيق الوقت غير صحيح. حاول مرة أخرى.")
            return
        
        state['post_data']['auto_delete_time'] = delete_time
        state['waiting_for'] = None
        
        await self.show_post_settings(update)

    def parse_relative_time(self, text: str, base_time: datetime) -> Optional[datetime]:
        """Parse relative time from text"""
        try:
            text_lower = text.lower()
            
            if "بعد ساعة" in text_lower:
                return base_time + timedelta(hours=1)
            
            if "بعد" in text_lower and "دقيقة" in text_lower:
                minutes = int(''.join(filter(str.isdigit, text)))
                return base_time + timedelta(minutes=minutes)
            
            if "بعد يوم" in text_lower:
                return base_time + timedelta(days=1)
            
            # Try absolute datetime
            return self.parse_datetime(text)
        except:
            return None

    async def show_post_settings(self, query_or_update):
        """Show post settings"""
        if hasattr(query_or_update, 'from_user'):
            query = query_or_update
            user_id = query.from_user.id
        else:
            update = query_or_update
            user_id = update.effective_user.id
        
        state = self.get_user_state(user_id)
        post_data = state['post_data']
        
        silent_status = "🔕 صامت" if post_data.get('silent') else "🔔 مع إشعار"
        pin_status = "📌 مثبت" if post_data.get('pin_message') else "📋 عادي"
        
        keyboard = [
            [InlineKeyboardButton(f"الإشعارات: {silent_status}", callback_data="toggle_silent")],
            [InlineKeyboardButton(f"التثبيت: {pin_status}", callback_data="toggle_pin")],
            [InlineKeyboardButton("✅ إنهاء وإرسال", callback_data="finalize_post")],
            [InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "⚙️ إعدادات المنشور:\n\n"
        text += f"📝 المحتوى: {post_data['content'][:50]}...\n"
        text += f"📋 القنوات: {len(post_data['selected_channels'])} قناة\n"
        
        if post_data.get('scheduled_time'):
            text += f"⏰ الجدولة: {post_data['scheduled_time'].strftime('%Y-%m-%d %H:%M')}\n"
        else:
            text += "🚀 النشر: فوري\n"
        
        if post_data.get('auto_delete_time'):
            text += f"🗑️ الحذف: {post_data['auto_delete_time'].strftime('%Y-%m-%d %H:%M')}\n"
        else:
            text += "🗑️ الحذف: بدون حذف\n"
        
        text += f"\n{silent_status}\n{pin_status}"
        
        if hasattr(query_or_update, 'edit_message_text'):
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

    async def toggle_post_setting(self, query, setting: str):
        """Toggle post settings"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        
        if setting == "silent":
            state['post_data']['silent'] = not state['post_data'].get('silent', False)
        elif setting == "pin":
            state['post_data']['pin_message'] = not state['post_data'].get('pin_message', False)
        
        await self.show_post_settings(query)

    async def finalize_post(self, query):
        """Finalize and send/schedule the post"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        post_data = state['post_data']
        
        db = SessionLocal()
        try:
            # Get selected channels
            channels = db.query(Channel).filter(Channel.channel_id.in_(post_data['selected_channels'])).all()
            
            if post_data.get('scheduled_time'):
                # Schedule the post
                for channel in channels:
                    scheduled_post = ScheduledPost(
                        channel_id=channel.channel_id,
                        content=post_data['content'],
                        buttons=json.dumps(post_data.get('buttons', [])),
                        scheduled_time=post_data['scheduled_time'],
                        auto_delete_time=post_data.get('auto_delete_time'),
                        silent=post_data.get('silent', False),
                        pin_message=post_data.get('pin_message', False)
                    )
                    db.add(scheduled_post)
                
                db.commit()
                
                # Schedule with APScheduler
                scheduler.add_job(
                    self.send_scheduled_posts,
                    trigger=DateTrigger(run_date=post_data['scheduled_time']),
                    id=f"post_{datetime.now().timestamp()}"
                )
                
                await query.edit_message_text(
                    f"✅ تم جدولة المنشور بنجاح!\n"
                    f"⏰ سيتم النشر في: {post_data['scheduled_time'].strftime('%Y-%m-%d %H:%M')}\n"
                    f"📋 عدد القنوات: {len(channels)}"
                )
            else:
                # Send immediately
                success_count = 0
                for channel in channels:
                    try:
                        await self.send_post_to_channel(channel, post_data)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send to channel {channel.channel_id}: {e}")
                
                await query.edit_message_text(
                    f"✅ تم إرسال المنشور!\n"
                    f"📤 نجح: {success_count}/{len(channels)} قناة"
                )
        
        finally:
            db.close()
            self.clear_user_state(user_id)

    async def send_post_to_channel(self, channel: Channel, post_data: dict):
        """Send post to a specific channel"""
        content = post_data['content']
        
        # Add header if enabled
        if channel.header_enabled and channel.header_text:
            content = f"{channel.header_text}\n\n{content}"
        
        # Add footer if enabled
        if channel.footer_enabled and channel.footer_text:
            content = f"{content}\n\n{channel.footer_text}"
        
        # Prepare buttons
        reply_markup = None
        if post_data.get('buttons'):
            keyboard = []
            for row in post_data['buttons']:
                button_row = []
                for button in row:
                    button_row.append(InlineKeyboardButton(button['text'], url=button['url']))
                keyboard.append(button_row)
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message
        message = await self.application.bot.send_message(
            chat_id=channel.channel_id,
            text=content,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
            disable_notification=post_data.get('silent', False)
        )
        
        # Pin if requested
        if post_data.get('pin_message'):
            await self.application.bot.pin_chat_message(
                chat_id=channel.channel_id,
                message_id=message.message_id,
                disable_notification=post_data.get('silent', False)
            )
        
        # Schedule auto delete if requested
        if post_data.get('auto_delete_time'):
            scheduler.add_job(
                self.delete_message,
                trigger=DateTrigger(run_date=post_data['auto_delete_time']),
                args=[channel.channel_id, message.message_id],
                id=f"delete_{channel.channel_id}_{message.message_id}"
            )
        
        return message

    async def send_scheduled_posts(self):
        """Send scheduled posts"""
        db = SessionLocal()
        try:
            now = datetime.now()
            posts = db.query(ScheduledPost).filter(
                ScheduledPost.scheduled_time <= now,
                ScheduledPost.sent == False
            ).all()
            
            for post in posts:
                try:
                    channel = db.query(Channel).filter(Channel.channel_id == post.channel_id).first()
                    if channel:
                        post_data = {
                            'content': post.content,
                            'buttons': json.loads(post.buttons) if post.buttons else [],
                            'silent': post.silent,
                            'pin_message': post.pin_message,
                            'auto_delete_time': post.auto_delete_time
                        }
                        
                        message = await self.send_post_to_channel(channel, post_data)
                        post.sent = True
                        post.message_id = message.message_id
                        
                except Exception as e:
                    logger.error(f"Failed to send scheduled post {post.id}: {e}")
            
            db.commit()
        finally:
            db.close()

    async def delete_message(self, chat_id: str, message_id: int):
        """Delete a message"""
        try:
            await self.application.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.error(f"Failed to delete message {message_id} in {chat_id}: {e}")

    async def show_channels_menu(self, query):
        """Show channels management menu"""
        db = SessionLocal()
        try:
            channels = db.query(Channel).all()
            
            keyboard = [
                [InlineKeyboardButton("➕ إضافة قناة", callback_data="add_channel")]
            ]
            
            for channel in channels:
                keyboard.append([
                    InlineKeyboardButton(f"⚙️ {channel.channel_name}", callback_data=f"channel_settings_{channel.channel_id}"),
                    InlineKeyboardButton("🗑️", callback_data=f"remove_channel_{channel.channel_id}")
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = f"📋 إدارة القنوات ({len(channels)} قناة)\n\nاختر إجراء:"
            
            await query.edit_message_text(text, reply_markup=reply_markup)
        finally:
            db.close()

    async def add_channel_prompt(self, query):
        """Prompt user to add channel"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['waiting_for'] = 'channel_forward'
        
        text = """
➕ إضافة قناة جديدة

لإضافة قناة:
1. أضف البوت كمشرف في القناة
2. أرسل أي رسالة من القناة إلى هذا البوت (Forward)
3. سيتم إضافة القناة تلقائياً

أرسل رسالة محولة من القناة الآن:
        """
        
        await query.edit_message_text(text)

    async def handle_channel_forward(self, update: Update):
        """Handle forwarded message from channel"""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        
        if not update.message.forward_from_chat:
            await update.message.reply_text("❌ يجب إرسال رسالة محولة من القناة")
            return
        
        chat = update.message.forward_from_chat
        if chat.type != 'channel':
            await update.message.reply_text("❌ يجب أن تكون رسالة من قناة وليس مجموعة")
            return
        
        db = SessionLocal()
        try:
            # Check if channel already exists
            existing = db.query(Channel).filter(Channel.channel_id == str(chat.id)).first()
            if existing:
                await update.message.reply_text(f"⚠️ القناة {chat.title} مضافة مسبقاً")
                return
            
            # Add new channel
            channel = Channel(
                channel_id=str(chat.id),
                channel_name=chat.title,
                added_by=str(user_id)
            )
            db.add(channel)
            db.commit()
            
            state['waiting_for'] = None
            
            await update.message.reply_text(f"✅ تم إضافة القناة: {chat.title}")
            
        finally:
            db.close()

    async def show_channel_settings(self, query, channel_id: str):
        """Show settings for a specific channel"""
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await query.answer("❌ القناة غير موجودة", show_alert=True)
                return
            
            header_status = "✅ مفعل" if channel.header_enabled else "❌ معطل"
            footer_status = "✅ مفعل" if channel.footer_enabled else "❌ معطل"
            
            keyboard = [
                [InlineKeyboardButton(f"Header: {header_status}", callback_data=f"toggle_header_{channel_id}")],
                [InlineKeyboardButton(f"Footer: {footer_status}", callback_data=f"toggle_footer_{channel_id}")],
                [InlineKeyboardButton("📝 تعديل Header", callback_data=f"edit_header_{channel_id}")],
                [InlineKeyboardButton("📝 تعديل Footer", callback_data=f"edit_footer_{channel_id}")],
                [InlineKeyboardButton("🔙 العودة", callback_data="manage_channels")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"⚙️ إعدادات القناة: {channel.channel_name}\n\n"
            text += f"📋 Header: {header_status}\n"
            if channel.header_text:
                text += f"النص: {channel.header_text[:50]}...\n"
            text += f"\n📋 Footer: {footer_status}\n"
            if channel.footer_text:
                text += f"النص: {channel.footer_text[:50]}...\n"
            
            await query.edit_message_text(text, reply_markup=reply_markup)
        finally:
            db.close()

    async def show_scheduled_posts(self, query):
        """Show scheduled posts"""
        db = SessionLocal()
        try:
            posts = db.query(ScheduledPost).filter(ScheduledPost.sent == False).all()
            
            if not posts:
                text = "📅 لا توجد منشورات مجدولة"
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]]
            else:
                text = f"📅 المنشورات المجدولة ({len(posts)}):\n\n"
                keyboard = []
                
                for post in posts:
                    channel = db.query(Channel).filter(Channel.channel_id == post.channel_id).first()
                    channel_name = channel.channel_name if channel else "قناة محذوفة"
                    
                    text += f"📝 {post.content[:30]}...\n"
                    text += f"📋 {channel_name}\n"
                    text += f"⏰ {post.scheduled_time.strftime('%Y-%m-%d %H:%M')}\n\n"
                
                keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
        finally:
            db.close()

    async def show_settings_menu(self, query):
        """Show bot settings menu"""
        keyboard = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="show_stats")],
            [InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "⚙️ إعدادات البوت"
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def confirm_remove_channel(self, query, channel_id: str):
        """Confirm channel removal"""
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await query.answer("❌ القناة غير موجودة", show_alert=True)
                return
            
            keyboard = [
                [InlineKeyboardButton("✅ نعم، احذف القناة", callback_data=f"confirm_remove_{channel_id}")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="manage_channels")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"⚠️ هل أنت متأكد من حذف القناة؟\n\n📋 {channel.channel_name}\n\n⚠️ سيتم حذف جميع المنشورات المجدولة لهذه القناة"
            await query.edit_message_text(text, reply_markup=reply_markup)
        finally:
            db.close()

    async def remove_channel(self, query, channel_id: str):
        """Remove a channel"""
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await query.answer("❌ القناة غير موجودة", show_alert=True)
                return
            
            channel_name = channel.channel_name
            
            # Remove scheduled posts for this channel
            db.query(ScheduledPost).filter(ScheduledPost.channel_id == channel_id).delete()
            
            # Remove the channel
            db.delete(channel)
            db.commit()
            
            await query.edit_message_text(f"✅ تم حذف القناة: {channel_name}")
            
            # Show channels menu after 2 seconds
            import asyncio
            await asyncio.sleep(2)
            await self.show_channels_menu(query)
            
        finally:
            db.close()

    async def toggle_channel_header(self, query, channel_id: str):
        """Toggle channel header"""
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await query.answer("❌ القناة غير موجودة", show_alert=True)
                return
            
            channel.header_enabled = not channel.header_enabled
            db.commit()
            
            await self.show_channel_settings(query, channel_id)
        finally:
            db.close()

    async def toggle_channel_footer(self, query, channel_id: str):
        """Toggle channel footer"""
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await query.answer("❌ القناة غير موجودة", show_alert=True)
                return
            
            channel.footer_enabled = not channel.footer_enabled
            db.commit()
            
            await self.show_channel_settings(query, channel_id)
        finally:
            db.close()

    async def edit_channel_header(self, query, channel_id: str):
        """Edit channel header"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['waiting_for'] = 'header_text'
        state['editing_channel'] = channel_id
        
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await query.answer("❌ القناة غير موجودة", show_alert=True)
                return
            
            current_text = channel.header_text or "لا يوجد نص حالياً"
            text = f"📝 تعديل Header للقناة: {channel.channel_name}\n\n"
            text += f"النص الحالي:\n{current_text}\n\n"
            text += "أرسل النص الجديد للـ Header:"
            
            await query.edit_message_text(text)
        finally:
            db.close()

    async def edit_channel_footer(self, query, channel_id: str):
        """Edit channel footer"""
        user_id = query.from_user.id
        state = self.get_user_state(user_id)
        state['waiting_for'] = 'footer_text'
        state['editing_channel'] = channel_id
        
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await query.answer("❌ القناة غير موجودة", show_alert=True)
                return
            
            current_text = channel.footer_text or "لا يوجد نص حالياً"
            text = f"📝 تعديل Footer للقناة: {channel.channel_name}\n\n"
            text += f"النص الحالي:\n{current_text}\n\n"
            text += "أرسل النص الجديد للـ Footer:"
            
            await query.edit_message_text(text)
        finally:
            db.close()

    async def handle_header_text(self, update: Update):
        """Handle header text input"""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        channel_id = state.get('editing_channel')
        
        if not channel_id:
            await update.message.reply_text("❌ خطأ في النظام")
            return
        
        new_text = update.message.text
        
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await update.message.reply_text("❌ القناة غير موجودة")
                return
            
            channel.header_text = new_text
            channel.header_enabled = True
            db.commit()
            
            state['waiting_for'] = None
            state['editing_channel'] = None
            
            await update.message.reply_text(f"✅ تم تحديث Header للقناة: {channel.channel_name}")
            
        finally:
            db.close()

    async def handle_footer_text(self, update: Update):
        """Handle footer text input"""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        channel_id = state.get('editing_channel')
        
        if not channel_id:
            await update.message.reply_text("❌ خطأ في النظام")
            return
        
        new_text = update.message.text
        
        db = SessionLocal()
        try:
            channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
            if not channel:
                await update.message.reply_text("❌ القناة غير موجودة")
                return
            
            channel.footer_text = new_text
            channel.footer_enabled = True
            db.commit()
            
            state['waiting_for'] = None
            state['editing_channel'] = None
            
            await update.message.reply_text(f"✅ تم تحديث Footer للقناة: {channel.channel_name}")
            
        finally:
            db.close()

    def run(self):
        """Run the bot"""
        # Create database tables
        create_tables()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start scheduler
        scheduler.start()
        
        # Run the bot
        logger.info("Bot starting...")
        self.application.run_polling()

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found in environment variables")
        exit(1)
    
    if not ADMIN_USER_ID:
        print("❌ ADMIN_USER_ID not found in environment variables")
        exit(1)
    
    bot = TelegramChannelBot()
    bot.run()