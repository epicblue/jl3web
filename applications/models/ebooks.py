from applications.extensions import db

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
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 添加上传用户属性

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
   