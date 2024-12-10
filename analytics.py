import os
from datetime import datetime, timedelta
import json
from openai import OpenAI
import google.generativeai as genai
from collections import defaultdict

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

class CompetitorAnalyzer:
    def __init__(self):
        self.cache_file = 'competitor_analysis.json'
        self.load_cache()

    def load_cache(self):
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
        except:
            self.cache = {}

    def save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=4)

    def analyze_competitor(self, username):
        """تحليل منافس محدد"""
        try:
            # تحليل آخر 10 منشورات
            analysis_prompt = f"""
            قم بتحليل الحساب: {username}
            
            قدم تحليلاً للعناصر التالية:
            1. نوع المحتوى الأكثر تفاعلاً
            2. أفضل أوقات النشر
            3. الهاشتاغات المستخدمة
            4. أسلوب التواصل مع المتابعين
            5. نقاط القوة والضعف
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "أنت محلل محتوى سوشيال ميديا محترف"},
                    {"role": "user", "content": analysis_prompt}
                ]
            )
            
            analysis = response.choices[0].message.content
            self.cache[username] = {
                'last_analysis': datetime.now().isoformat(),
                'analysis': analysis
            }
            self.save_cache()
            return analysis
        except Exception as e:
            print(f"خطأ في تحليل المنافس: {e}")
            return None

class ContentPlanner:
    def __init__(self):
        self.cache_file = 'content_plan.json'
        self.load_cache()

    def load_cache(self):
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
        except:
            self.cache = {}

    def save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=4)

    def generate_monthly_plan(self, month, year, business_type):
        """إنشاء خطة محتوى شهرية"""
        try:
            plan_prompt = f"""
            قم بإنشاء خطة محتوى لشهر {month}/{year}
            نوع النشاط: {business_type}
            
            قم بتوزيع المحتوى على:
            1. منشورات عادية
            2. قصص
            3. ريلز
            4. محتوى تفاعلي
            5. محتوى موسمي/مناسبات
            
            مع مراعاة:
            - التنوع في المحتوى
            - المناسبات خلال الشهر
            - أوقات النشر المثالية
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "أنت مخطط محتوى سوشيال ميديا محترف"},
                    {"role": "user", "content": plan_prompt}
                ]
            )
            
            plan = response.choices[0].message.content
            self.cache[f"{month}-{year}"] = {
                'business_type': business_type,
                'plan': plan,
                'created_at': datetime.now().isoformat()
            }
            self.save_cache()
            return plan
        except Exception as e:
            print(f"خطأ في إنشاء الخطة: {e}")
            return None

class ImageAnalyzer:
    def analyze_image(self, image_url):
        """تحليل الصورة وتقديم توصيات للتحسين"""
        try:
            analysis_prompt = f"""
            قم بتحليل هذه الصورة: {image_url}
            
            قدم تحليلاً للعناصر التالية:
            1. جودة الصورة
            2. التكوين والألوان
            3. مدى ملاءمتها للمنصة
            4. اقتراحات للتحسين
            """
            
            model = genai.GenerativeModel('gemini-pro-vision')
            response = model.generate_content(analysis_prompt)
            return response.text
        except Exception as e:
            print(f"خطأ في تحليل الصورة: {e}")
            return None

class AudienceAnalyzer:
    def __init__(self):
        self.cache_file = 'audience_insights.json'
        self.load_cache()

    def load_cache(self):
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
        except:
            self.cache = defaultdict(dict)

    def save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=4)

    def analyze_engagement(self, post_data):
        """تحليل تفاعل الجمهور مع المنشور"""
        try:
            engagement_prompt = f"""
            قم بتحليل تفاعل الجمهور مع هذا المنشور:
            
            المحتوى: {post_data['content']}
            التعليقات: {post_data['comments']}
            الإعجابات: {post_data['likes']}
            المشاركات: {post_data['shares']}
            
            قدم تحليلاً للعناصر التالية:
            1. نوع التفاعل الأكثر شيوعاً
            2. المشاعر السائدة في التعليقات
            3. أسباب نجاح/فشل المنشور
            4. توصيات للمحتوى المستقبلي
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "أنت محلل تفاعل جمهور محترف"},
                    {"role": "user", "content": engagement_prompt}
                ]
            )
            
            analysis = response.choices[0].message.content
            
            # حفظ التحليل في الذاكرة المؤقتة
            post_id = post_data.get('id', str(datetime.now().timestamp()))
            self.cache[post_id] = {
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            }
            self.save_cache()
            
            return analysis
        except Exception as e:
            print(f"خطأ في تحليل التفاعل: {e}")
            return None

# تصدير الكلاسات للاستخدام في app.py
__all__ = ['CompetitorAnalyzer', 'ContentPlanner', 'ImageAnalyzer', 'AudienceAnalyzer']
