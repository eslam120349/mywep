from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, flash, send_file, session, abort,Response
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from app import app, db
from models import User,Message,Project,ProjectImage
from forms import LoginForm, RegistrationForm,MessageForm
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
import os
import uuid
import random
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('home'))

@app.route('/project/<int:project_id>')
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)


@app.route('/home')
def home():
    projects = Project.query.order_by(Project.created_at.desc()).limit(3).all()
    all_images = ProjectImage.query.all()
    random_images = random.sample(all_images, min(6, len(all_images)))  # اختار 6 صور عشوائيًا
    has_unreplied = Message.query.filter_by(is_repl=False).first() is not None
        
    # Get the language from session, default to English
    language = session.get('language', 'en')
    return render_template('home.html',projects=projects , images=random_images , has_unreplied=has_unreplied ,language=language)

@app.route('/projects')
def projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    has_unreplied = Message.query.filter_by(is_repl=False).first() is not None
        
    # Get the language from session, default to English
    language = session.get('language', 'en')
    return render_template('projects.html',projects=projects, has_unreplied=has_unreplied , language=language)

@app.route('/services')
def services():
    has_unreplied = Message.query.filter_by(is_repl=False).first() is not None

    # Get the language from session, default to English
    language = session.get('language', 'en')
    return render_template('services.html', has_unreplied=has_unreplied ,language=language)

@app.route('/contact')
def contact():
    form=MessageForm()
    has_unreplied = Message.query.filter_by(is_repl=False).first() is not None
    
    # Get the language from session, default to English
    language = session.get('language', 'en')

    return render_template('contact.html',form=form, has_unreplied=has_unreplied ,language=language)

@app.route('/send_massege', methods=['GET', 'POST'])
@login_required
def send_massege():
    form = MessageForm()
    has_unreplied = Message.query.filter_by(is_repl=False).first() is not None

    # Get the language from session, default to English
    language = session.get('language', 'en')
    if form.validate_on_submit():
        print("Form is valid ✅")
        print("Message content:", form.message.data)

        new_message = Message(
        user_id=current_user.id,
        message=form.message.data
        )

        db.session.add(new_message)
        db.session.commit()
        print("Message saved ✅")

        flash('Message sent successfully!')
        return redirect(url_for('home'))

    else:
        print("Form errors:", form.errors)
    
    return render_template('contact.html', form=form, has_unreplied=has_unreplied ,language=language)

@app.route('/reply/<int:msg_id>', methods=['POST'])
def mark_as_replied(msg_id):
    msg = Message.query.get_or_404(msg_id)
    msg.is_repl = True
    db.session.commit()
    return '', 204  # بنرجع رد فارغ يعني OK بدون محتوى


@app.route('/api/register', methods=['POST'])
def register_api():
    data = request.get_json()

    # Check if user already exists
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400

    # Create new user
    user = User(
        name=data.get('name'),
        email=data.get('email')
    )
    user.set_password(data.get('password'))

    # Save user to database
    db.session.add(user)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Registration successful'})

@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()

    if user and user.check_password(data.get('password')):
        login_user(user)
        return jsonify({'success': True, 'user': {'id': user.id, 'name': user.name, 'email': user.email}})

    return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout_api():
    logout_user()
    return jsonify({'success': True})

@app.route('/api/user')
@login_required
def get_user():
    return jsonify({
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email
    })

# Regular form-based routes (optional, for initial render)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    # Get the language from session, default to English
    language = session.get('language', 'en')

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('home')
            return redirect(next_page)
        flash('Invalid email or password')

    return render_template('login.html', form=form, language=language)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Get the language from session, default to English
    language = session.get('language', 'en')
    
    if current_user.is_authenticated:
        return redirect(url_for('home'))


    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        user.key=form.password.data
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))

    return render_template('register.html', form=form ,language=language)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/set-language/<language>')
def set_language(language):
    # Store the selected language in session
    session['language'] = language
    # Redirect back to the previous page
    return redirect(request.referrer or url_for('index'))

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(404)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function


