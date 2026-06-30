from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-super-secret-key-change-this-in-production'

# ===== تنظیمات دیتابیس PostgreSQL =====
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://love_38zp_user:m9bFRSh2U0gQYFRayKt1MyIHmJRc1qm3@dpg-d91omgreo5us739f58u0-a.oregon-postgres.render.com/love_38zp')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===== مدل دیتابیس =====
class UserPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200))
    text = db.Column(db.Text)
    image_path = db.Column(db.String(500))
    is_public = db.Column(db.Boolean, default=True)
    password_hash = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            self.password_hash = None
    
    def check_password(self, password):
        if not self.password_hash:
            return True
        return check_password_hash(self.password_hash, password)

# ===== تنظیمات آپلود =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# ایجاد پوشه آپلود
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 پوشه آپلود: {UPLOAD_FOLDER}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ===== مسیرهای استاتیک =====
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/static/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/static/music/<path:filename>')
def serve_music(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static', 'music'), filename)

# ===== صفحه اصلی =====
@app.route('/')
def index():
    return render_template('index.html')

# ===== صفحه ساخت =====
@app.route('/create', methods=['GET', 'POST'])
def create_page():
    if request.method == 'POST':
        slug = request.form.get('slug', '').strip().lower()
        name = request.form.get('name', '').strip()
        text = request.form.get('text', '').strip()
        is_public = request.form.get('is_public') == 'on'
        password = request.form.get('password', '').strip()
        
        # دریافت عکس
        image = request.files.get('image')
        if not image or image.filename == '':
            image = request.files.get('image1')
        
        # اعتبارسنجی
        if not slug:
            return render_template('create.html', error='لطفاً یک آدرس یکتا انتخاب کنید')
        
        if not slug.replace('-', '').replace('_', '').isalnum():
            return render_template('create.html', error='آدرس فقط می‌تواند شامل حروف، اعداد، - و _ باشد')
        
        existing = UserPage.query.filter_by(slug=slug).first()
        if existing:
            return render_template('create.html', error='این آدرس قبلاً استفاده شده است')
        
        if not text:
            return render_template('create.html', error='لطفاً متن عاشقانه را بنویسید')
        
        if not is_public and not password:
            return render_template('create.html', error='در حالت خصوصی، باید رمز عبور تعیین کنید')
        
        # ===== ذخیره عکس =====
        image_path = None
        if image and image.filename and image.filename != '':
            if allowed_file(image.filename):
                try:
                    original_filename = secure_filename(image.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    image.save(filepath)
                    image_path = f'uploads/{unique_filename}'
                    print(f"✅ عکس ذخیره شد: {filepath}")
                except Exception as e:
                    print(f"❌ خطا در ذخیره عکس: {e}")
            else:
                print(f"⚠️ فرمت فایل مجاز نیست: {image.filename}")
        else:
            print(f"⚠️ هیچ عکسی آپلود نشده")
        
        # ===== ایجاد صفحه =====
        new_page = UserPage(
            slug=slug,
            name=name or slug,
            text=text,
            image_path=image_path,
            is_public=is_public
        )
        new_page.set_password(password if not is_public else None)
        
        try:
            db.session.add(new_page)
            db.session.commit()
            print(f"✅ صفحه ساخته شد: /page/{slug}")
            print(f"🖼️ مسیر عکس: {image_path}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطا: {e}")
            return render_template('create.html', error='خطا در ذخیره اطلاعات')
        
        return redirect(url_for('view_page', slug=slug))
    
    return render_template('create.html')

# ===== صفحه نمایش =====
@app.route('/page/<slug>', methods=['GET', 'POST'])
def view_page(slug):
    page = UserPage.query.filter_by(slug=slug).first_or_404()
    
    print(f"🔍 صفحه: {slug}")
    print(f"🖼️ مسیر عکس در دیتابیس: {page.image_path}")
    
    if page.is_public:
        return render_template('view_page.html', page=page)
    
    if session.get(f'page_{slug}'):
        return render_template('view_page.html', page=page, unlocked=True)
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        if page.check_password(password):
            session[f'page_{slug}'] = True
            return render_template('view_page.html', page=page, unlocked=True)
        else:
            return render_template('view_page.html', page=page, need_password=True, error='❌ رمز عبور اشتباه است')
    
    return render_template('view_page.html', page=page, need_password=True)

# ===== خروج =====
@app.route('/page/<slug>/logout')
def logout_page(slug):
    session.pop(f'page_{slug}', None)
    return redirect(url_for('view_page', slug=slug))

# ===== لیست صفحات =====
@app.route('/pages')
def list_pages():
    pages = UserPage.query.filter_by(is_public=True).order_by(UserPage.created_at.desc()).all()
    return render_template('pages_list.html', pages=pages)

# ===== ساخت دیتابیس =====
with app.app_context():
    db.create_all()
    print("✅ دیتابیس PostgreSQL ساخته شد!")

# ===== اجرا =====
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)