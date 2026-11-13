import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.models import AccountPreferences

from .forms import PostForm
from .models import News, PostReaction, PostView


BAN_GROUP = 'Nexora Banned'


def can_write(user):
    return (
        user.is_authenticated and user.is_active
        and not user.groups.filter(name=BAN_GROUP).exists()
        and not AccountPreferences.objects.filter(user=user, reader_mode=True).exists()
    )


def published_posts():
    return News.objects.filter(status='published').select_related('author').prefetch_related('tags')


def filter_posts(posts, request):
    query = request.GET.get('q', '').strip()[:100]
    tag = request.GET.get('tag', '').strip()[:50]
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'new')

    if query:
        posts = posts.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
            | Q(content__icontains=query) | Q(tags__name__icontains=query)
            | Q(author__first_name__icontains=query)
            | Q(author__last_name__icontains=query)
        ).distinct()

    if tag:
        posts = posts.filter(tags__slug=tag)

    if category in dict(News.CATEGORY_CHOICES):
        posts = posts.filter(category=category)

    if sort == 'rating':
        posts = posts.order_by((F('likes_count') - F('dislikes_count')).desc(), '-created_at')
    elif sort == 'views':
        posts = posts.order_by('-views_count', '-created_at')
    else:
        sort = 'new'
        posts = posts.order_by('-created_at')

    return posts, {'search_query': query, 'tag_filter': tag, 'category_filter': category, 'sort': sort}


def index(request):
    base = published_posts()
    if request.GET.get('q') or request.GET.get('tag') or request.GET.get('category') or request.GET.get('sort'):
        posts, filters = filter_posts(base, request)
        return render(request, 'index.html', {
            'is_search': True, 'research_news': posts[:100], **filters,
        })

    recent = list(base[:12])
    return render(request, 'index.html', {
        'main_news': recent[0] if recent else None,
        'other_news': recent[1:3],
        'short_news': recent[3:],
    })


def category_posts(request, category):
    choices = dict(News.CATEGORY_CHOICES)
    if category not in choices:
        raise Http404('Такого раздела нет')
    posts, filters = filter_posts(published_posts().filter(category=category), request)
    return render(request, 'listing.html', {'page_title': choices[category], 'posts': posts[:100], **filters})


def topic_posts(request, topic):
    choices = dict(News.TOPIC_CHOICES)
    if topic not in choices or topic == 'other':
        raise Http404('Такой темы нет')
    posts, filters = filter_posts(published_posts().filter(topic=topic), request)
    return render(request, 'listing.html', {'page_title': choices[topic], 'posts': posts[:100], **filters})


def post_detail(request, pk):
    post = get_object_or_404(News.objects.select_related('author').prefetch_related('tags'), pk=pk)
    is_owner = request.user.is_authenticated and post.author_id == request.user.pk
    if post.status != 'published' and not is_owner:
        raise Http404('Публикация не найдена')

    if post.status == 'published':
        visitor = request.session.get('nexora_visitor')
        if not visitor:
            visitor = secrets.token_hex(16)
            request.session['nexora_visitor'] = visitor
        _, created = PostView.objects.get_or_create(
            post=post, visitor_key=visitor, viewed_on=timezone.localdate()
        )
        if created:
            News.objects.filter(pk=post.pk).update(views_count=F('views_count') + 1)
            post.views_count += 1

    my_vote = 0
    if request.user.is_authenticated:
        my_vote = PostReaction.objects.filter(post=post, user=request.user).values_list('value', flat=True).first() or 0

    related = published_posts().filter(topic=post.topic).exclude(pk=post.pk)[:3]
    return render(request, 'post_detail.html', {
        'post': post, 'related_posts': related, 'my_vote': my_vote,
        'can_rate': can_write(request.user), 'is_owner': is_owner,
    })


@require_POST
@login_required
def react_to_post(request, pk):
    if not can_write(request.user):
        raise PermissionDenied('Оценивать публикации нельзя.')

    raw = request.POST.get('vote')
    if raw not in ('1', '-1'):
        return HttpResponseBadRequest('Неверная реакция.')
    value = int(raw)

    with transaction.atomic():
        post = get_object_or_404(News.objects.select_for_update(), pk=pk, status='published')
        existing = PostReaction.objects.select_for_update().filter(post=post, user=request.user).first()
        changes = {'likes_count': 0, 'dislikes_count': 0}

        if existing:
            changes['likes_count' if existing.value == 1 else 'dislikes_count'] -= 1
            if existing.value == value:
                existing.delete()
            else:
                existing.value = value
                existing.save(update_fields=['value'])
                changes['likes_count' if value == 1 else 'dislikes_count'] += 1
        else:
            PostReaction.objects.create(post=post, user=request.user, value=value)
            changes['likes_count' if value == 1 else 'dislikes_count'] += 1

        News.objects.filter(pk=post.pk).update(
            likes_count=F('likes_count') + changes['likes_count'],
            dislikes_count=F('dislikes_count') + changes['dislikes_count'],
        )

    return redirect('post_detail', pk=pk)


@login_required
def my_posts(request):
    if not can_write(request.user):
        raise PermissionDenied('Аккаунт не может создавать публикации.')
    posts = News.objects.filter(author=request.user).order_by('-updated_at')
    return render(request, 'my_posts.html', {'posts': posts})


@login_required
def post_create(request):
    if not can_write(request.user):
        raise PermissionDenied('Аккаунт не может создавать публикации.')
    form = PostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.instance = post
            form.save_tags()
        messages.success(request, 'Публикация сохранена.')
        return redirect('my_posts')
    return render(request, 'post_editor.html', {'form': form, 'page_title': 'Новая публикация'})


@login_required
def post_edit(request, pk):
    if not can_write(request.user):
        raise PermissionDenied('Недостаточно прав.')
    post = get_object_or_404(News, pk=pk, author=request.user)
    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, 'Изменения сохранены.')
        return redirect('my_posts')
    return render(request, 'post_editor.html', {'form': form, 'post': post, 'page_title': 'Редактирование'})


@require_POST
@login_required
def post_delete(request, pk):
    if not can_write(request.user):
        raise PermissionDenied('Недостаточно прав.')
    post = get_object_or_404(News, pk=pk, author=request.user)
    post.delete()
    messages.success(request, 'Публикация удалена.')
    return redirect('my_posts')


@require_POST
@login_required
def reader_mode_update(request):
    preferences, _ = AccountPreferences.objects.get_or_create(user=request.user)
    preferences.reader_mode = request.POST.get('reader_mode') == 'on'
    preferences.save(update_fields=['reader_mode'])
    messages.success(request, 'Режим читателя обновлён.')
    return redirect('account_settings')
