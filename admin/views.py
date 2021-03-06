import time, os, bleach
from random import randint
from flask import render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_user, logout_user, login_required
from markdown import markdown
from sqlalchemy import or_, and_
from werkzeug.utils import secure_filename
from admin.models import Post, Tag, PostTag, User
from admin.main import app, db
from gl import archive_page_limit


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.values.get('username')
        password = request.values.get('password')
        user = User.query.filter(and_(User.name == username, User.password == password)).first()
        if user is not None:
            login_user(user)
            return jsonify(redirect_url=url_for('admin_index'), results='success')
        else:
            return jsonify(results='fail')
    else:
        return render_template('/login.html')


@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    flash('你已经退出登录了')
    return redirect(url_for('login'))


@app.route('/')
@app.route('/admin/')
@app.route('/admin/index')
@login_required
def admin_index():
    return render_template('index.html')


@app.route('/admin/article/index')
@login_required
def article_list():
    page_num = request.args.get('page_num')
    if not page_num:
        page_num = 1
    paginate = Post.query.filter_by(stype=1).order_by(Post.id.desc()).paginate(int(page_num), archive_page_limit, True)
    posts = paginate.items
    for p in posts:
        p.post_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p.post_time))
    return render_template('/article/index.html', pagination=paginate, posts=posts)


@app.route('/admin/article/draft')
@login_required
def draft_list():
    page_num = request.args.get('page_num')
    if not page_num:
        page_num = 1
    paginate = Post.query.filter_by(stype=2).order_by(Post.id.desc()).paginate(int(page_num), archive_page_limit, True)
    posts = paginate.items
    for p in posts:
        p.post_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p.post_time))
    return render_template('/article/draft.html', pagination=paginate, posts=posts)


@app.route('/admin/article/add', methods=['GET', 'POST'])
@login_required
def article_add():
    if request.method == 'POST':
        title = request.values.get('title')
        tags_str = request.values.get('tags')
        category = int(request.values.get('category'))
        store_type = int(request.values.get('store'))
        cont = request.values.get('cont')
        cont_html = markdown(cont)
        # post.content = markdown(post.markdown_source)
        post_time = int(time.time())
        post = Post(title=title, cont=cont_html, marksource=cont, post_time=post_time, category=category,
                    tags_str=tags_str, stype=store_type)
        db.session.add(post)
        # 下面这行代码用于获取自增长的主键
        db.session.flush()
        if tags_str != '':
            tags = tags_str.split(',')
            for tag in tags:
                t = Tag.query.filter_by(name=tag).first()
                if not t and tag.strip() != '':
                    size = randint(12, 20)
                    rgb = 'rgb({R},{G},{B})'.format(R=randint(0, 254), G=randint(0, 254), B=randint(0, 254))
                    t = Tag(name=tag, size=size, RGB=rgb)
                    db.session.add(t)
                    db.session.flush()
                db.session.add(PostTag(post.id, t.id))
        db.session.commit()
    return render_template('/article/add.html', post=None)


@app.route('/admin/article/edit/<string:pid>', methods=['GET', 'POST'])
@login_required
def article_edit(pid):
    post = db.session.query(Post).filter_by(id=int(pid)).first()
    if request.method == 'POST':
        post.stype = 1
        post.title = request.values.get('title')
        post.tags = request.values.get('tags')
        post.cacategory_id = int(request.values.get('category'))
        post.markdown_source = request.values.get('cont')
        post.content = bleach.clean(
            markdown(post.markdown_source)
        )

        if post.tags != '':
            tag_list = post.tags.split(',')
            for tag in tag_list:
                t = Tag.query.filter_by(name=tag).first()
                if not t and tag.strip() != '':
                    size = randint(12, 20)
                    rgb = 'rgb({R},{G},{B})'.format(R=randint(0, 254), G=randint(0, 254), B=randint(0, 254))
                    t2 = Tag(tag, size, rgb)
                    db.session.add(t2)
                    db.session.flush()
                    db.session.add(PostTag(post.id, t2.id))
                elif t:
                    r = PostTag.query.filter_by(post_id=post.id).filter_by(tag_id=t.id).first()
                    if not r:
                        db.session.add(PostTag(post.id, t.id))
        db.session.commit()
    return render_template('/article/add.html', post=post)


@app.route('/admin/article/delete/<string:pid>')
@login_required
def article_delete(pid):
    post = db.session.query(Post).filter_by(id=int(pid)).first()
    p_type = post.stype
    db.session.delete(post)
    db.session.commit()
    if p_type == 1:
        return redirect(url_for('article_list'))
    else:
        return redirect(url_for('draft_list'))


@app.route('/admin/article/show/<string:pid>')
@login_required
def article_showorhide(pid):
    post = db.session.query(Post).filter_by(id=int(pid)).first()
    post.status = 0 if post.status == 1 else 1
    db.session.commit()
    return redirect(url_for('article_list'))


@app.route('/admin/article/search', methods=['GET', 'POST'])
@login_required
def article_search():
    keyword = ''
    page_num = 1
    if request.method == 'POST':
        keyword = request.form.get('keyword')

    if request.method == 'GET':
        keyword = request.args.get('keyword')
        page_num = int(request.args.get('page_num'))

    paginate = Post.query.filter(or_(Post.title.like('%' + keyword + '%'), Post.content.like('%' + keyword + '%'))) \
        .paginate(page_num, archive_page_limit, True)
    posts = paginate.items
    for p in posts:
        p.post_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p.post_time))
    return render_template('/article/search.html', pagination=paginate, posts=posts, keyword=keyword)


@app.route('/admin/article/pic_upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'GET':
        return render_template('/article/pic_upload.html')
    else:
        file = request.files.get('fileList')
        if file and _allowed_file(file.filename):
            filename = (secure_filename(file.filename)).lower()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return jsonify(rea="<h1>{url}</h1>".format(url=os.path.join(app.config['UPLOAD_FOLDER'], filename)), res='suc')
        else:
            return jsonify(rea='文件类型有错', res='error')


def _allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


@app.errorhandler(404)
def page_not_fount(e):
    return render_template('404.html')


@app.errorhandler(500)
def page_not_fount(e):
    return render_template('500.html')