// Add smooth scrolling to all links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Add mobile menu toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const navbar = document.querySelector('.navbar');
    const navLinks = document.querySelector('.nav-links');
    
    if (window.innerWidth <= 768) {
        const menuButton = document.createElement('button');
        menuButton.classList.add('menu-toggle');
        menuButton.innerHTML = '☰';
        navbar.insertBefore(menuButton, navLinks);
        
        menuButton.addEventListener('click', () => {
            navLinks.classList.toggle('show');
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const addAuthorButton = document.getElementById('add-author');
    if (addAuthorButton) {
        addAuthorButton.addEventListener('click', function() {
            const authorInputs = document.querySelector('.author-inputs');
            const newAuthorRow = document.createElement('div');
            newAuthorRow.className = 'author-row';
            newAuthorRow.innerHTML = `
                <input type="text" name="author_names[]" placeholder="Author Name" required>
                <input type="email" name="author_emails[]" placeholder="Author Email" required>
                <input type="text" name="author_affiliations[]" placeholder="Affiliation" required>
                <button type="button" class="btn-secondary remove-author" onclick="this.parentElement.remove()">Remove</button>
            `;
            authorInputs.appendChild(newAuthorRow);
        });
    }
}); 