from flask import Blueprint, render_template
from flask_login import current_user
from applications.common.utils.rights import authorize
from werkzeug.utils import secure_filename
from flask import request, jsonify, send_from_directory, render_template
from applications.extensions import db
from applications.models import Category, Tag, Ebook
import os

bp = Blueprint('ebooks', __name__, url_prefix='/ebooks')

def get_upload_folder():
    """
    获取上传文件夹的路径。

    Args:
        无

    Returns:
        str: 上传文件夹的绝对路径。

    """
    # 获取当前文件的绝对路径
    basedir = os.path.abspath(os.path.dirname(__file__))
    # 拼接上传文件夹的路径
    path = os.path.join(basedir, 'uploads')
    # 创建上传文件夹，如果文件夹已存在则不报错
    os.makedirs(path, exist_ok=True)
    # 返回上传文件夹的路径
    return path

# 主页
#@authorize("ebook:main") # 对应“标识”
@bp.get('/')
def ebooks():
    return render_template('readonly.html')

@bp.get('/editor')
@authorize("ebook:editor") # 对应“标识”
def ebookseditor():
    return render_template('editor.html')


# 上传电子书
@bp.route('/upload', methods=['POST'])
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
        while os.path.exists(os.path.join(get_upload_folder(), filename)):
            filename = f"{base}_{i}{ext}"
            i += 1

        # 保存文件
        file.save(os.path.join(get_upload_folder(), filename))

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

        new_ebook = Ebook(title=title, author=author, file_path=filename, tags=tags, upload_user_id=current_user.id)
        db.session.add(new_ebook)
        db.session.commit()
        return jsonify({"message": "Ebook uploaded successfully", "filename": filename}), 201
# 获取指定标签下的所有电子书
@bp.route('/books/tags/<string:tag_name>', methods=['GET'])
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
            'tags': [{'id': tag.id, 'name': tag.name} for tag in ebook.tags]
        }
        for ebook in ebooks
    ]
    
    return jsonify(ebooks_data), 200

# 删除标签
@bp.route('/tags/<int:tag_id>', methods=['DELETE'])
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
    
# 移动标签
@bp.route('/tags/move/<int:tag_id>/<int:parent_id>', methods=['POST'])
def move_tag(tag_id,parent_id):
    tag = Tag.query.get(tag_id)
    if tag:
        tag.category_id = parent_id
        # 删除标签本身
        db.session.commit()
        return jsonify({"message": "Tag 移动成功"}), 200
    else:
        return jsonify({"error": "Tag not found"}), 404
@bp.route('/categories/move/<int:category_id>/<int:parent_id>', methods=['POST'])
def move_category(category_id,parent_id):
    cat = Category.query.get(category_id)
    if cat:
        cat.parent_id = parent_id
        # 删除标签本身
        db.session.commit()
        return jsonify({"message": "类别移动成功"}), 200
    else:
        return jsonify({"error": "Tag not found"}), 404


@bp.route('/categories/<int:parent_id>/keywords', methods=['POST'])
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


@bp.route('/categories', methods=['POST'])
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

@bp.route('/categories/<int:category_id>', methods=['GET'])
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

@bp.route('/categories', methods=['GET'])
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
@bp.route('/categories/<int:parent_id>/children', methods=['POST'])
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


@bp.route('/categories/<int:category_id>', methods=['PUT'])
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
@bp.route('/categories/<int:category_id>', methods=['DELETE'])
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


# 给电子书添加标签
@bp.route('/tags/<int:ebook_id>', methods=['POST'])
def add_ebook_tag(ebook_id):
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
@bp.route('/books/<int:ebook_id>/tags/<int:tag_id>', methods=['DELETE'])
def delete_ebook_tag(ebook_id, tag_id):
    ebook = Ebook.query.get(ebook_id)
    if ebook:
        tag = Tag.query.filter_by(id=tag_id).first()
        if tag and tag in ebook.tags:
            ebook.tags.remove(tag)
            db.session.commit()
            return jsonify({"message": "Tag deleted successfully"}), 200
        else:
            return jsonify({"error": "Tag not found"}), 404
    else:
        return jsonify({"error": "Ebook not found"}), 404

@bp.route('/tags/<int:keyword_id>', methods=['PUT'])
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
@bp.route('/books', methods=['GET'])
def get_books():
    from sqlalchemy.orm import joinedload
    ebooks = Ebook.query.options(joinedload('tags')).all()
    books_data = []
    for ebook in ebooks:
        book_data = {
            'id': ebook.id,
            'title': ebook.title,
            'author': ebook.author,
            'tags': [{'id': tag.id, 'name': tag.name} for tag in ebook.tags]
        }
        books_data.append(book_data)
    return jsonify(books_data)

# 查找电子书
@bp.route('/books/search', methods=['GET'])
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
            'tags': [{'id': tag.id, 'name': tag.name} for tag in ebook.tags]
        }
        for ebook in ebooks
    ]

    return jsonify(books_data), 200

# 编辑电子书名称
@bp.route('/books/<int:ebook_id>/edit_title', methods=['PUT'])
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
@bp.route('/download/<int:ebook_id>')
def download_ebook(ebook_id):
    ebook = Ebook.query.get_or_404(ebook_id)
    return send_from_directory(directory=get_upload_folder(), path=ebook.file_path, as_attachment=True)

# 删除电子书
@bp.route('/books/<int:ebook_id>', methods=['DELETE'])
def delete_ebook(ebook_id):
    ebook = Ebook.query.get(ebook_id)
    if not ebook:
        return jsonify({"error": "Ebook not found"}), 404
    
    # 文件系统中删除电子书文件
    file_path = os.path.join(get_upload_folder(), ebook.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # 数据库中删除电子书记录
    db.session.delete(ebook)
    db.session.commit()
    
    return jsonify({"message": "Ebook deleted successfully"}), 200
