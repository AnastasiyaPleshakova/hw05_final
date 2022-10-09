from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render


from .forms import CommentForm, PostForm
from .models import Follow, Group, Post
from .utils import paginators

User = get_user_model()


# @query_debugger
def index(request):
    posts = Post.objects.select_related('author', 'group').all()
    context = {'page_obj': paginators(request, posts)}
    return render(request, 'posts/index.html', context)


# @query_debugger
def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author').all()
    context = {
        'page_obj': paginators(request, posts),
        'group': group
    }
    return render(request, 'posts/group_list.html', context)


# @query_debugger
def profile(request, username):
    following = False
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group').all()
    author = User.objects.get(username=username)
    # сначала объединила условия
    # if request.user.is_authenticated and Follow.objects.filter(
    #       user=request.user, author=author).exists():
    #     following = True
    # но по количеству строк получается одинаково, решила сделать так:
    if request.user.is_authenticated:
        following = Follow.objects.filter(user=request.user, author=author).\
            exists()
    context = {
        'page_obj': paginators(request, posts),
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.prefetch_related('comments__author'),
        id=post_id
    )
    form = CommentForm()
    context = {
        'post': post,
        'form': form,
        'comments': post.comments.all(),
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'posts/post_create.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', request.user)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    if not form.is_valid():
        return render(request, 'posts/post_create.html', {'form': form})
    form.save()
    return redirect('posts:post_detail', post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.select_related('author', 'group').\
        filter(author__following__user=request.user)
    context = {'page_obj': paginators(request, posts)}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = User.objects.get(username=username)
    if request.user != author:
        Follow.objects.get_or_create(
            user=request.user,
            author=User.objects.get(username=username)
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    follow = get_object_or_404(
        Follow,
        author__username=username,
        user=request.user
    )
    follow.delete()
    return redirect('posts:profile', username=username)
