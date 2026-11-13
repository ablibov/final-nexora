from django.urls import path
from accounts import views as account_views
from accounts import settings_views as account_settings_views
from . import views, public_views

urlpatterns = [
    path('', public_views.index, name='index'),
    path('section/<slug:category>/', public_views.category_posts, name='category_posts'),
    path('topic/<slug:topic>/', public_views.topic_posts, name='topic_posts'),
    path('post/<int:pk>/', public_views.post_detail, name='post_detail'),
    path('post/<int:pk>/react/', public_views.react_to_post, name='react_to_post'),
    path('settings/reader-mode/', public_views.reader_mode_update, name='reader_mode_update'),
    path('my-posts/', public_views.my_posts, name='my_posts'),
    path('my-posts/new/', public_views.post_create, name='post_create'),
    path('my-posts/<int:pk>/edit/', public_views.post_edit, name='post_edit'),
    path('my-posts/<int:pk>/delete/', public_views.post_delete, name='post_delete'),
    path('login/', account_views.login_view, name='login'),
    path('logout/', account_views.logout_view, name='logout'),
    path('register/', account_views.register_view, name='register'),
    path('verify-email/', account_views.verify_email_view, name='verify_email'),
    path('settings/', account_settings_views.account_settings, name='account_settings'),
    path('settings/email/verify/', account_settings_views.verify_new_email, name='verify_new_email'),
    path('settings/sessions/logout-others/', account_settings_views.logout_other_sessions, name='logout_other_sessions'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
]
