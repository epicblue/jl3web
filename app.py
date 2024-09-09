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

# 电子书模型
class Ebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    author = db.Column(db.String(120))
    file_path = db.Column(db.String(200))

    def __repr__(self):
        return f'<Ebook {self.title}>'

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
        new_ebook = Ebook(title=request.form.get('title'), author=request.form.get('author'), file_path=filename)
        db.session.add(new_ebook)
        db.session.commit()
        return jsonify({"message": "Ebook uploaded successfully"}), 201

# 获取所有电子书列表
@app.route('/books', methods=['GET'])
def get_books():
    ebooks = Ebook.query.all()
    return jsonify([{'id': e.id, 'title': e.title, 'author': e.author} for e in ebooks])

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