from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 配置数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ebooks.db')
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# 关联表
ebook_tags = db.Table('ebook_tags',
    db.Column('ebook_id', db.Integer, db.ForeignKey('ebook.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# 电子书模型
class Ebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    author = db.Column(db.String(120))
    file_path = db.Column(db.String(200))
    tags = db.relationship('Tag', secondary=ebook_tags, backref=db.backref('ebooks', lazy='dynamic'))

    def __repr__(self):
        return f'<Ebook {self.title}>'

# 标签模型
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Tag {self.name}>'

# 初始化数据库
db.create_all()

# 上传电子书
@app.route('/upload', methods=['POST'])
def upload_ebook():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        title = request.form.get('title')
        author = request.form.get('author')
        tags_str = request.form.get('tags', '')  # 获取标签字符串
        
        # 解析标签字符串
        tags = []
        for tag_name in tags_str.split(','):
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag is None:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                tags.append(tag)

        new_ebook = Ebook(title=title, author=author, file_path=filename, tags=tags)
        db.session.add(new_ebook)
        db.session.commit()
        return jsonify({"message": "Ebook uploaded successfully"}), 201

# 删除标签
@app.route('/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    tag = Tag.query.get(tag_id)
    if tag:
        # 先解除标签与所有电子书的关联
        for ebook in tag.ebooks:
            ebook.tags.remove(tag)
        
        # 删除标签本身
        db.session.delete(tag)
        db.session.commit()
        return jsonify({"message": "Tag deleted successfully"}), 200
    else:
        return jsonify({"error": "Tag not found"}), 404
@app.route('/tags/<int:ebook_id>', methods=['POST'])
def add_tag(ebook_id):
    data = request.get_json()
    tag_name = data.get('tag')

    ebook = Ebook.query.get(ebook_id)
    if not ebook:
        return jsonify({'message': 'Ebook not found'}), 404

    tag = Tag.query.filter_by(name=tag_name).first()
    if not tag:
        tag = Tag(name=tag_name)
        db.session.add(tag)

    if tag not in ebook.tags:
        ebook.tags.append(tag)
        db.session.commit()
        return jsonify({'message': 'Tag added successfully'}), 201
    else:
        return jsonify({'message': 'Tag already exists for this ebook'}), 400


@app.route('/tags/<int:ebook_id>/<string:tag_name>', methods=['DELETE'])
def delete_ebook_tag(ebook_id, tag_name):
    ebook = Ebook.query.get(ebook_id)
    if ebook:
        tag = Tag.query.filter_by(name=tag_name).first()
        if tag and tag in ebook.tags:
            ebook.tags.remove(tag)
            db.session.commit()
            return jsonify({"message": "Tag deleted successfully"}), 200
        else:
            return jsonify({"error": "Tag not found"}), 404
    else:
        return jsonify({"error": "Ebook not found"}), 404


# 获取所有电子书列表
@app.route('/books', methods=['GET'])
def get_books():
    ebooks = Ebook.query.all()
    books_data = []
    for ebook in ebooks:
        book_data = {
            'id': ebook.id,
            'title': ebook.title,
            'author': ebook.author,
            'tags': [tag.name for tag in ebook.tags]
        }
        books_data.append(book_data)
    return jsonify(books_data)

# 下载电子书
@app.route('/download/<int:ebook_id>')
def download_ebook(ebook_id):
    ebook = Ebook.query.get_or_404(ebook_id)
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], path=ebook.file_path, as_attachment=True)

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)