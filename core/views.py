
import re

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import News


ADMIN_GROUP = 'Administrators'
BAN_GROUP = 'Nexora Banned'


def index(request):
    search_query = request.GET.get('q', '').strip()
    posts = News.objects.all()

    if search_query:
        posts = posts.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(content__icontains=search_query)
        )
        return render(request, 'index.html', {
            'search_query': search_query,
            'research_news': posts,
        })

    recent_posts = list(posts[:12])

    return render(request, 'index.html', {
        'main_news': recent_posts[0] if recent_posts else None,
        'other_news': recent_posts[1:3],
        'short_news': recent_posts[3:],
    })


def category_posts(request, category):
    choices = dict(News.CATEGORY_CHOICES)

    if category not in choices:
        raise Http404('Такого раздела нет')

    return render(request, 'listing.html', {
        'page_title': choices[category],
        'posts': News.objects.filter(category=category),
    })


def topic_posts(request, topic):
    choices = dict(News.TOPIC_CHOICES)

    if topic not in choices or topic == 'other':
        raise Http404('Такой темы нет')

    return render(request, 'listing.html', {
        'page_title': choices[topic],
        'posts': News.objects.filter(topic=topic),
    })


def post_detail(request, pk):
    post = get_object_or_404(News, pk=pk)

    related = (
        News.objects
        .filter(topic=post.topic)
        .exclude(pk=post.pk)[:3]
    )

    return render(request, 'post_detail.html', {
        'post': post,
        'related_posts': related,
    })


def is_admin(user):
    if not user.is_authenticated:
        return False

    return (
        user.is_superuser
        or user.groups.filter(name=ADMIN_GROUP).exists()
    )


def is_banned(user):
    return user.groups.filter(name=BAN_GROUP).exists()


