# ============= المكتبات المطلوبة =============
from flask import Flask, render_template, request, jsonify, send_file, session
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import random
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadPassword, ChallengeRequired, TwoFactorRequired
import base64
from PIL import Image
import io
import traceback
import sys
from openai import OpenAI
from huggingface_hub import InferenceClient
import calendar
import pytz
import re
from collections import defaultdict

# ============= تهيئة التطبيق =============
load_dotenv()
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.urandom(24)

# ============= تكوين API =============
# OpenAI
def init_api_keys():
    openai_key = os.getenv('OPENAI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    if not openai_key:
        print("Warning: OPENAI_API_KEY not found in environment variables")
    if not google_key:
        print("Warning: GOOGLE_API_KEY not found in environment variables")
        
    return openai_key, google_key

# تهيئة المفاتيح عند بدء التطبيق
openai_api_key, google_api_key = init_api_keys()

client = OpenAI(
    api_key=openai_api_key,
    base_url="https://api.openai.com/v1"
)

# Gemini
api_key = google_api_key
if not api_key:
    print("Warning: GOOGLE_API_KEY not found in environment variables")

try:
    genai.configure(api_key=api_key)
    text_model = genai.GenerativeModel('gemini-pro')
    vision_model = genai.GenerativeModel('gemini-pro-vision')
    print("تم تهيئة نماذج Gemini بنجاح", file=sys.stderr)
except Exception as e:
    print(f"خطأ في تهيئة نماذج Gemini: {str(e)}", file=sys.stderr)

# Instagram
instagram_client = None

# ============= الثوابت والإعدادات =============
# المواسم
SEASONS = {
    'winter': {'start': '21-12', 'end': '20-03', 'name': 'الشتاء'},
    'spring': {'start': '21-03', 'end': '20-06', 'name': 'الربيع'},
    'summer': {'start': '21-06', 'end': '20-09', 'name': 'الصيف'},
    'autumn': {'start': '21-09', 'end': '20-12', 'name': 'الخريف'}
}

# المناسبات
OCCASIONS = {
    'رمضان': {'type': 'hijri', 'month': 9},
    'عيد الفطر': {'type': 'hijri', 'month': 10, 'day': 1},
    'عيد الأضحى': {'type': 'hijri', 'month': 12, 'day': 10},
    'رأس السنة الميلادية': {'type': 'gregorian', 'month': 1, 'day': 1},
    'اليوم الوطني السعودي': {'type': 'gregorian', 'month': 9, 'day': 23}
}

# قوالب المحتوى
CONTENT_TEMPLATES = {
    'tips': """
    🌟 [عنوان جذاب]
    
    💡 نصائح مهمة:
    [النصائح]
    
    💪 [خاتمة تحفيزية]
    
    #[هاشتاغات_مناسبة]
    """,
    'story': """
    📖 [عنوان القصة]
    
    [محتوى القصة]
    
    ✨ [خاتمة مؤثرة]
    
    #[هاشتاغات_مناسبة]
    """,
    'tutorial': """
    📚 [عنوان الدرس]
    
    🔍 الخطوات:
    [خطوات الشرح]
    
    💡 نصيحة مهمة:
    [نصيحة]
    
    #[هاشتاغات_مناسبة]
    """,
    'contest': """
    🎉 [عنوان المسابقة]
    
    🎁 الجائزة:
    [تفاصيل الجائزة]
    
    📝 كيفية المشاركة:
    [خطوات المشاركة]
    
    ⏰ موعد الإعلان عن الفائز:
    [التاريخ والوقت]
    
    #[هاشتاغات_مناسبة]
    """,
    'promotion': """
    ⭐️ [عنوان العرض]
    
    💥 العرض:
    [تفاصيل العرض]
    
    ⏳ العرض متاح حتى:
    [تاريخ انتهاء العرض]
    
    📞 للتواصل:
    [معلومات التواصل]
    
    #[هاشتاغات_مناسبة]
    """,
    'live': """
    🔴 بث مباشر:
    [عنوان البث]
    
    📅 الموعد:
    [التاريخ والوقت]
    
    📋 جدول البث:
    [تفاصيل الجدول]
    
    #[هاشتاغات_مناسبة]
    """,
    'marketing': """
    🔥 [عنوان جذاب للمنتج/الخدمة]
    
    ✨ المميزات الرئيسية:
    ▫️ [ميزة 1]
    ▫️ [ميزة 2]
    ▫️ [ميزة 3]
    
    💰 العرض الخاص:
    [تفاصيل العرض والسعر]
    
    🎁 الهدية:
    [تفاصيل الهدية أو العرض الإضافي]
    
    ⏰ العرض متاح لفترة محدودة!
    
    📱 للطلب والاستفسار:
    [معلومات التواصل]
    
    #[هاشتاغات_تسويقية]
    """,
    'edu_marketing': """
    📚 [عنوان تعليمي جذاب]
    
    ❓ هل تعلم:
    [معلومة قيمة متعلقة بالمنتج/الخدمة]
    
    🎯 المشكلة:
    [وصف المشكلة التي يواجهها الجمهور]
    
    ✅ الحل:
    [كيف يحل منتجك/خدمتك هذه المشكلة]
    
    📊 النتائج:
    ▫️ [نتيجة 1]
    ▫️ [نتيجة 2]
    ▫️ [نتيجة 3]
    
    💡 نصيحة مجانية:
    [قدم نصيحة قيمة مجانية]
    
    🎁 عرض خاص للمتابعين:
    [تفاصيل العرض]
    
    📱 للاستفادة من العرض:
    [معلومات التواصل]
    
    #تعليم #تطوير #محتوى_تعليمي #[هاشتاغات_إضافية]
    """
}

# الرموز التعبيرية
EMOJI_MAP = {
    'مهم': '⚡️',
    'جديد': '🆕',
    'حصري': '🔥',
    'عرض': '🎯',
    'خصم': '💰',
    'نصيحة': '💡',
    'تذكير': '⏰',
    'انتبه': '⚠️'
}

# قاعدة بيانات بسيطة للنصائح والأفكار
CONTENT_TIPS = {
    'instagram_post': [
        'استخدم صور عالية الجودة',
        'اكتب كابشن يثير المشاعر',
        'استخدم 5-10 هاشتاغات',
        'اطرح سؤالاً في نهاية المنشور',
    ],
    'instagram_story': [
        'استخدم الملصقات التفاعلية',
        'أضف موسيقى مناسبة',
        'استخدم استطلاعات الرأي',
        'اربط القصة بمنشور في حسابك',
    ],
    'instagram_reel': [
        'استخدم موسيقى رائجة',
        'اجعل أول 3 ثواني مثيرة',
        'أضف نصوصاً على الفيديو',
        'استخدم الترندات الحالية',
    ],
    'tiktok': [
        'تابع التحديات الشائعة',
        'استخدم الفلاتر المميزة',
        'شارك في الترندات',
        'أضف موسيقى من قائمة الأكثر استخداماً',
    ]
}

BEST_POSTING_TIMES = {
    'instagram_post': ['9:00 صباحاً', '3:00 مساءً', '9:00 مساءً'],
    'instagram_story': ['8:00 صباحاً', '2:00 مساءً', '8:00 مساءً'],
    'instagram_reel': ['11:00 صباحاً', '5:00 مساءً', '10:00 مساءً'],
    'tiktok': ['10:00 صباحاً', '4:00 مساءً', '11:00 مساءً']
}

# بيانات الجمهور المستهدف
TARGET_AUDIENCE_DATA = {
    'عام': 'محتوى يناسب جميع الفئات العمرية والاهتمامات.',
    'شباب': 'محتوى حيوي يتماشى مع اهتمامات الشباب وأحدث الترندات.',
    'عائلات': 'محتوى يركز على القيم العائلية والأنشطة الجماعية.',
    'رجال أعمال': 'محتوى احترافي يركز على الابتكار والنمو المهني.',
    'طلاب': 'محتوى تعليمي وترفيهي يناسب الطلاب.'
}

# البيانات الافتراضية
DEFAULT_POSTING_TIMES = {
    'weekday': {
        'morning': '9:00 صباحاً',
        'afternoon': '3:00 مساءً',
        'evening': '8:00 مساءً'
    },
    'weekend': {
        'morning': '11:00 صباحاً',
        'afternoon': '4:00 مساءً',
        'evening': '9:00 مساءً'
    }
}

# الهاشتاغات الافتراضية
DEFAULT_HASHTAGS = {
    'عام': ['#محتوى', '#تسويق', '#سوشيال_ميديا', '#انستغرام', '#تطوير_الذات', '#نجاح', '#تحفيز', '#ريادة_أعمال'],
    'تعليم': ['#تعليم', '#مهارات', '#تطوير', '#معرفة', '#تعلم', '#دراسة', '#نصائح_تعليمية'],
    'أعمال': ['#ريادة_أعمال', '#نجاح', '#تسويق', '#استثمار', '#تجارة', '#اقتصاد', '#مشاريع'],
    'تقنية': ['#تقنية', '#تكنولوجيا', '#برمجة', '#ابتكار', '#تطوير', '#تطبيقات', '#ذكاء_اصطناعي'],
    'رياضة': ['#رياضة', '#صحة', '#لياقة', '#تمارين', '#تحدي', '#حياة_صحية', '#تحفيز'],
    'طعام': ['#طبخ', '#وصفات', '#طعام_صحي', '#مطبخ', '#طبخات', '#وصفات_سهلة', '#مطاعم'],
    'سفر': ['#سفر', '#سياحة', '#رحلات', '#سافر', '#مغامرات', '#سياحة_عربية', '#وجهات_سياحية'],
    'تسويق': [
        '#تسويق_الكتروني',
        '#تسويق_رقمي',
        '#اعلان',
        '#عروض_خاصة',
        '#تخفيضات',
        '#تسوق',
        '#اعلانات',
        '#تسويق_انستقرام',
        '#تجارة_الكترونية',
        '#متجر',
        '#عروض_حصرية',
        '#تسويق_المنتجات'
    ]
}

def init_instagram_client():
    try:
        client = Client()
        client.login(os.getenv('INSTAGRAM_USERNAME'), os.getenv('INSTAGRAM_PASSWORD'))
        return client
    except Exception as e:
        print(f"Error initializing Instagram client: {str(e)}", file=sys.stderr)
        return None

def generate_image_prompt(topic):
    prompt = f"""اقترح وصفاً لصورة تناسب منشور على Instagram:
    الموضوع: {topic}
    نوع النشاط: 
    
    اكتب الوصف باللغة العربية، وركز على العناصر البصرية والتكوين والألوان."""
    
    response = text_model.generate_content(prompt)
    return response.text

def format_content_for_instagram(content):
    # تنسيق المحتوى للنشر على انستغرام
    formatted_content = {
        'caption': '',
        'hashtags': []
    }
    
    try:
        # استخراج النص الرئيسي والهاشتاغات
        lines = content.split('\n')
        caption_lines = []
        hashtags = []
        
        for line in lines:
            if line.strip().startswith('#'):
                # جمع الهاشتاغات
                tags = line.strip().split()
                hashtags.extend(tags)
            else:
                # جمع النص
                if line.strip():
                    caption_lines.append(line.strip())
        
        # تنسيق النص النهائي
        formatted_content['caption'] = '\n\n'.join(caption_lines)
        if hashtags:
            formatted_content['caption'] += '\n\n' + ' '.join(hashtags)
        formatted_content['hashtags'] = hashtags
        
    except Exception as e:
        print(f"Error formatting content: {str(e)}", file=sys.stderr)
        print("Detailed error:")
        print(traceback.format_exc(), file=sys.stderr)
        formatted_content['caption'] = content
    
    return formatted_content

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_tips', methods=['POST'])
def get_tips():
    try:
        data = request.get_json()
        content_type = data.get('contentType', '')
        
        if content_type in CONTENT_TIPS:
            return jsonify({
                'success': True,
                'tips': random.sample(CONTENT_TIPS[content_type], 2),
                'best_times': random.sample(BEST_POSTING_TIMES[content_type], 2)
            })
        
        return jsonify({
            'success': False,
            'error': 'نوع المحتوى غير معروف'
        })
    
    except Exception as e:
        print(f"Error getting tips: {str(e)}", file=sys.stderr)
        print("Detailed error:")
        print(traceback.format_exc(), file=sys.stderr)
        return jsonify({
            'success': False,
            'error': 'حدث خطأ في جلب النصائح'
        })

@app.route('/generate_content', methods=['POST'])
def generate_content():
    try:
        print("=== بداية توليد المحتوى ===", file=sys.stderr)
        
        # التحقق من تهيئة النموذج
        if not api_key:
            raise Exception("لم يتم تكوين مفتاح Google API")
            
        data = request.get_json()
        print(f"البيانات المستلمة: {data}", file=sys.stderr)
        
        # التحقق من البيانات المطلوبة
        if not data:
            raise ValueError("لم يتم استلام أي بيانات")
            
        topic = data.get('topic', '')
        content_type = data.get('content_type', 'tips')
        tone = data.get('tone', 'professional')
        
        print(f"الموضوع: {topic}", file=sys.stderr)
        print(f"نوع المحتوى: {content_type}", file=sys.stderr)
        print(f"النبرة: {tone}", file=sys.stderr)
        
        if not topic:
            raise ValueError("الرجاء إدخال الموضوع")
            
        if content_type not in CONTENT_TEMPLATES:
            content_type = 'tips'  # استخدام النوع الافتراضي إذا كان النوع غير صالح
        
        # اختيار القالب المناسب
        template = CONTENT_TEMPLATES[content_type]
        
        # تحديد نمط المحتوى
        content_styles = {
            'tips': 'نصائح ومعلومات مفيدة',
            'story': 'قصة قصيرة جذابة',
            'tutorial': 'شرح تعليمي مبسط',
            'contest': 'مسابقة تفاعلية',
            'promotion': 'عرض ترويجي مميز',
            'live': 'تغطية مباشرة'
        }
        
        tone_styles = {
            'professional': 'مهني واحترافي',
            'casual': 'غير رسمي وبسيط',
            'friendly': 'ودي وقريب',
            'humorous': 'مرح وخفيف'
        }
        
        style = content_styles.get(content_type, 'نصائح ومعلومات مفيدة')
        selected_tone = tone_styles.get(tone, 'مهني واحترافي')
        
        # إنشاء النص المطلوب
        prompt = f"""أنت خبير في كتابة محتوى وسائل التواصل الاجتماعي باللغة العربية.
        المطلوب: إنشاء محتوى {style} حول "{topic}" بنبرة {selected_tone}.
        
        استخدم القالب التالي:
        {template}
        
        يجب أن يكون المحتوى:
        1. جذاباً وملفتاً للانتباه
        2. مناسباً لمنصة انستغرام
        3. يتضمن رموزاً تعبيرية مناسبة
        4. يحتوي على دعوة للتفاعل
        5. يتضمن 5-7 هاشتاغات مناسبة باللغة العربية
        
        ملاحظة: قم بملء القالب مباشرة دون تغيير هيكله.
        """
        
        print("=== النص المطلوب ===", file=sys.stderr)
        print(prompt, file=sys.stderr)
        
        try:
            print("جاري إرسال الطلب إلى نموذج Gemini...", file=sys.stderr)
            response = text_model.generate_content(prompt)
            print("تم استلام الرد من نموذج Gemini", file=sys.stderr)
            
            if not response or not hasattr(response, 'text'):
                raise Exception("لم يتم استلام رد صالح من النموذج")
                
            content = response.text.strip()
            if not content:
                raise Exception("الرد المستلم فارغ")
                
            print("=== المحتوى المولد ===", file=sys.stderr)
            print(content, file=sys.stderr)
            
            # توليد وصف الصورة
            try:
                print("جاري توليد وصف الصورة...", file=sys.stderr)
                image_prompt = f"""اقترح وصفاً مختصراً لصورة تناسب منشور على انستغرام حول: {topic}
                الوصف يجب أن يكون باللغة العربية ويركز على العناصر البصرية."""
                
                image_response = text_model.generate_content(image_prompt)
                image_description = image_response.text.strip() if image_response and hasattr(image_response, 'text') else ""
                print(f"وصف الصورة: {image_description}", file=sys.stderr)
                
            except Exception as image_error:
                print(f"خطأ في توليد وصف الصورة: {str(image_error)}", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                image_description = ""
            
            return jsonify({
                'status': 'success',
                'content': content,
                'image_prompt': image_description
            })
            
        except Exception as model_error:
            print(f"خطأ في نموذج Gemini: {str(model_error)}", file=sys.stderr)
            print(f"التفاصيل الكاملة للخطأ:", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            raise Exception(f"حدث خطأ أثناء توليد المحتوى: {str(model_error)}")
        
    except ValueError as ve:
        print(f"خطأ في التحقق من البيانات: {str(ve)}", file=sys.stderr)
        return jsonify({
            'status': 'error',
            'message': str(ve)
        }), 400
        
    except Exception as e:
        print(f"خطأ في توليد المحتوى: {str(e)}", file=sys.stderr)
        print("التفاصيل الكاملة للخطأ:", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return jsonify({
            'status': 'error',
            'message': str(e) or 'حدث خطأ في توليد المحتوى'
        }), 500

@app.route('/post_to_instagram', methods=['POST'])
def post_to_instagram():
    try:
        data = request.get_json()
        caption = data.get('caption', '')
        image_data = data.get('image', '')  # Base64 encoded image
        
        # تنظيف النص
        clean_caption = caption.replace('<div>', '').replace('</div>', '\n').replace('<br>', '\n')
        
        # حفظ الصورة مؤقتاً
        if image_data:
            try:
                # تحويل Base64 إلى صورة
                image_bytes = base64.b64decode(image_data.split(',')[1])
                image = Image.open(io.BytesIO(image_bytes))
                
                # حفظ الصورة مؤقتاً
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    image.save(temp_file.name, 'JPEG')
                    
                    # نشر الصورة على انستغرام
                    cl = Client()
                    cl.login(session['instagram_username'], session['instagram_password'])
                    media = cl.photo_upload(
                        temp_file.name,
                        caption=clean_caption
                    )
                
                # حذف الملف المؤقت
                os.unlink(temp_file.name)
                
                return jsonify({
                    'success': True,
                    'message': 'تم نشر المحتوى بنجاح'
                })
                
            except Exception as e:
                print(f"Error processing image: {str(e)}", file=sys.stderr)
                print("Detailed error:")
                print(traceback.format_exc(), file=sys.stderr)
                return jsonify({
                    'success': False,
                    'error': f'خطأ في معالجة الصورة: {str(e)}'
                })
        else:
            # إرسال رسالة مباشرة فقط
            cl = Client()
            cl.login(session['instagram_username'], session['instagram_password'])
            user_id = cl.user_id
            cl.direct_send(clean_caption, [user_id])
            
            return jsonify({
                'success': True,
                'message': 'تم إرسال النص بنجاح'
            })
            
    except Exception as e:
        print(f"Error posting to Instagram: {str(e)}", file=sys.stderr)
        print("Detailed error:")
        print(traceback.format_exc(), file=sys.stderr)
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/connect_instagram', methods=['POST'])
def connect_instagram():
    try:
        print("=== بداية الاتصال بالانستجرام ===", file=sys.stderr)
        username = os.getenv('INSTAGRAM_USERNAME')
        password = os.getenv('INSTAGRAM_PASSWORD')

        if not username or not password:
            print("خطأ: بيانات الاعتماد غير موجودة في ملف .env", file=sys.stderr)
            return jsonify({
                'success': False,
                'error': 'بيانات الاعتماد غير موجودة'
            }), 400

        try:
            # تهيئة كائن Instagram
            cl = Client()
            cl.delay_range = [1, 3]
            cl.request_timeout = 30
            
            try:
                # محاولة تسجيل الدخول
                print("محاولة تسجيل الدخول...", file=sys.stderr)
                login_result = cl.login(username, password)
                print(f"نتيجة تسجيل الدخول: {login_result}", file=sys.stderr)
                
                if login_result:
                    print("تم تسجيل الدخول بنجاح", file=sys.stderr)
                    session['instagram_username'] = username
                    session['instagram_connected'] = True
                    session['instagram_session'] = cl.get_settings()
                    return jsonify({'success': True})
                else:
                    print("فشل تسجيل الدخول: لم يتم إرجاع نتيجة صحيحة", file=sys.stderr)
                    return jsonify({
                        'success': False,
                        'error': 'فشل تسجيل الدخول'
                    }), 401
                    
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                print(f"خطأ في تسجيل الدخول: {error_type} - {error_message}", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                
                if isinstance(e, BadPassword):
                    return jsonify({
                        'success': False,
                        'error': 'كلمة المرور غير صحيحة'
                    }), 401
                elif isinstance(e, ChallengeRequired):
                    print("مطلوب رمز تحقق", file=sys.stderr)
                    return jsonify({
                        'success': False,
                        'error': 'challenge_required'
                    }), 403
                elif isinstance(e, TwoFactorRequired):
                    return jsonify({
                        'success': False,
                        'error': 'التحقق بخطوتين مفعل. يرجى تعطيله مؤقتاً'
                    }), 403
                else:
                    return jsonify({
                        'success': False,
                        'error': 'حدث خطأ في عملية تسجيل الدخول'
                    }), 500
                    
        except Exception as e:
            print(f"خطأ غير متوقع: {type(e).__name__} - {str(e)}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            return jsonify({
                'success': False,
                'error': 'حدث خطأ في الاتصال'
            }), 500
            
    except Exception as e:
        print(f"خطأ غير متوقع: {type(e).__name__} - {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return jsonify({
            'success': False,
            'error': 'حدث خطأ في الاتصال'
        }), 500

@app.route('/verify_instagram', methods=['POST'])
def verify_instagram():
    try:
        print("=== بداية التحقق من الرمز ===", file=sys.stderr)
        data = request.get_json()
        
        if not data:
            print("خطأ: لم يتم استلام بيانات JSON", file=sys.stderr)
            return jsonify({
                'success': False,
                'error': 'بيانات غير صالحة'
            }), 400

        verification_code = data.get('verification_code')
        username = os.getenv('INSTAGRAM_USERNAME')
        password = os.getenv('INSTAGRAM_PASSWORD')

        print(f"استخدام بيانات الاعتماد من ملف .env - username: {username}", file=sys.stderr)

        if not verification_code:
            print("خطأ: الرمز مفقود", file=sys.stderr)
            return jsonify({
                'success': False,
                'error': 'يرجى إدخال رمز التحقق'
            }), 400

        try:
            # تهيئة كائن Instagram
            cl = Client()
            cl.delay_range = [1, 3]
            cl.request_timeout = 30
            
            # تسجيل الدخول مع رمز التحقق
            print("محاولة تسجيل الدخول مع رمز التحقق...", file=sys.stderr)
            cl.login(username, password, verification_code=verification_code)
            print("تم تسجيل الدخول بنجاح!", file=sys.stderr)
            
            # حفظ معلومات الحساب في الجلسة
            session['instagram_username'] = username
            session['instagram_connected'] = True
            session['instagram_session'] = cl.get_settings()

            return jsonify({'success': True})
            
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            print(f"خطأ في التحقق: {error_type} - {error_message}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            
            if 'verification_code' in error_message.lower():
                return jsonify({
                    'success': False,
                    'error': 'رمز التحقق غير صحيح'
                }), 401
            else:
                return jsonify({
                    'success': False,
                    'error': 'حدث خطأ في عملية التحقق'
                }), 500
                
    except Exception as e:
        print(f"خطأ غير متوقع: {type(e).__name__} - {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return jsonify({
            'success': False,
            'error': 'حدث خطأ في عملية التحقق'
        }), 500

@app.route('/get_account_info')
def get_account_info():
    try:
        if session.get('instagram_connected'):
            return jsonify({
                'success': True,
                'username': session.get('instagram_username')
            })
        return jsonify({'success': False})
    except Exception as e:
        print(f"خطأ في جلب معلومات الحساب: {str(e)}", file=sys.stderr)
        return jsonify({
            'success': False,
            'error': 'حدث خطأ في جلب معلومات الحساب'
        })

def save_to_history(content_data):
    history_file = 'content_history.json'
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        history.insert(0, content_data)
        history = history[:50]  # نحتفظ بآخر 50 محتوى فقط
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving to history: {str(e)}", file=sys.stderr)
        print("Detailed error:")
        print(traceback.format_exc(), file=sys.stderr)

@app.route('/get_history', methods=['GET'])
def get_history():
    try:
        if os.path.exists('content_history.json'):
            with open('content_history.json', 'r', encoding='utf-8') as f:
                history = json.load(f)
            return jsonify({
                'success': True,
                'history': history[:10]  # نرجع آخر 10 محتويات فقط
            })
    except Exception as e:
        print(f"Error reading history: {str(e)}", file=sys.stderr)
        print("Detailed error:")
        print(traceback.format_exc(), file=sys.stderr)
    
    return jsonify({
        'success': False,
        'history': []
    })

@app.route('/generate_image', methods=['POST'])
def generate_image():
    try:
        print("=== بداية طلب توليد الصورة ===", file=sys.stderr)
        
        if not client:
            raise Exception("لم يتم تهيئة OpenAI بشكل صحيح. تحقق من مفتاح API")
            
        data = request.get_json()
        prompt = data.get('prompt', '')
        
        if not prompt:
            print("لم يتم توفير وصف للصورة", file=sys.stderr)
            return jsonify({
                'success': False,
                'error': 'لم يتم توفير وصف للصورة'
            })
        
        print(f"الوصف المستلم: {prompt}", file=sys.stderr)
        
        # تحويل الوصف إلى اللغة الإنجليزية للحصول على نتائج أفضل
        translation_prompt = f"""
        Translate the following image description to English, keeping the important details and making it more suitable for DALL-E image generation:
        {prompt}
        
        Translation:"""
        
        print("جاري ترجمة الوصف...", file=sys.stderr)
        translation_response = text_model.generate_content(translation_prompt)
        english_prompt = translation_response.text.strip()
        print(f"الوصف بالإنجليزية: {english_prompt}", file=sys.stderr)
        
        print("جاري إرسال الطلب إلى DALL-E...", file=sys.stderr)
        try:
            # توليد الصورة باستخدام DALL-E
            response = client.images.generate(
                model="dall-e-2",
                prompt=english_prompt,
                n=1,
                size="1024x1024"
            )
            
            image_url = response.data[0].url
            print(f"تم استلام رابط الصورة: {image_url}", file=sys.stderr)
            
            return jsonify({
                'success': True,
                'image_url': image_url
            })
        except Exception as img_error:
            print(f"خطأ في توليد الصورة من DALL-E: {str(img_error)}", file=sys.stderr)
            raise Exception(f"فشل في توليد الصورة: {str(img_error)}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"خطأ في توليد الصورة: {error_msg}", file=sys.stderr)
        print("تفاصيل الخطأ الكاملة:", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        
        if "API key" in error_msg.lower():
            error_msg = "خطأ في مفتاح API. الرجاء التحقق من صحة المفتاح"
        elif "billing" in error_msg.lower():
            error_msg = "خطأ في الفوترة. الرجاء التحقق من حالة حسابك"
        
        return jsonify({
            'success': False,
            'error': error_msg
        })

class ContentScheduler:
    def __init__(self):
        self.scheduled_content = defaultdict(list)
        self.load_schedule()
    
    def load_schedule(self):
        try:
            with open('content_schedule.json', 'r', encoding='utf-8') as f:
                self.scheduled_content = defaultdict(list, json.load(f))
        except FileNotFoundError:
            self.scheduled_content = defaultdict(list)
    
    def save_schedule(self):
        with open('content_schedule.json', 'w', encoding='utf-8') as f:
            json.dump(dict(self.scheduled_content), f, ensure_ascii=False, indent=4)
    
    def schedule_content(self, date_str, content_data):
        """جدولة محتوى جديد"""
        try:
            schedule_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            self.scheduled_content[schedule_date].append(content_data)
            self.save_schedule()
            return True, "تمت جدولة المحتوى بنجاح"
        except Exception as e:
            return False, f"خطأ في جدولة المحتوى: {str(e)}"
    
    def get_scheduled_content(self, date_str=None):
        """الحصول على المحتوى المجدول"""
        if date_str:
            return self.scheduled_content.get(date_str, [])
        return dict(self.scheduled_content)
    
    def get_upcoming_content(self, days=7):
        """الحصول على المحتوى القادم"""
        upcoming = {}
        current_date = datetime.now()
        for i in range(days):
            date = (current_date + timedelta(days=i)).strftime('%Y-%m-%d')
            if date in self.scheduled_content:
                upcoming[date] = self.scheduled_content[date]
        return upcoming
    
    def get_season_suggestions(self):
        """اقتراحات حسب الموسم الحالي"""
        current_date = datetime.now()
        current_month_day = current_date.strftime('%d-%m')
        
        current_season = None
        for season, dates in SEASONS.items():
            start = datetime.strptime(dates['start'], '%d-%m').replace(year=current_date.year)
            end = datetime.strptime(dates['end'], '%d-%m').replace(year=current_date.year)
            
            if start <= current_date <= end:
                current_season = season
                break
        
        season_suggestions = {
            'winter': ['نصائح للعناية بالبشرة في الشتاء', 'أفكار للأنشطة الشتوية', 'وصفات المشروبات الدافئة'],
            'spring': ['نصائح للعناية بالحديقة', 'أفكار للنزهات الربيعية', 'وصفات صحية للربيع'],
            'summer': ['نصائح للعناية بالبشرة في الصيف', 'أفكار للرحلات الصيفية', 'وصفات المشروبات المنعشة'],
            'autumn': ['نصائح للعناية بالصحة في الخريف', 'أفكار للأنشطة الخريفية', 'وصفات الخريف اللذيذة']
        }
        
        return season_suggestions.get(current_season, [])

# إنشاء مثيل من ContentScheduler
content_scheduler = ContentScheduler()

@app.route('/schedule_content', methods=['POST'])
def schedule_content_endpoint():
    """واجهة برمجية لجدولة المحتوى"""
    try:
        data = request.get_json()
        date_str = data.get('date')
        content_data = data.get('content')
        
        if not date_str or not content_data:
            return jsonify({'status': 'error', 'message': 'البيانات غير مكتملة'}), 400
        
        success, message = content_scheduler.schedule_content(date_str, content_data)
        
        if success:
            return jsonify({'status': 'success', 'message': message}), 200
        else:
            return jsonify({'status': 'error', 'message': message}), 400
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_schedule', methods=['GET'])
def get_schedule_endpoint():
    """الحصول على جدول المحتوى"""
    date = request.args.get('date')
    schedule = content_scheduler.get_scheduled_content(date)
    return jsonify({'status': 'success', 'schedule': schedule})

@app.route('/get_upcoming', methods=['GET'])
def get_upcoming_endpoint():
    """الحصول على المحتوى القادم"""
    days = int(request.args.get('days', 7))
    upcoming = content_scheduler.get_upcoming_content(days)
    return jsonify({'status': 'success', 'upcoming': upcoming})

@app.route('/get_suggestions', methods=['GET'])
def get_suggestions_endpoint():
    """الحصول على اقتراحات المحتوى"""
    suggestions = content_scheduler.get_season_suggestions()
    return jsonify({'status': 'success', 'suggestions': suggestions})

@app.route('/track_post', methods=['POST'])
def track_post_endpoint():
    """تتبع أداء المنشورات"""
    try:
        data = request.get_json()
        post_id = data.get('post_id')
        metrics = data.get('metrics')
        
        if not post_id or not metrics:
            return jsonify({'status': 'error', 'message': 'البيانات غير مكتملة'}), 400
        
        content_analytics.track_post(post_id, metrics)
        return jsonify({'status': 'success', 'message': 'تم تحديث التحليلات بنجاح'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_post_analytics/<post_id>', methods=['GET'])
def get_post_analytics_endpoint(post_id):
    """الحصول على تحليلات منشور معين"""
    analytics = content_analytics.get_post_analytics(post_id)
    return jsonify({'status': 'success', 'analytics': analytics})

@app.route('/get_best_posts', methods=['GET'])
def get_best_posts_endpoint():
    """الحصول على أفضل المنشورات"""
    try:
        # محاولة الحصول على البيانات من التحليلات
        analytics_data = content_analytics.get_best_performing_posts()
        
        if not analytics_data:
            # إذا لم تتوفر بيانات، قدم نصائح ومقترحات
            return jsonify({
                'status': 'success',
                'data': {
                    'recommendations': [
                        'استخدم صور عالية الجودة مع إضاءة جيدة',
                        'اكتب عناوين جذابة تثير اهتمام متابعيك',
                        'استخدم مزيجاً من الهاشتاغات الشائعة والمخصصة',
                        'انشر في أوقات نشاط متابعيك'
                    ],
                    'best_posts': [],
                    'note': 'لا توجد بيانات كافية بعد. هذه توصيات عامة للمساعدة.'
                }
            })
        
        return jsonify({
            'status': 'success',
            'data': analytics_data
        })
        
    except Exception as e:
        print(f"خطأ في الحصول على أفضل المنشورات: {str(e)}", file=sys.stderr)
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ في جلب البيانات'
        }), 500

@app.route('/get_best_times', methods=['GET'])
def get_best_times_endpoint():
    """الحصول على أفضل أوقات النشر"""
    try:
        # محاولة الحصول على البيانات من التحليلات
        analytics_data = content_analytics.get_best_posting_times()
        
        if not analytics_data:
            # إذا لم تتوفر بيانات، استخدم البيانات الافتراضية
            current_day = datetime.now().strftime('%A')
            is_weekend = current_day in ['Friday', 'Saturday']
            time_data = DEFAULT_POSTING_TIMES['weekend' if is_weekend else 'weekday']
            
            return jsonify({
                'status': 'success',
                'data': {
                    'morning': {
                        'time': time_data['morning'],
                        'description': 'أفضل وقت للنشر صباحاً عندما يكون المتابعون نشطين'
                    },
                    'afternoon': {
                        'time': time_data['afternoon'],
                        'description': 'فترة نشاط عالية بعد الظهر'
                    },
                    'evening': {
                        'time': time_data['evening'],
                        'description': 'وقت مثالي للتفاعل المسائي'
                    }
                },
                'message': 'توصيات مبنية على أفضل الممارسات العامة'
            })
    except Exception as e:
        print(f"خطأ في الحصول على أفضل أوقات النشر: {str(e)}", file=sys.stderr)
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ في جلب البيانات'
        }), 500

@app.route('/optimize_content', methods=['POST'])
def optimize_content_endpoint():
    """تحسين المحتوى"""
    try:
        data = request.get_json()
        caption = data.get('caption', '')
        target_length = data.get('target_length')
        
        optimized_caption = smart_optimizer.optimize_caption(caption, target_length)
        
        return jsonify({
            'status': 'success',
            'optimized_caption': optimized_caption
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_trending_hashtags', methods=['GET'])
def get_trending_hashtags_endpoint():
    """الحصول على الهاشتاغات الرائجة"""
    category = request.args.get('category')
    limit = int(request.args.get('limit', 10))
    
    trending = smart_optimizer.get_trending_hashtags(category, limit)
    return jsonify({'status': 'success', 'trending_hashtags': trending})

class ContentAnalytics:
    """تحليل أداء المحتوى"""
    def __init__(self):
        self.analytics_data = defaultdict(dict)
        self.load_analytics()
    
    def load_analytics(self):
        try:
            with open('content_analytics.json', 'r', encoding='utf-8') as f:
                self.analytics_data = defaultdict(dict, json.load(f))
        except FileNotFoundError:
            self.analytics_data = defaultdict(dict)
    
    def save_analytics(self):
        with open('content_analytics.json', 'w', encoding='utf-8') as f:
            json.dump(dict(self.analytics_data), f, ensure_ascii=False, indent=4)
    
    def track_post(self, post_id, metrics):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if post_id not in self.analytics_data:
            self.analytics_data[post_id] = {
                'created_at': current_time,
                'metrics_history': []
            }
        
        metrics['timestamp'] = current_time
        self.analytics_data[post_id]['metrics_history'].append(metrics)
        self.analytics_data[post_id]['last_updated'] = current_time
        self.save_analytics()
    
    def get_post_analytics(self, post_id):
        return self.analytics_data.get(post_id, {})
    
    def get_best_performing_posts(self, metric='likes', limit=5):
        posts_metrics = []
        for post_id, data in self.analytics_data.items():
            if data['metrics_history']:
                latest_metrics = data['metrics_history'][-1]
                posts_metrics.append({
                    'post_id': post_id,
                    'metric_value': latest_metrics.get(metric, 0),
                    'data': data
                })
        
        return sorted(posts_metrics, key=lambda x: x['metric_value'], reverse=True)[:limit]
    
    def get_best_posting_times(self):
        engagement_by_hour = defaultdict(list)
        
        for post_data in self.analytics_data.values():
            for metric in post_data['metrics_history']:
                if 'timestamp' in metric:
                    hour = datetime.strptime(metric['timestamp'], '%Y-%m-%d %H:%M:%S').hour
                    engagement = metric.get('likes', 0) + metric.get('comments', 0)
                    engagement_by_hour[hour].append(engagement)
        
        average_engagement = {
            hour: sum(engagements)/len(engagements)
            for hour, engagements in engagement_by_hour.items()
            if engagements
        }
        
        return dict(sorted(average_engagement.items(), key=lambda x: x[1], reverse=True))

class SmartOptimizer:
    """تحسين المحتوى ذكياً"""
    def __init__(self):
        self.hashtag_data = defaultdict(dict)
        self.load_hashtag_data()
    
    def load_hashtag_data(self):
        """تحميل بيانات الهاشتاغات"""
        # في حالة عدم وجود بيانات، استخدم الهاشتاغات الافتراضية
        self.hashtag_data = DEFAULT_HASHTAGS
    
    def get_trending_hashtags(self, category=None, limit=10):
        """الحصول على الهاشتاغات الرائجة"""
        try:
            if category and category in self.hashtag_data:
                hashtags = self.hashtag_data[category]
            else:
                # إذا لم يتم تحديد فئة أو كانت الفئة غير موجودة، اجمع كل الهاشتاغات
                hashtags = []
                for cat_hashtags in self.hashtag_data.values():
                    hashtags.extend(cat_hashtags)
                
                # إزالة التكرار
                hashtags = list(set(hashtags))
            
            # ترتيب عشوائي وتحديد العدد المطلوب
            random.shuffle(hashtags)
            return hashtags[:limit]
            
        except Exception as e:
            print(f"خطأ في جلب الهاشتاغات: {str(e)}", file=sys.stderr)
            # إرجاع قائمة افتراضية في حالة حدوث خطأ
            return DEFAULT_HASHTAGS['عام'][:limit]
    
    def update_hashtag_data(self, hashtag, engagement):
        if hashtag not in self.hashtag_data:
            self.hashtag_data[hashtag] = {
                'total_engagement': 0,
                'usage_count': 0,
                'last_used': None,
                'performance_history': []
            }
        
        self.hashtag_data[hashtag]['total_engagement'] += engagement
        self.hashtag_data[hashtag]['usage_count'] += 1
        self.hashtag_data[hashtag]['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.hashtag_data[hashtag]['performance_history'].append({
            'engagement': engagement,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        self.save_hashtag_data()
    
    def save_hashtag_data(self):
        with open('hashtag_data.json', 'w', encoding='utf-8') as f:
            json.dump(dict(self.hashtag_data), f, ensure_ascii=False, indent=4)
    
    def optimize_caption(self, caption, target_length=None):
        # تحسين النص
        caption = self.fix_punctuation(caption)
        
        if target_length:
            caption = self.adjust_length(caption, target_length)
        
        caption = self.add_emojis(caption)
        
        return caption
    
    def fix_punctuation(self, text):
        rules = [
            (r'،\s*،', '،'),
            (r'\s+،', '،'),
            (r'،(?![\\s])', '، '),
            (r'\s+\.', '.'),
            (r'!+', '!'),
            (r'\s+!', '!'),
            (r'؟+', '؟'),
            (r'\s+؟', '؟')
        ]
        
        for pattern, replacement in rules:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def adjust_length(self, text, target_length):
        current_length = len(text)
        
        if current_length <= target_length:
            return text
        
        sentences = text.split('.')
        while len('.'.join(sentences)) > target_length and len(sentences) > 1:
            sentences.pop()
        
        return '.'.join(sentences)
    
    def add_emojis(self, text):
        for word, emoji in EMOJI_MAP.items():
            if word in text and emoji not in text:
                text = text.replace(word, f'{emoji} {word}')
        
        return text

# ============= إنشاء المثيلات =============
content_scheduler = ContentScheduler()
content_analytics = ContentAnalytics()
smart_optimizer = SmartOptimizer()

@app.route('/health')
def health_check():
    """
    نقطة نهاية للتحقق من صحة التطبيق
    تستخدم للتأكد من أن التطبيق يعمل بشكل صحيح
    """
    status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_keys': {
            'openai': bool(openai_api_key),
            'google': bool(google_api_key)
        }
    }
    return jsonify(status)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
