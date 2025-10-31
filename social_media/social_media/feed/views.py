from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Q
from .forms import RegisterForm, ProfileForm, PostForm
from .models import Profile, Post, Follow, Comment, Chat, Message, Notification

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            return redirect('feed:feed')
    else:
        form = RegisterForm()
    return render(request, 'feed/register.html', {'form': form})

@login_required
def home(request):
    """Legacy home page - redirect to feed"""
    return redirect('feed:feed')

@login_required
def feed(request):
    """Main feed showing posts from followed users"""
    following_users = User.objects.filter(followers__follower=request.user)
    posts = Post.objects.filter(
        Q(author__in=following_users) | Q(author=request.user)
    ).distinct().order_by('-created_at')
    
    return render(request, 'feed/feed.html', {
        'posts': posts,
    })

@login_required
def profile(request):
    profile = request.user.profile
    posts = request.user.posts.all()
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('feed:profile')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'feed/profile.html', {
        'form': form,
        'posts': posts,
        'total_posts': posts.count(),
        'total_followers': profile.total_followers(),
        'total_following': profile.total_following(),
    })

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('feed:feed')
    else:
        form = PostForm()
    return render(request, 'feed/create_post.html', {'form': form})

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()
    
    if request.method == 'POST':
        if 'comment' in request.POST:
            text = request.POST.get('comment')
            if text:
                Comment.objects.create(post=post, author=request.user, text=text)
                # Create notification for post owner
                if post.author != request.user:
                    Notification.objects.create(
                        user=post.author,
                        from_user=request.user,
                        notification_type='comment',
                        post=post
                    )
                return redirect('feed:post_detail', post_id=post.id)
    
    return render(request, 'feed/post_detail.html', {
        'post': post,
        'comments': comments,
    })

@login_required
def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    profile = user.profile
    posts = user.posts.all()
    
    # Check if current user is following this user
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=request.user, 
            following=user
        ).exists()
    
    return render(request, 'feed/user_profile.html', {
        'profile_user': user,
        'profile': profile,
        'posts': posts,
        'is_following': is_following,
        'total_posts': posts.count(),
        'total_followers': profile.total_followers(),
        'total_following': profile.total_following(),
    })

@login_required
def search_users(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id)[:20]
    
    return render(request, 'feed/search.html', {'users': users, 'query': query})

@login_required
def follow_user(request, username):
    user_to_follow = get_object_or_404(User, username=username)
    
    if request.user != user_to_follow:
        follow, created = Follow.objects.get_or_create(
            follower=request.user, 
            following=user_to_follow
        )
        
        # Create notification only if new follow
        if created:
            Notification.objects.create(
                user=user_to_follow,
                from_user=request.user,
                notification_type='follow'
            )
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'following': True})
    
    return redirect('feed:user_profile', username=username)

@login_required
def unfollow_user(request, username):
    user_to_unfollow = get_object_or_404(User, username=username)
    
    Follow.objects.filter(follower=request.user, following=user_to_unfollow).delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'following': False})
    
    return redirect('feed:user_profile', username=username)

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        # Create notification for post owner
        if post.author != request.user:
            Notification.objects.create(
                user=post.author,
                from_user=request.user,
                notification_type='like',
                post=post
            )
    
    return JsonResponse({'liked': liked, 'total_likes': post.total_likes()})

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            comment = Comment.objects.create(post=post, author=request.user, text=text)
            return JsonResponse({
                'success': True,
                'author': comment.author.username,
                'text': comment.text,
                'created_at': comment.created_at.strftime('%b %d, %Y')
            })
    return JsonResponse({'success': False})

@login_required
def chat_list(request):
    chats = Chat.objects.filter(participants=request.user).order_by('-updated_at')
    
    # TEMPORARILY COMMENT OUT THESE LINES:
    # Mark messages as read when viewing chat list
    # for chat in chats:
    #     unread_messages = chat.messages.filter(is_read=False).exclude(sender=request.user)
    #     unread_messages.update(is_read=True)
    
    return render(request, 'feed/chat_list.html', {'chats': chats})

@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
    other_user = chat.participants.exclude(id=request.user.id).first()
    
    # TEMPORARILY COMMENT OUT THESE LINES:
    # Mark messages as read when opening chat
    # unread_messages = chat.messages.filter(is_read=False).exclude(sender=request.user)
    # unread_messages.update(is_read=True)
    
    if request.method == 'POST':
        text = request.POST.get('text')
        image = request.FILES.get('image')
        if text or image:
            Message.objects.create(chat=chat, sender=request.user, text=text, image=image)
            chat.save()  # Update updated_at
            return redirect('feed:chat_detail', chat_id=chat.id)
    
    messages = chat.messages.all()
    return render(request, 'feed/chat_detail.html', {
        'chat': chat,
        'other_user': other_user,
        'messages': messages,
    })

@login_required
def start_chat(request, username):
    other_user = get_object_or_404(User, username=username)
    
    # Find existing chat or create new one
    chat = Chat.objects.filter(participants=request.user).filter(participants=other_user).first()
    if not chat:
        chat = Chat.objects.create()
        chat.participants.add(request.user, other_user)
    
    return redirect('feed:chat_detail', chat_id=chat.id)

@login_required
def share_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    users = User.objects.exclude(id=request.user.id)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            # Start chat and send post
            chat = Chat.objects.filter(participants=request.user).filter(participants=user).first()
            if not chat:
                chat = Chat.objects.create()
                chat.participants.add(request.user, user)
            
            Message.objects.create(
                chat=chat, 
                sender=request.user, 
                text=f"Check out this post from {post.author.username}: {post.caption}",
                image=post.image
            )
            return redirect('feed:chat_detail', chat_id=chat.id)
    
    return render(request, 'feed/share_post.html', {
        'post': post,
        'users': users,
    })

@login_required
def notifications(request):
    notifications = request.user.notifications.all()[:50]
    # Mark as read when viewing
    unread_notifications = notifications.filter(is_read=False)
    unread_notifications.update(is_read=True)
    
    return render(request, 'feed/notifications.html', {'notifications': notifications})