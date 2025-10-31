// AJAX Follow/Unfollow functionality
class SocialInteractions {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupFollowButtons();
        this.setupLikeButtons();
    }
    
    setupFollowButtons() {
        document.querySelectorAll('.follow-btn, .unfollow-btn').forEach(button => {
            button.addEventListener('click', this.handleFollowClick.bind(this));
        });
    }
    
    setupLikeButtons() {
        document.querySelectorAll('.btn-like').forEach(button => {
            button.addEventListener('click', this.handleLikeClick.bind(this));
        });
    }
    
    handleFollowClick(e) {
        e.preventDefault();
        const button = e.currentTarget;
        const url = button.href;
        const isCurrentlyFollowing = button.classList.contains('unfollow-btn');
        
        this.updateButtonState(button, 'loading');
        
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                this.updateFollowUI(button, data.following);
                this.showNotification(data.following ? 'Followed successfully!' : 'Unfollowed successfully!', 'success');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showNotification('Something went wrong!', 'error');
            // Fallback to normal navigation
            window.location.href = url;
        })
        .finally(() => {
            button.disabled = false;
        });
    }
    
    handleLikeClick(e) {
        const button = e.currentTarget;
        const postId = button.dataset.postId;
        
        fetch(`/like-post/${postId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.liked) {
                button.classList.add('liked');
                this.showNotification('Liked!', 'success');
            } else {
                button.classList.remove('liked');
                this.showNotification('Unliked', 'info');
            }
            button.querySelector('span').textContent = data.total_likes;
        })
        .catch(error => {
            console.error('Error:', error);
            this.showNotification('Something went wrong!', 'error');
        });
    }
    
    updateFollowUI(button, isFollowing) {
        if (isFollowing) {
            // Now following
            button.textContent = 'Following';
            button.classList.remove('btn-premium', 'follow-btn');
            button.classList.add('btn-outline-light', 'unfollow-btn');
        } else {
            // Now unfollowed
            button.textContent = 'Follow';
            button.classList.remove('btn-outline-light', 'unfollow-btn');
            button.classList.add('btn-premium', 'follow-btn');
        }
    }
    
    updateButtonState(button, state) {
        switch(state) {
            case 'loading':
                button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Loading...';
                button.disabled = true;
                break;
            case 'success':
                button.disabled = false;
                break;
            case 'error':
                button.disabled = false;
                break;
        }
    }
    
    showNotification(message, type = 'info') {
        // Create a simple notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} position-fixed`;
        notification.style.cssText = `
            top: 20px; 
            right: 20px; 
            z-index: 9999; 
            min-width: 200px;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    getCSRFToken() {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, 10) === ('csrftoken' + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(10));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new SocialInteractions();
});