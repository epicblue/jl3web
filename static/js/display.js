function displaySearchResults(books) {
    const booksList = document.getElementById('books');
    booksList.innerHTML = ''; // 清空列表

    books.forEach(book => {
        const li = document.createElement('li');
        li.className = 'book-item';
        li.textContent = `${book.title} - ${book.author}`;

        // 添加标签列表
        const tagsContainer = document.createElement('span');
        tagsContainer.className = 'tags-container';

        book.tags.forEach(tag => {
            const tagItem = document.createElement('span');
            tagItem.className = 'tag-item';
            tagItem.textContent = tag + ' ';
            tagItem.addEventListener('click', function() {
                showBooksByTag(tag); // 调用显示对应电子书的函数
            });
            tagsContainer.appendChild(tagItem);
        });

        const addTagButton = document.createElement('button');
        addTagButton.className = 'add-tag-button';
        addTagButton.textContent = '添加标签';
        addTagButton.addEventListener('click', function() {
            showAddTagInput(book.id);
        });

        const downloadButton = document.createElement('button');
        downloadButton.textContent = '下载';
        downloadButton.onclick = () => {
            window.location.href = `/download/${book.id}`;
        };

        li.appendChild(tagsContainer);
        li.appendChild(document.createTextNode(' ')); // 添加空格
        li.appendChild(addTagButton);
        li.appendChild(document.createTextNode(' ')); // 添加空格
        li.appendChild(downloadButton);
        booksList.appendChild(li);
    });
}