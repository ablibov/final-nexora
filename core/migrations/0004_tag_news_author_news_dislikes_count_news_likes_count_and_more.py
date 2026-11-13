import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_nexora_avatar'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=40, unique=True)),
                ('slug', models.SlugField(allow_unicode=True, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='news',
            name='author',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='nexora_posts', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='news',
            name='dislikes_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='news',
            name='likes_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='news',
            name='status',
            field=models.CharField(choices=[('draft', 'Черновик'), ('published', 'Опубликовано')], db_index=True, default='published', max_length=12),
        ),
        migrations.AddField(
            model_name='news',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='news',
            name='views_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='news',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='posts', to='core.tag'),
        ),
        migrations.CreateModel(
            name='PostReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.SmallIntegerField(choices=[(1, 'Нравится'), (-1, 'Не нравится')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='core.news')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_reactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('post', 'user'), name='one_reaction_per_reader'), models.CheckConstraint(condition=models.Q(('value__in', [-1, 1])), name='reaction_is_vote')],
            },
        ),
        migrations.CreateModel(
            name='PostView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visitor_key', models.CharField(max_length=32)),
                ('viewed_on', models.DateField()),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visits', to='core.news')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('post', 'visitor_key', 'viewed_on'), name='one_post_view_per_day')],
            },
        ),
    ]
