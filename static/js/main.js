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
    // Legacy author functionality - keep for backward compatibility
    const addAuthorButton = document.getElementById('add-author');
    if (addAuthorButton) {
        console.warn('Using legacy author functionality. Consider upgrading to new co-author system.');
        addAuthorButton.addEventListener('click', function() {
            const authorInputs = document.querySelector('.author-inputs');
            if (!authorInputs) return;
            
            const newAuthorRow = document.createElement('div');
            newAuthorRow.className = 'author-row';
            newAuthorRow.style.opacity = '0';
            newAuthorRow.innerHTML = `
                <input type="text" name="author_names[]" placeholder="Author Name" required>
                <input type="email" name="author_emails[]" placeholder="Author Email" required>
                <input type="text" name="author_affiliations[]" placeholder="Affiliation" required>
                <button type="button" class="btn-secondary remove-author" onclick="removeAuthorRow(this)" title="Remove author">Remove</button>
            `;
            authorInputs.appendChild(newAuthorRow);
            
            // Smooth animation
            setTimeout(() => {
                newAuthorRow.style.transition = 'opacity 0.3s ease';
                newAuthorRow.style.opacity = '1';
            }, 10);
        });
    }
});

// Legacy function for removing author rows
function removeAuthorRow(button) {
    const authorRow = button.parentElement;
    authorRow.style.transition = 'opacity 0.3s ease';
    authorRow.style.opacity = '0';
    setTimeout(() => {
        authorRow.remove();
    }, 300);
} 