# 网址：https://github.com/epicblue/jl3web
# 作者：epicblue
# 日期：2024.9.10

from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
import logging
from flask_script import Manager

app = Flask(__name__)

# 配置数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ebooks.db')
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# 关联表
ebook_tag = db.Table(
    'ebook_tag',
    db.Column('ebook_id', db.Integer, db.ForeignKey('ebook.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# 电子书模型
class Ebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    tags = db.relationship("Tag", secondary=ebook_tag, back_populates="ebooks")

    def __repr__(self):
        return f'<Ebook {self.title}>'

# 标签模型
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship("Category", back_populates="tags")
    ebooks = db.relationship("Ebook", secondary=ebook_tag, back_populates="tags")

    def __repr__(self):
        return f'<Tag {self.name}>'

# 定义Category模型
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    subcategories = db.relationship("Category", back_populates="parent", remote_side=[id])
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    parent = db.relationship("Category", back_populates="subcategories")
    tags = db.relationship("Tag", back_populates="category")

    def __repr__(self):
        return f'<Category {self.name}>'
    
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
        original_filename = secure_filename(file.filename)
        base, ext = os.path.splitext(original_filename)
        
        # 构造初始文件名
        filename = original_filename

        # 检查是否有同名文件
        i = 1
        while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            filename = f"{base}_{i}{ext}"
            i += 1

        # 保存文件
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
                    # 获取根节点的 ID
                    root_category = Category.query.filter_by(name='root').first()
                    tag = Tag(name=tag_name, category_id=root_category.id)
                    db.session.add(tag)
                tags.append(tag)

        new_ebook = Ebook(title=title, author=author, file_path=filename, tags=tags)
        db.session.add(new_ebook)
        db.session.commit()
        return jsonify({"message": "Ebook uploaded successfully", "filename": filename}), 201
# 获取指定标签下的所有电子书
@app.route('/books/tags/<string:tag_name>', methods=['GET'])
def get_books_by_tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first()
    if not tag:
        return jsonify({'message': 'Tag not found'}), 404
    
    # 获取与该标签关联的所有电子书
    ebooks = tag.ebooks
    ebooks_data = [
        {
            'id': ebook.id,
            'title': ebook.title,
            'author': ebook.author,
            'tags': [tag.name for tag in ebook.tags]
        }
        for ebook in ebooks
    ]
    
    return jsonify(ebooks_data), 200

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

@app.route('/categories/<int:parent_id>/keywords', methods=['POST'])
def add_keyword(parent_id):
    data = request.get_json()
    keyword = data.get('keyword')

    if not keyword:
        return jsonify({"error": "Keyword is required"}), 400

    parent = Category.query.get(parent_id)
    if not parent:
        return jsonify({"error": "Parent category not found"}), 404

    keyword_tag = Tag(name=keyword,category_id=parent_id)
    parent.tags.append(keyword_tag)
    db.session.commit()

    return jsonify({"message": "Keyword added successfully"}), 200


@app.route('/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    name = data.get('name')
    parent_id = data.get('parent_id')

    if not name:
        return jsonify({"error": "Name is required"}), 400

    category = Category(name=name)
    if parent_id:
        parent = Category.query.get(parent_id)
        if not parent:
            return jsonify({"error": "Parent category not found"}), 404
        parent.subcategories.append(category)

    db.session.add(category)
    db.session.commit()
    return jsonify({"message": "Category created successfully", "id": category.id}), 201

@app.route('/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    category = Category.query.get(category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    category_data = {
        'id': category.id,
        'name': category.name,
        'subcategories': [
            {'id': sub.id, 'name': sub.name}
            for sub in category.subcategories
        ],
        'tags': [
            {'id': tag.id, 'name': tag.name}
            for tag in category.tags
        ]
    }

    return jsonify(category_data), 200

@app.route('/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    
    # 将 Category 对象转换成字典形式
    categories_data = []
    for category in categories:
        subcategories = category.subcategories if category.subcategories is not None else []
        
        if isinstance(subcategories, Category):
            subcategories = Category.query.filter_by(parent_id=category.id).all()
        
        category_dict = {
            'id': category.id,
            'name': category.name,
            'parent':category.parent_id if category.parent_id is not None else '#',
            'subcategories': [
                {'id': sub.id, 'name': sub.name}
                for sub in subcategories
            ],
            'tags': [
                {'id': tag.id, 'name': tag.name}
                for tag in category.tags
            ]
        }
        categories_data.append(category_dict)

    return jsonify(categories_data)

# 创建子分类
@app.route('/categories/<int:parent_id>/children', methods=['POST'])
def create_subcategory(parent_id):
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({"error": "Name is required"}), 400

    parent = Category.query.get(parent_id)
    if not parent:
        return jsonify({"error": "Parent category not found"}), 404

    try:
        subcategory = Category(name=name, parent_id=parent_id)
        db.session.add(subcategory)
        db.session.commit()
    except:
        return jsonify({"error": "Failed to create subcategory"}), 500
    return jsonify({"message": "Subcategory created successfully", "id": subcategory.id}), 201


@app.route('/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    category = Category.query.get(category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    data = request.get_json()
    name = data.get('name')
    parent_id = data.get('parent_id')

    if name:
        category.name = name

    if parent_id:
        parent = Category.query.get(parent_id)
        if not parent:
            return jsonify({"error": "Parent category not found"}), 404
        if category.parent != parent:
            if category.parent:
                category.parent.subcategories.remove(category)
            parent.subcategories.append(category)

    db.session.commit()
    return jsonify({"message": "Category updated successfully"}), 200

# 删除子分类
@app.route('/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    category = Category.query.get(category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    # 删除所有子分类和标签
    #if category.subcategories is not None:
    #    return jsonify({"error": "Category not found"}), 404
    if len(category.tags)>0:
        return jsonify({"error": "Category not found"}), 404

    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Category deleted successfully"}), 200

def ensure_root_category_exists():
    root_category = Category.query.filter_by(name='root').first()
    if not root_category:
        root_category = Category(name='root')
        db.session.add(root_category)
        db.session.commit()

ensure_root_category_exists()

# 给电子书添加标签
@app.route('/tags/<int:ebook_id>', methods=['POST'])
def add_tag(ebook_id):
    data = request.get_json()
    tag_name = data.get('tag')

    ebook = Ebook.query.get(ebook_id)
    if not ebook:
        return jsonify({'message': 'Ebook not found'}), 404

    tag = Tag.query.filter_by(name=tag_name).first()
    if not tag:
        root_category = Category.query.filter_by(name='root').first()
        tag = Tag(name=tag_name, category_id=root_category.id)

        db.session.add(tag)

    if tag not in ebook.tags:
        ebook.tags.append(tag)
        db.session.commit()
        return jsonify({'message': 'Tag added successfully'}), 201
    else:
        return jsonify({'message': 'Tag already exists for this ebook'}), 400

# 删除电子书的标签
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

@app.route('/tags/<int:keyword_id>', methods=['PUT'])
def update_keyword_name(keyword_id):
    data = request.get_json()
    new_name = data.get('name')

    if not new_name:
        return jsonify({"error": "New name is required"}), 400

    keyword = Tag.query.get(keyword_id)
    if not keyword:
        return jsonify({"error": "Keyword not found"}), 404

    keyword.name = new_name
    db.session.commit()

    return jsonify({"message": "Keyword name updated successfully"}), 200
# 获取所有电子书列表
@app.route('/books', methods=['GET'])
def get_books():
    from sqlalchemy.orm import joinedload
    ebooks = Ebook.query.options(joinedload('tags')).all()
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

# 查找电子书
@app.route('/books/search', methods=['GET'])
def search_books():
    search_query = request.args.get('query', '').strip()
    if not search_query:
        return jsonify({"error": "Search query is required"}), 400

    # 根据标题和作者进行搜索
    ebooks = Ebook.query.filter(
        (Ebook.title.ilike(f'%{search_query}%')) |
        (Ebook.author.ilike(f'%{search_query}%'))
    ).all()

    # 将符合条件的电子书数据转化为字典格式
    books_data = [
        {
            'id': ebook.id,
            'title': ebook.title,
            'author': ebook.author,
            'tags': [tag.name for tag in ebook.tags]
        }
        for ebook in ebooks
    ]

    return jsonify(books_data), 200

# 编辑电子书名称
@app.route('/books/<int:ebook_id>/edit_title', methods=['PUT'])
def edit_ebook_title(ebook_id):
    ebook = Ebook.query.get(ebook_id)
    if not ebook:
        return jsonify({"error": "Ebook not found"}), 404
    
    new_title = request.form.get('title')
    if not new_title:
        return jsonify({"error": "New title is required"}), 400
    
    ebook.title = new_title
    db.session.commit()
    
    return jsonify({"message": "Title updated successfully"}), 200

# 下载电子书
@app.route('/download/<int:ebook_id>')
def download_ebook(ebook_id):
    ebook = Ebook.query.get_or_404(ebook_id)
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], path=ebook.file_path, as_attachment=True)

# 删除电子书
@app.route('/books/<int:ebook_id>', methods=['DELETE'])
def delete_ebook(ebook_id):
    ebook = Ebook.query.get(ebook_id)
    if not ebook:
        return jsonify({"error": "Ebook not found"}), 404
    
    # 文件系统中删除电子书文件
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], ebook.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # 数据库中删除电子书记录
    db.session.delete(ebook)
    db.session.commit()
    
    return jsonify({"message": "Ebook deleted successfully"}), 200

# 主页路由
@app.route('/manage')
def index():
    return render_template('index.html')

# 主页路由
@app.route('/')
def readonlyindex():
    return render_template('index2.html')


if __name__ == '__main__':
    print('app running')
    app.run(debug=True)