@app.route("/admin/add_project", methods=["GET", "POST"])
@login_required
@admin_required
def add_project():
    if not current_user.is_admin:
        flash("غير مصرح لك بالدخول", "danger")
        return redirect(url_for("projects"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        images = request.files.getlist("images")

        project = Project(title=title, description=description)
        db.session.add(project)
        db.session.flush()

        for image in images:
            if image and allowed_file(image.filename):
                try:
                    # رفع الصورة لـ Cloudinary
                    upload_result = cloudinary.uploader.upload(image)
                    image_url = upload_result["secure_url"]

                    # حفظ رابط الصورة في قاعدة البيانات
                    project_image = ProjectImage(image_url=image_url, project_id=project.id)
                    db.session.add(project_image)

                except Exception as e:
                    flash("حدث خطأ أثناء رفع الصور: " + str(e), "danger")
                    return render_template("admin/add_project.html")
            else:
                flash("صيغة واحدة أو أكثر من الصور غير مدعومة!", "danger")
                return render_template("admin/add_project.html")

        db.session.commit()
        flash("تمت إضافة المشروع مع الصور!", "success")
        return redirect(url_for("projects"))
    
    # Get the language from session, default to English
    language = session.get('language', 'en')

    return render_template("admin/add_project.html" , language=language)


@app.route("/admin/delete_project/<int:project_id>", methods=["POST"])
@login_required
@admin_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)

    # حذف كل صور المشروع من الملفات
    for img in project.images:
        filename = img.image_url.split('/')[-1]
        filepath = os.path.join(app.root_path, 'static', 'uploads', filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(img)  # حذف صورة من قاعدة البيانات

    # حذف المشروع نفسه
    db.session.delete(project)
    db.session.commit()
    flash("تم حذف المشروع بنجاح", "success")
    return redirect(url_for("projects"))


@app.route('/admin/messages')
@login_required
@admin_required
def admin_messages():
    messages = Message.query.order_by(Message.id.desc()).all()
    # Get the language from session, default to English
    language = session.get('language', 'en')
    return render_template('admin/messages.html', messages=messages,language=language)

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# Error handlers
@app.errorhandler(403)
def forbidden(error):
    language = session.get('language', 'en')
    return render_template('errors/403.html', language=language), 403

@app.errorhandler(404)
def page_not_found(error):
    language = session.get('language', 'en')
    return render_template('errors/404.html', language=language), 404


    # Get the language from session, default to English
    language = session.get('language', 'en')

    form = LessonForm()
    if form.validate_on_submit():
        # Create new lesson directly
        lesson = Lesson(
            user_id=current_user.id,
            grade_level=form.grade_level.data,
            topic=form.topic.data,
            teaching_strategy=form.teaching_strategy.data,
            language=form.language.data
        )
        # Generate lesson plan content
        try:
            lesson_plan = generate_lesson_plan(
                form.grade_level.data,
                form.topic.data,
                form.teaching_strategy.data
                ,form.language.data
                ,form.AI.data
                
            )
            lesson.generated_plan = lesson_plan
            lesson.gpt_plan=gpt_plans(form.grade_level.data,form.topic.data,form.teaching_strategy.data,form.language.data )

        except Exception as e:
            flash(f'Error generating lesson plan: {str(e)}')
            return render_template('create_lesson.html', form=form, language=language)

        # Save to database
        db.session.add(lesson)
        db.session.commit()

        flash('Lesson plan created successfully!')
        return redirect(url_for('edit_lesson_form', lesson_id=lesson.id))

    return render_template('create_lesson.html', form=form, language=language)

@app.route('/sitemap.xml')
def sitemap():
    base_url = request.url_root.strip('/')
    pages = [
        {'url': base_url + url_for('index'), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'url': base_url + url_for('home'), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'url': base_url + url_for('projects'), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'url': base_url + url_for('services'), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'url': base_url + url_for('contact'), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
    ]

    for project in Project.query.all():
        project_url = base_url + url_for('view_project', project_id=project.id)
        pages.append({
            'url': project_url,
            'lastmod': project.created_at.strftime('%Y-%m-%d')
        })

    sitemap_xml = render_template('sitemap.xml', pages=pages)
    return Response(sitemap_xml, mimetype='application/xml')