def parse_post_id(value):
    value = (value or '').strip()

    match = re.fullmatch(
        r'(?:(?:post|пост)\s*#?\s*|#)?([0-9]+)',
        value,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    post_id = int(match.group(1))
    return post_id if post_id > 0 else None


@login_required
@require_http_methods(['GET', 'POST'])
def admin_panel(request):
    if not is_admin(request.user):
        raise PermissionDenied(
            'У вас нет прав для доступа к Admin Panel.'
        )

    User = get_user_model()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action in ('ban', 'unban', 'promote', 'demote'):
            try:
                user_id = int(request.POST.get('user_id', ''))

                if user_id <= 0:
                    raise ValueError

            except (ValueError, TypeError):
                return HttpResponseBadRequest(
                    'Некорректный ID пользователя.'
                )

            with transaction.atomic():
                target = (
                    User.objects
                    .select_for_update()
                    .filter(pk=user_id)
                    .first()
                )

                if target is None:
                    messages.error(
                        request,
                        'Пользователь не найден.'
                    )

                elif action == 'ban':
                    if target.pk == request.user.pk:
                        messages.error(
                            request,
                            'Нельзя заблокировать самого себя.'
                        )

                    elif is_admin(target):
                        messages.error(
                            request,
                            'Нельзя заблокировать администратора.'
                        )

                    elif is_banned(target):
                        messages.warning(
                            request,
                            'Пользователь уже заблокирован.'
                        )

                    elif not target.is_active:
                        messages.error(
                            request,
                            'Аккаунт уже неактивен.'
                        )

                    else:
                        banned_group, _ = Group.objects.get_or_create(
                            name=BAN_GROUP
                        )

                        target.groups.add(banned_group)
                        target.is_active = False
                        target.save(update_fields=['is_active'])

                        messages.success(
                            request,
                            f'Пользователь #{target.pk} заблокирован.'
                        )

                elif action == 'unban':
                    if not is_banned(target):
                        messages.error(
                            request,
                            'Этот пользователь не заблокирован.'
                        )

                    else:
                        banned_group = Group.objects.get(
                            name=BAN_GROUP
                        )

                        target.groups.remove(banned_group)
                        target.is_active = True
                        target.save(update_fields=['is_active'])

                        messages.success(
                            request,
                            f'Пользователь #{target.pk} разблокирован.'
                        )

                elif action == 'promote':
                    if is_admin(target):
                        messages.warning(
                            request,
                            'Пользователь уже администратор.'
                        )

                    elif not target.is_active or is_banned(target):
                        messages.error(
                            request,
                            'Нельзя назначить неактивного пользователя.'
                        )

                    else:
                        admin_group, _ = Group.objects.get_or_create(
                            name=ADMIN_GROUP
                        )

                        target.groups.add(admin_group)

                        messages.success(
                            request,
                            f'Пользователь #{target.pk} теперь администратор.'
                        )

                elif action == 'demote':
                    if not request.user.is_superuser:
                        raise PermissionDenied(
                            'Снять администратора может только суперпользователь.'
                        )

                    elif target.is_superuser:
                        messages.error(
                            request,
                            'Нельзя снять права суперпользователя.'
                        )

                    elif not is_admin(target):
                        messages.warning(
                            request,
                            'Пользователь не является администратором.'
                        )

                    else:
                        admin_group = Group.objects.get(
                            name=ADMIN_GROUP
                        )

                        target.groups.remove(admin_group)

                        messages.success(
                            request,
                            f'Права администратора #{target.pk} отозваны.'
                        )

            return redirect('admin_panel')

        elif action == 'delete_post':
            post_id = parse_post_id(
                request.POST.get('post_id', '')
            )

            if post_id is None:
                return HttpResponseBadRequest(
                    'Некорректный номер публикации.'
                )

            confirmation = request.session.pop(
                'admin_post_confirmation',
                None
            )

            if (
                not confirmation
                or confirmation.get('id') != post_id
                or confirmation.get('name') != request.POST.get(
                    'expected_name', ''
                )
                or timezone.now().timestamp()
                - confirmation.get('time', 0) > 600
            ):
                messages.error(
                    request,
                    'Сначала найдите и проверьте публикацию.'
                )

                return redirect('admin_panel')

            with transaction.atomic():
                post = (
                    News.objects
                    .select_for_update()
                    .filter(pk=post_id)
                    .first()
                )

                if post is None:
                    messages.error(
                        request,
                        'Публикация не найдена.'
                    )

                elif post.name != confirmation['name']:
                    messages.error(
                        request,
                        'Заголовок изменился. Проверьте пост заново.'
                    )

                else:
                    post.delete()

                    messages.success(
                        request,
                        f'Публикация #{post_id} успешно удалена.'
                    )

            return redirect('admin_panel')

        return HttpResponseBadRequest(
            'Неизвестное действие.'
        )

    user_query = request.GET.get(
        'user', ''
    ).strip()[:100]

    users = User.objects.all().order_by('-pk')

    if user_query:
        search_filter = Q()

        model_fields = {
            field.name for field in User._meta.fields
        }

        for field in ('username', 'email', 'first_name', 'last_name'):
            if field in model_fields:
                search_filter |= Q(**{
                    f'{field}__icontains': user_query
                })

        if user_query.isascii() and user_query.isdecimal():
            search_filter |= Q(pk=int(user_query))

        users = users.filter(search_filter)

    page = Paginator(users, 15).get_page(
        request.GET.get('page')
    )

    admin_ids = set(
        User.objects.filter(
            groups__name=ADMIN_GROUP
        ).values_list('pk', flat=True)
    )

    banned_ids = set(
        User.objects.filter(
            groups__name=BAN_GROUP
        ).values_list('pk', flat=True)
    )

    for account in page.object_list:
        account.panel_is_admin = (
            account.is_superuser
            or account.pk in admin_ids
        )

        account.panel_is_banned = (
            account.pk in banned_ids
        )

    post_query = request.GET.get(
        'post', ''
    ).strip()[:100]

    preview = None
    post_search_error = ''

    request.session.pop(
        'admin_post_confirmation',
        None
    )

    if post_query:
        post_id = parse_post_id(post_query)

        if post_id is None:
            post_search_error = (
                'Введите номер поста, например: пост 14.'
            )

        else:
            preview = News.objects.filter(
                pk=post_id
            ).first()

            if preview is None:
                post_search_error = (
                    f'Публикация #{post_id} не найдена.'
                )

            else:
                request.session[
                    'admin_post_confirmation'
                ] = {
                    'id': preview.pk,
                    'name': preview.name,
                    'time': timezone.now().timestamp(),
                }

    total_users = User.objects.count()

    total_admins = (
        User.objects.filter(
            Q(is_superuser=True)
            | Q(groups__name=ADMIN_GROUP)
        )
        .distinct()
        .count()
    )

    total_bans = User.objects.filter(
        groups__name=BAN_GROUP
    ).count()

    total_posts = News.objects.count()

    return render(request, 'adminpanel.html', {
        'page': page,
        'user_query': user_query,
        'post_query': post_query,
        'preview': preview,
        'post_search_error': post_search_error,
        'total_users': total_users,
        'total_admins': total_admins,
        'total_bans': total_bans,
        'total_posts': total_posts,
    })
